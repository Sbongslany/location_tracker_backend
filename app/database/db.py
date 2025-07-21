

# app/database/db.py
import sqlite3
from contextlib import contextmanager

# Assuming you kept the database name as "locations.db" or your new chosen name
DATABASE = "locations1.db" # Or "my_live_tracker.db" or whatever you named it last

@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        # Create users table FIRST (important for foreign key if you use it)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                hashed_password TEXT NOT NULL
            )
        """)

        # Create locations table - UPDATED: NO unit_id
        conn.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,  -- Keep this, it's from JWT
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                timestamp TEXT NOT NULL,
                -- Optional: Foreign key constraint (highly recommended)
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        conn.commit()