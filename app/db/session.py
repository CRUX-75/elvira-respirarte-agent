from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.config import settings


def get_database_url() -> str:
    """
    Return the configured database URL.

    The application requires DATABASE_URL only for persistence-related flows.
    This allows local tests that do not touch the database to keep running
    without requiring PostgreSQL.
    """
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    database_url = settings.database_url

    # Easypanel or other platforms may provide postgres:// URLs.
    # SQLAlchemy expects postgresql:// or postgresql+psycopg://.
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)

    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    return database_url


def create_db_engine() -> Engine:
    """
    Create a SQLAlchemy engine for PostgreSQL.

    pool_pre_ping=True helps avoid stale connections in long-running deployments.
    """
    return create_engine(
        get_database_url(),
        pool_pre_ping=True,
        future=True,
    )


engine = create_db_engine()
