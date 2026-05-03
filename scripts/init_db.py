from pathlib import Path

from sqlalchemy import text

from app.db.session import engine


SCHEMA_PATH = Path(__file__).resolve().parents[1] / "app" / "db" / "schema.sql"


def init_db() -> None:
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    with engine.begin() as conn:
        conn.execute(text(schema_sql))

    print("Database schema initialized successfully.")


if __name__ == "__main__":
    init_db()
