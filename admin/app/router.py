import logging
import zipfile
from io import BytesIO

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import KBVersionResponse
from app.service import ConflictError, KnowledgeBaseService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/knowledge-base",
    tags=["knowledge-base"],
)


@router.post("/versions", response_model=KBVersionResponse, status_code=201)
def upload_version(
    archive: UploadFile = File(...),
    comment: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """Upload a new knowledge base version and immediately ingest it into Qdrant."""
    if not archive.filename or not archive.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Uploaded file must be a .zip archive")

    content = archive.file.read()
    try:
        zipfile.ZipFile(BytesIO(content))
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid .zip archive")

    svc = KnowledgeBaseService(db)
    try:
        return svc.upload_version(content, comment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Upload/ingest failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/versions", response_model=list[KBVersionResponse])
def list_versions(db: Session = Depends(get_db)):
    """List all knowledge base versions."""
    svc = KnowledgeBaseService(db)
    return svc.list_versions()


@router.get("/versions/active", response_model=KBVersionResponse)
def get_active_version(db: Session = Depends(get_db)):
    """Get the currently active knowledge base version."""
    svc = KnowledgeBaseService(db)
    version = svc.get_active_version()
    if version is None:
        raise HTTPException(status_code=404, detail="No active version")
    return version


@router.get("/versions/active/archive")
def download_active_archive(db: Session = Depends(get_db)):
    """Download the active version as a .zip archive."""
    svc = KnowledgeBaseService(db)
    version = svc.get_active_version()
    if version is None:
        raise HTTPException(status_code=404, detail="No active version")
    zip_bytes, filename = svc.download_version_archive(version)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/versions/{version_num}/archive")
def download_version_archive(version_num: int, db: Session = Depends(get_db)):
    """Download a specific version as a .zip archive."""
    svc = KnowledgeBaseService(db)
    version = svc.get_version(version_num)
    if version is None:
        raise HTTPException(status_code=404, detail=f"Version {version_num} not found")
    zip_bytes, filename = svc.download_version_archive(version)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/versions/{version_num}/activate", response_model=KBVersionResponse)
def activate_version(version_num: int, db: Session = Depends(get_db)):
    """Activate a version by pointing the kb_active alias to it."""
    svc = KnowledgeBaseService(db)
    try:
        return svc.activate_version(version_num)
    except LookupError:
        raise HTTPException(status_code=404, detail=f"Version {version_num} not found")
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.delete("/versions/{version_num}", status_code=204)
def delete_version(version_num: int, db: Session = Depends(get_db)):
    """Delete a version and all its files from MinIO, Qdrant, and the database."""
    svc = KnowledgeBaseService(db)
    try:
        svc.delete_version(version_num)
    except LookupError:
        raise HTTPException(status_code=404, detail=f"Version {version_num} not found")
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
