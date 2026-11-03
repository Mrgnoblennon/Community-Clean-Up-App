from flask import Flask, render_template
import sqlite3

app = Flask(__name__)

@app.route("/")
def home():
  return render_template("index.html")

@app.route("/events")
def events():
    connection = sqlite3.connect("instance/cleanup.db")
    connection.row_factory = sqlite3.Row

    cursor = connection.cursor()
    cursor.execute("SELECT * FROM events")

    cleanup_events = cursor.fetchall()
    connection.close()

    return render_template("events.html", events=cleanup_events)

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
    return "Registration route working!"

if __name__ == "__main__":
    app.run(debug=True)