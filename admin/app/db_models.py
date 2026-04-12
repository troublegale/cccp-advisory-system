import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class KBVersion(Base):
    __tablename__ = "kb_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_num = Column(Integer, unique=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    status = Column(String(20), nullable=False, default="uploaded")
    s3_prefix = Column(Text, nullable=False)
    qdrant_collection = Column(Text, nullable=True)
    file_count = Column(Integer, nullable=True)
    comment = Column(Text, nullable=True)

    files = relationship("KBFile", back_populates="version", cascade="all, delete-orphan")


class KBFile(Base):
    __tablename__ = "kb_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_id = Column(UUID(as_uuid=True), ForeignKey("kb_versions.id"), nullable=False)
    filename = Column(Text, nullable=False)
    s3_key = Column(Text, nullable=False)
    size_bytes = Column(Integer, nullable=True)
    sha256 = Column(Text, nullable=True)

    version = relationship("KBVersion", back_populates="files")
