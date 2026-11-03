from flask import Flask, render_template, request, redirect, url_for
import sqlite3

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










if __name__ == "__main__":
    app.run(debug=True, port=5001)