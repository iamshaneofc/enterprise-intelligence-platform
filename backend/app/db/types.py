"""Custom SQLAlchemy database types for hybrid SQLite / PostgreSQL support."""
import json
from typing import Any, List, Optional
from sqlalchemy.types import TypeDecorator, Text

from backend.app.core.config import settings

# Try to import pgvector's SQLAlchemy Vector type
try:
    from pgvector.sqlalchemy import Vector as PgVector
    PGVECTOR_AVAILABLE = True
except ImportError:
    PgVector = None
    PGVECTOR_AVAILABLE = False


class VectorType(TypeDecorator):
    """
    Portable Vector Type.
    Uses native pgvector.Vector on PostgreSQL for efficient similarity search,
    falls back to JSON text storage on SQLite and other dialects.
    Guarantees a Python List[float] interface.
    """
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        """Use pgvector.Vector on PostgreSQL, Text on other dialects."""
        if PGVECTOR_AVAILABLE and dialect.name == "postgresql":
            return dialect.type_descriptor(PgVector(settings.EMBEDDING_DIMENSION))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value: Optional[List[float]], dialect: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, (list, tuple)):
            return json.dumps([float(x) for x in value])
        return str(value)

    def process_result_value(self, value: Optional[str], dialect: Any) -> Optional[List[float]]:
        if value is None:
            return None
        if isinstance(value, list):
            return [float(x) for x in value]
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [float(x) for x in parsed]
            return None
        except Exception:
            return None

