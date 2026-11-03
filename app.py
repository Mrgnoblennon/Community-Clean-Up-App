from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import date

app = Flask(__name__)

@app.route("/")
def home():
  return render_template("index.html")

@app.route("/events")
def events():
    search = request.args.get("search", "").strip()

    connection = sqlite3.connect("instance/cleanup.db")
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    cursor.execute(
        "SELECT * FROM events WHERE name LIKE ?",
        (f"%{search}%",)
    )

    cleanup_events = cursor.fetchall()
    connection.close()

    return render_template("events.html", events=cleanup_events, search=search)

@app.route("/events/<int:event_id>")
def event_details(event_id):
    connection = sqlite3.connect("instance/cleanup.db")
    connection.row_factory = sqlite3.Row

    cursor = connection.cursor()
    cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))

    event = cursor.fetchone()
    connection.close()

    if event is None:
        return "Event not found", 404

    return render_template("event_details.html", event=event)

@app.route("/events/<int:event_id>/join", methods=["POST"])
def join_event(event_id):
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()

    if not name or not email:
        return "Name and email are required", 400

    connection = sqlite3.connect("instance/cleanup.db")
    cursor = connection.cursor()

    try:
        cursor.execute(
            "SELECT capacity FROM events WHERE id = ?",
            (event_id,)
        )
        event = cursor.fetchone()

        if event is None:
            return "Event not found", 404

        cursor.execute(
            "SELECT COUNT(*) FROM registrations WHERE event_id = ?",
            (event_id,)
        )
        registration_count = cursor.fetchone()[0]

        if registration_count >= event[0]:
            return "This event is fully booked", 400

        cursor.execute("""
            INSERT INTO registrations (event_id, name, email)
            VALUES (?, ?, ?)
        """, (event_id, name, email))

        cursor.execute("""
            UPDATE events
            SET registered = registered + 1
            WHERE id = ?
        """, (event_id,))

        connection.commit()

    except sqlite3.IntegrityError:
        return "This email is already registered for this event", 400

    finally:
        connection.close()

    return redirect(url_for("confirmation", event_id=event_id))

@app.route("/events/<int:event_id>/confirmation")
def confirmation(event_id):
  
    connection = sqlite3.connect("instance/cleanup.db")
    connection.row_factory = sqlite3.Row

    cursor = connection.cursor()
    cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
    event = cursor.fetchone()
    connection.close()

    if event is None:
        return "Event not found", 404

    return render_template("confirmation.html", event=event)

@app.route("/create-event", methods=["GET", "POST"])
def create_event():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        location = request.form.get("location", "").strip()
        event_date = request.form.get("date", "")
        time = request.form.get("time", "")
        description = request.form.get("description", "").strip()
        equipment = request.form.get("equipment", "").strip()
        safety_confirmed = request.form.get("safety_confirmed")

        try:
            capacity = int(request.form.get("capacity", "0"))
            parsed_date = date.fromisoformat(event_date)
        except ValueError:
            return "Invalid date or participant limit", 400

        if not name or not location or not time:
            return "Please complete all required fields", 400

        if capacity < 1:
            return "Participant limit must be at least 1", 400

        if parsed_date < date.today():
            return "Event date cannot be in the past", 400

        if safety_confirmed != "on":
            return "Safety checklist confirmation is required", 400

        connection = sqlite3.connect("instance/cleanup.db")
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO events
            (name, location, date, time, capacity,
             registered, description, equipment, safety_instructions)
            VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?)
        """, (
            name, location, event_date, time, capacity,
            description, equipment, "Safety checklist reviewed"
        ))

        connection.commit()
        event_id = cursor.lastrowid
        connection.close()

        return redirect(url_for("event_details", event_id=event_id))

    return render_template("create_event.html")


if __name__ == "__main__":
    app.run(debug=True, port=5001)