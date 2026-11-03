import sqlite3

connection = sqlite3.connect("instance/cleanup.db")
cursor = connection.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        registered INTEGER DEFAULT 0,
        capacity INTEGER NOT NULL
    )
""")

cursor.execute("SELECT COUNT(*) FROM events")

if cursor.fetchone()[0] == 0:
    cursor.executemany("""
        INSERT INTO events (name, date, time, registered, capacity)
        VALUES (?, ?, ?, ?, ?)
    """, [
        ("Riverside Park Clean-Up", "2026-10-24", "10:00–12:00", 12, 20),
        ("Meadow Lane Clean-Up", "2026-11-14", "09:00–11:00", 6, 15)
    ])

cursor.execute("""
    CREATE TABLE IF NOT EXISTS registrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        FOREIGN KEY (event_id) REFERENCES events(id),
        UNIQUE (event_id, email)
    )
""")

connection.commit()
connection.close()