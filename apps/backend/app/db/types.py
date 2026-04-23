from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB


# Keep PostgreSQL production semantics while allowing SQLite-backed tests.
JSON_VARIANT = JSON().with_variant(JSONB, "postgresql")
