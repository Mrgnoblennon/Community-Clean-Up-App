
import sqlite3

connection = sqlite3.connect("instance/cleanup.db")
cursor = connection.cursor()

email = input("Enter organiser email: ").strip().lower()

cursor.execute("""
    UPDATE users
    SET approved = 1
    WHERE LOWER(email) = ?
      AND role = 'organiser'
      AND approved = 0
""", (email,))

connection.commit()

if cursor.rowcount == 1:
    print("Organiser approved successfully!")
else:
    print("No pending organiser found with that email.")

connection.close()