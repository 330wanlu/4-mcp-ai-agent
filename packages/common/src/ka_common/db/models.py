"""SQLAlchemy 模型：documents / chunks / audit_logs / tickets / memory / users。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ka_common.db.base import Base, TimestampMixin

# doubao-embedding-vision 可通过 dimensions 指定；项目冻结为 1024
EMBEDDING_DIM = 1024


class User(Base, TimestampMixin):
    """鉴权后置：先建空壳表。"""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(128), default="")
    roles: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    extra: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    source_path: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    domain: Mapped[str] = mapped_column(String(64), default="policies")  # policies/travel/...
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, default="")
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    chunks: Mapped[list[Chunk]] = relationship(
        "Chunk", back_populates="document", cascade="all, delete-orphan"
    )


class Chunk(Base, TimestampMixin):
    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    document_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    section: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_estimate: Mapped[int] = mapped_column(Integer, default=0)
    embedding = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    document: Mapped[Document] = relationship("Document", back_populates="chunks")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    session_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    agent: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class Ticket(Base, TimestampMixin):
    """Business MCP 用：阶段 4 写操作落库。"""

    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    ticket_type: Mapped[str] = mapped_column(String(64), nullable=False)  # travel/leave/...
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


class SessionSummary(Base, TimestampMixin):
    """Memory MCP：会话摘要（PostgreSQL 真相源）。"""

    __tablename__ = "session_summaries"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    turns: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class UserPreference(Base, TimestampMixin):
    """Memory MCP：用户偏好（PostgreSQL 真相源）。"""

    __tablename__ = "user_preferences"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    preferences: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    notes: Mapped[str] = mapped_column(Text, default="")
