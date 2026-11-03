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

connection.commit()
connection.close()