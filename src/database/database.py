import os
import sqlite3
from pathlib import Path


def get_connection():
    db_path = Path(os.getenv("SECURITY_DB_PATH", "data/security.db"))
    conn = sqlite3.connect(db_path)
    return conn