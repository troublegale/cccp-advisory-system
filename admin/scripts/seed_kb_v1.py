"""
Seed script: import files from knowledge/ directory as KB version 1.

Run once manually inside the admin container:
    uv run python scripts/seed_kb_v1.py

After seeding, call:
    POST /api/v1/knowledge-base/versions/1/activate
"""

import hashlib
import sys
from pathlib import Path

# Add parent directory to path so we can import app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.db_models import KBFile, KBVersion
from app.service import KnowledgeBaseService
from app.storage import ensure_bucket_exists, get_minio_client


def seed() -> None:
    # Ensure tables exist
    import app.db_models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Idempotency: skip if v1 already exists
        existing = db.query(KBVersion).filter(KBVersion.version_num == 1).first()
        if existing:
            print("Version 1 already exists, skipping seed.")
            return

        knowledge_dir = Path(settings.knowledge_dir)
        if not knowledge_dir.is_dir():
            print(f"Knowledge directory not found: {knowledge_dir}")
            return

        md_files = sorted(knowledge_dir.glob("*.md"))
        if not md_files:
            print(f"No .md files found in {knowledge_dir}")
            return

        # Ensure MinIO bucket
        s3 = get_minio_client()
        ensure_bucket_exists(s3, settings.minio_kb_bucket)

        s3_prefix = "versions/v1/"

        version = KBVersion(
            version_num=1,
            status="uploaded",
            s3_prefix=s3_prefix,
            file_count=len(md_files),
            comment="Initial import from knowledge/ directory",
        )
        db.add(version)
        db.flush()

        for md_file in md_files:
            content = md_file.read_bytes()
            s3_key = f"{s3_prefix}{md_file.name}"

            s3.put_object(
                Bucket=settings.minio_kb_bucket,
                Key=s3_key,
                Body=content,
            )

            db.add(KBFile(
                version_id=version.id,
                filename=md_file.name,
                s3_key=s3_key,
                size_bytes=len(content),
                sha256=hashlib.sha256(content).hexdigest(),
            ))
            print(f"  Uploaded {md_file.name} -> {s3_key}")

        db.commit()
        db.refresh(version)
        print(f"Seeded version 1 with {len(md_files)} files. Ingesting...")

        svc = KnowledgeBaseService(db)
        collection_name = f"{settings.kb_collection_prefix}1"
        svc._ingest(version, collection_name)
        print(f"Ingested into Qdrant collection '{collection_name}'.")
        print("Next step:")
        print("  curl -X POST http://localhost/api/v1/knowledge-base/versions/1/activate")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
