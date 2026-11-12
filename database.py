
import sqlite3
import os
import sys

# Database location
DB_PATH = os.path.join("instance", "cleanup.db")


def setup_database():
    # Ensure the database folder exists
    os.makedirs("instance", exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    # Create events table
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

    # Create registrations table
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

    # Add attendee count to existing registrations
    cursor.execute("PRAGMA table_info(registrations)")
    columns = [column[1] for column in cursor.fetchall()]

    if "attendee_count" not in columns:
        cursor.execute("""
            ALTER TABLE registrations
            ADD COLUMN attendee_count INTEGER NOT NULL DEFAULT 1
            CHECK (attendee_count >= 1)
        """)

    # Create users table for organiser accounts
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'participant'
                CHECK (role IN ('participant', 'organiser')),
            approved INTEGER NOT NULL DEFAULT 0
                CHECK (approved IN (0, 1)),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Add missing columns to existing databases
    cursor.execute("PRAGMA table_info(events)")
    columns = [column[1] for column in cursor.fetchall()]

    new_columns = {
        "location": "TEXT",
        "description": "TEXT",
        "equipment": "TEXT",
        "safety_instructions": "TEXT",
        "latitude": "REAL",
        "longitude": "REAL"
    }

    for column_name, column_type in new_columns.items():
        if column_name not in columns:
            cursor.execute(
                f"ALTER TABLE events ADD COLUMN {column_name} {column_type}"
            )

    # Sample clean-up events
    sample_events = [
        ("South Beach Clean-Up", "South Beach, Fremantle",
         -32.073, 115.751, "2026-11-14", "09:00", 5, 20,
         "Beach litter collection", "Gloves and bags", "Safety checklist reviewed"),

        ("Kings Park Clean-Up", "Kings Park, Perth",
         -31.961, 115.833, "2026-11-21", "10:00", 30, 30,
         "Park litter collection", "Gloves and bags", "Safety checklist reviewed"),

        ("Cottesloe Beach Clean-Up", "Cottesloe Beach",
         -31.994, 115.751, "2026-11-28", "08:00", 8, 15,
         "Coastal clean-up", "Gloves and bags", "Safety checklist reviewed"),

        ("Swan River Clean-Up", "East Perth Foreshore",
         -31.953, 115.879, "2026-12-05", "09:00", 0, 25,
         "Riverbank clean-up", "Gloves and bags", "Safety checklist reviewed"),

        ("Bathers Beach Clean-Up", "Bathers Beach, Fremantle",
         -32.057, 115.744, "2026-11-07", "08:00", 10, 10,
         "Beach litter collection", "Gloves and bags", "Safety checklist reviewed"),

        ("Leighton Beach Clean-Up", "Leighton Beach, North Fremantle",
         -32.029, 115.750, "2026-11-15", "08:00", 12, 20,
         "Remove litter from the beach", "Gloves and bags", "Safety checklist reviewed"),

        ("Point Walter River Clean-Up", "Point Walter, Bicton",
         -32.011, 115.788, "2026-11-22", "09:00", 25, 25,
         "Collect rubbish along the Swan River", "Gloves and bags", "Safety checklist reviewed"),

        ("Coogee Beach Clean-Up", "Coogee Beach, WA",
         -32.115, 115.762, "2026-11-29", "07:30", 4, 15,
         "Beach and dune litter collection", "Gloves and bags", "Safety checklist reviewed"),

        ("Hyde Park Community Clean-Up", "Hyde Park, Perth",
         -31.938, 115.863, "2026-12-06", "10:00", 0, 30,
         "Remove litter from parkland", "Gloves and bags", "Safety checklist reviewed"),

        ("Scarborough Beach Clean-Up", "Scarborough Beach, Perth",
         -31.894, 115.756, "2026-12-12", "08:00", 18, 20,
         "Coastal litter collection", "Gloves and bags", "Safety checklist reviewed"),

        ("Manning Park Clean-Up", "Manning Park, Hamilton Hill",
         -32.091, 115.775, "2026-12-19", "09:00", 15, 15,
         "Park and bushland clean-up", "Gloves and bags", "Safety checklist reviewed"),

        ("Port Beach Clean-Up", "Port Beach, North Fremantle",
         -32.039, 115.748, "2026-10-18", "08:00", 10, 20,
         "Beach litter collection", "Gloves and bags", "Safety checklist reviewed"),

        ("Bibra Lake Community Clean-Up", "Bibra Lake, WA",
         -32.096, 115.821, "2026-10-25", "09:00", 20, 20,
         "Lakeside rubbish collection", "Gloves and bags", "Safety checklist reviewed")
    ]

    # Insert sample events only if they don't already exist
    for event in sample_events:
        cursor.execute(
            "SELECT id FROM events WHERE name = ?",
            (event[0],)
        )

        if cursor.fetchone() is None:
            cursor.execute("""
                INSERT INTO events
                (name, location, latitude, longitude, date, time,
                 registered, capacity, description, equipment,
                 safety_instructions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, event)

    connection.commit()
    connection.close()

    print("Database setup complete. Users table and sample events are ready.")


# Approve an existing organiser account
def approve_organiser(email):
    if not os.path.isfile(DB_PATH):
        print("Database not found. Run python database.py first.")
        return

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    try:
        cursor.execute("""
            UPDATE users
            SET approved = 1
            WHERE email = ? AND role = 'organiser'
        """, (email,))

        if cursor.rowcount > 0:
            connection.commit()
            print(f"Organiser approved: {email}")
        else:
            print(f"No organiser account found for: {email}")

    except sqlite3.Error as error:
        print(f"Database error: {error}")

    finally:
        connection.close()


# Run commands from the terminal
if __name__ == "__main__":

    if len(sys.argv) == 1:
        setup_database()

    elif len(sys.argv) == 3 and sys.argv[1] == "approve":
        approve_organiser(sys.argv[2])

    else:
        print("Available commands:")
        print("  python database.py")
        print("  python database.py approve email@example.com")
