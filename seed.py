# db_seed.py
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "flibrary.db")

def seed_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.executemany(
        "INSERT OR IGNORE INTO books VALUES (?, ?, ?, ?, ?)",
        [
            ('9780132350884', 'Clean Code', 'Robert C. Martin', 40.0, 10),
            ('9780201616224', 'The Pragmatic Programmer', 'Andrew Hunt', 45.0, 5),
            ('9780131103627', 'The C Programming Language', 'Brian Kernighan', 35.0, 7),
            ('9781491957660', 'Fluent Python', 'Luciano Ramalho', 50.0, 6),
            ('9780262033848', 'Introduction to Algorithms', 'Thomas H. Cormen', 60.0, 4),
            ('9780134685991', 'Effective Java', 'Joshua Bloch', 42.0, 8),
            ('9781492078005', 'Designing Data-Intensive Applications', 'Martin Kleppmann', 55.0, 3),
            ('9780134494166', 'Clean Architecture', 'Robert C. Martin', 38.0, 9),
            ('9781617296086', 'Spring in Action', 'Craig Walls', 47.0, 5),
            ('9781492055020', 'Python Data Science Handbook', 'Jake VanderPlas', 48.0, 6),
        ]
    )

    cursor.executemany(
        "INSERT OR IGNORE INTO customers (name, email) VALUES (?, ?)",
        [
            ('Ahmad Mahmoud', 'ahmad@mail.com'),
            ('Sara Khaled', 'sara@mail.com'),
            ('Omar Hassan', 'omar@mail.com'),
            ('Lina Youssef', 'lina@mail.com'),
            ('Yousef Nasser', 'yousef@mail.com'),
            ('Maya Adel', 'maya@mail.com'),
        ]
    )

    cursor.executemany(
        "INSERT INTO orders (customer_id) VALUES (?)",
        [(1,), (2,), (3,), (4,)]
    )

    cursor.executemany(
        "INSERT INTO order_items VALUES (?, ?, ?)",
        [
            (1, '9780132350884', 2),
            (1, '9780134685991', 1),
            (2, '9780201616224', 1),
            (2, '9781492078005', 2),
            (3, '9780131103627', 1),
            (4, '9781491957660', 1),
        ]
    )

    conn.commit()
    conn.close()
    print("✅ Database seeded successfully")

if __name__ == "__main__":
    seed_db()
