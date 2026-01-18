# db_init.py
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "flibrary.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS books (
        isbn TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        price REAL NOT NULL,
        stock INTEGER NOT NULL CHECK (stock >= 0)
    );

    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL
    );

    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        status TEXT DEFAULT 'created',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    );

    CREATE TABLE IF NOT EXISTS order_items (
        order_id INTEGER NOT NULL,
        isbn TEXT NOT NULL,
        qty INTEGER NOT NULL CHECK (qty > 0),
        FOREIGN KEY (order_id) REFERENCES orders(id),
        FOREIGN KEY (isbn) REFERENCES books(isbn)
    );

    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS tool_calls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        name TEXT NOT NULL,
        args_json TEXT NOT NULL,
        result_json TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    conn.close()
    print("✅ Database schema created successfully")

if __name__ == "__main__":
    init_db()
