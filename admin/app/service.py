import hashlib
import io
import logging
import zipfile
from pathlib import Path

import ollama
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import (
    CreateAlias,
    CreateAliasOperation,
    DeleteAlias,
    DeleteAliasOperation,
    Distance,
    PointStruct,
    VectorParams,
)
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.db_models import KBFile, KBVersion
from app.storage import get_minio_client

logger = logging.getLogger(__name__)


class ConflictError(Exception):
    pass


class KnowledgeBaseService:
    """Service for managing knowledge base versions, storage, and ingestion."""

    def __init__(self, db: Session):
        self.db = db
        self.s3 = get_minio_client()
        self.qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

    def list_versions(self) -> list[KBVersion]:
        """List all knowledge base versions ordered by version_num descending."""
        return (
            self.db.query(KBVersion)
            .order_by(KBVersion.version_num.desc())
            .all()
        )

    def get_active_version(self) -> KBVersion | None:
        """Get the currently active version."""
        return (
            self.db.query(KBVersion)
            .filter(KBVersion.status == "active")
            .first()
        )

    def get_version(self, version_num: int) -> KBVersion | None:
        """Get a specific version by its version number."""
        return (
            self.db.query(KBVersion)
            .filter(KBVersion.version_num == version_num)
            .first()
        )

    def upload_version(self, archive_bytes: bytes, comment: str | None = None) -> KBVersion:
        """Upload a new version from a zip archive and immediately ingest it into Qdrant."""
        md_files = self._extract_md_files(archive_bytes)
        if not md_files:
            raise ValueError("Archive contains no .md files")

        max_num = self.db.query(func.max(KBVersion.version_num)).scalar()
        version_num = (max_num or 0) + 1
        s3_prefix = f"versions/v{version_num}/"
        collection_name = f"{settings.kb_collection_prefix}{version_num}"

        version = KBVersion(
            version_num=version_num,
            status="uploaded",
            s3_prefix=s3_prefix,
            file_count=len(md_files),
            comment=comment,
        )
        self.db.add(version)
        self.db.flush()

        # Upload files to MinIO
        for filename, content in md_files.items():
            s3_key = f"{s3_prefix}{filename}"
            self.s3.put_object(
                Bucket=settings.minio_kb_bucket,
                Key=s3_key,
                Body=content,
            )
            self.db.add(KBFile(
                version_id=version.id,
                filename=filename,
                s3_key=s3_key,
                size_bytes=len(content),
                sha256=hashlib.sha256(content).hexdigest(),
            ))

        self.db.commit()
        self.db.refresh(version)

        # Ingest into Qdrant
        try:
            self._ingest(version, collection_name)
        except Exception:
            version.status = "failed"
            self.db.commit()
            raise

        return version

    def activate_version(self, version_num: int) -> KBVersion:
        """Activate a version by pointing the kb_active alias to its collection."""
        version = self.get_version(version_num)
        if version is None:
            raise LookupError(f"Version {version_num} not found")
        if version.status not in ("ingested", "active"):
            raise ConflictError(
                f"Version {version_num} has status '{version.status}', expected 'ingested'"
            )
        if version.status == "active":
            return version

        alias = settings.kb_active_alias
        collection_name = version.qdrant_collection

        # Atomically switch alias: delete old + create new
        try:
            self.qdrant.update_collection_aliases(
                change_aliases_operations=[
                    DeleteAliasOperation(
                        delete_alias=DeleteAlias(alias_name=alias)
                    ),
                    CreateAliasOperation(
                        create_alias=CreateAlias(
                            collection_name=collection_name, alias_name=alias
                        )
                    ),
                ]
            )
        except Exception:
            # Alias doesn't exist yet (first activation)
            self.qdrant.update_collection_aliases(
                change_aliases_operations=[
                    CreateAliasOperation(
                        create_alias=CreateAlias(
                            collection_name=collection_name, alias_name=alias
                        )
                    ),
                ]
            )

        self.db.query(KBVersion).filter(KBVersion.status == "active").update(
            {"status": "ingested"}
        )
        version.status = "active"
        self.db.commit()
        self.db.refresh(version)

        logger.info(
            "Activated version %d (alias %s -> %s)",
            version_num, alias, collection_name,
        )
        return version

    def delete_version(self, version_num: int) -> None:
        """Delete a version: remove Qdrant collection, MinIO files, and DB records."""
        version = self.get_version(version_num)
        if version is None:
            raise LookupError(f"Version {version_num} not found")
        if version.status == "active":
            raise ConflictError("Cannot delete the active version. Activate another version first.")

        # Delete Qdrant collection
        if version.qdrant_collection and self.qdrant.collection_exists(version.qdrant_collection):
            self.qdrant.delete_collection(version.qdrant_collection)

        # Delete files from MinIO
        for file in version.files:
            self.s3.delete_object(Bucket=settings.minio_kb_bucket, Key=file.s3_key)

        # Delete DB records
        self.db.delete(version)
        self.db.commit()

        logger.info("Deleted version %d", version_num)

    def download_version_archive(self, version: KBVersion) -> tuple[bytes, str]:
        """Download all files of a version as a zip archive."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in version.files:
                obj = self.s3.get_object(
                    Bucket=settings.minio_kb_bucket, Key=file.s3_key
                )
                zf.writestr(file.filename, obj["Body"].read())
        buf.seek(0)
        return buf.getvalue(), f"kb_v{version.version_num}.zip"

    def _ingest(self, version: KBVersion, collection_name: str) -> None:
        """Chunk, embed, and store version files in Qdrant."""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        chunks = []
        chunk_payloads = []
        for file in version.files:
            obj = self.s3.get_object(
                Bucket=settings.minio_kb_bucket, Key=file.s3_key
            )
            text = obj["Body"].read().decode("utf-8")
            for chunk in splitter.split_text(text):
                chunks.append(chunk)
                chunk_payloads.append({"filename": file.filename, "text": chunk})

        client = ollama.Client(host=settings.ollama_base_url)
        response = client.embed(model=settings.embedding_model, input=chunks)
        embeddings = response.embeddings
        vector_size = len(embeddings[0])

        if self.qdrant.collection_exists(collection_name):
            self.qdrant.delete_collection(collection_name)
        self.qdrant.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

        points = [
            PointStruct(id=i, vector=emb, payload=payload)
            for i, (emb, payload) in enumerate(zip(embeddings, chunk_payloads))
        ]
        self.qdrant.upsert(collection_name=collection_name, points=points)

        version.qdrant_collection = collection_name
        version.status = "ingested"
        self.db.commit()
        self.db.refresh(version)

        logger.info(
            "Ingested version %d: %d chunks into %s",
            version.version_num, len(chunks), collection_name,
        )

    @staticmethod
    def _extract_md_files(archive_bytes: bytes) -> dict[str, bytes]:
        """Extract .md files from a zip archive. Returns {filename: content}."""
        md_files = {}
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                name = Path(info.filename).name
                if name.startswith(".") or not name.endswith(".md"):
                    continue
                md_files[name] = zf.read(info)
        return md_files
