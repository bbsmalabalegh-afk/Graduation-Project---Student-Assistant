"""الاتصال بقاعدة البيانات (SQLite) وإنشاء الجداول."""
import sqlite3
from pathlib import Path

from . import config

SCHEMA_FILE = Path(__file__).resolve().parent / "schema.sql"


def connect(db_path=None) -> sqlite3.Connection:
    path = Path(db_path or config.DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init_db(db_path=None) -> None:
    con = connect(db_path)
    try:
        con.executescript(SCHEMA_FILE.read_text(encoding="utf-8"))
        con.commit()
    finally:
        con.close()


def get_db():
    """FastAPI dependency: اتصال جديد لكل Request ويتقفل بعده."""
    con = connect()
    try:
        yield con
    finally:
        con.close()


def row_to_dict(row):
    return dict(row) if row is not None else None
