"""数据库子包。"""

from ka_common.db.base import Base
from ka_common.db.models import (
    EMBEDDING_DIM,
    AuditLog,
    Chunk,
    Document,
    SessionSummary,
    Ticket,
    User,
    UserPreference,
)
from ka_common.db.session import ensure_vector_extension, get_engine, session_scope

__all__ = [
    "Base",
    "EMBEDDING_DIM",
    "AuditLog",
    "Chunk",
    "Document",
    "SessionSummary",
    "Ticket",
    "User",
    "UserPreference",
    "ensure_vector_extension",
    "get_engine",
    "session_scope",
]
