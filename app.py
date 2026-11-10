from flask import Flask, render_template, request, redirect, url_for, session
from datetime import date, datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import secrets, os , sqlite3
 
app = Flask(__name__)

verification_codes = {}
app.secret_key = os.environ["FLASK_SECRET_KEY"]

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
    map_events = []

    for event in cleanup_events:
        if event["latitude"] is not None and event["longitude"] is not None:
            map_events.append({
                "id": event["id"],
                "name": event["name"],
                "date": event["date"],
                "latitude": event["latitude"],
                "longitude": event["longitude"],
                "url": url_for("event_details", event_id=event["id"])
            })

    return render_template(
        "events.html",
        events=cleanup_events,
        search=search,
        map_events=map_events
    )

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

        cursor.execute(
            "SELECT registered FROM events WHERE id = ?",
            (event_id,)
        )
        registered = cursor.fetchone()[0]

        if registered >= event[0]:
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

@app.route("/registrations/<int:registration_id>/edit", methods=["GET", "POST"])
def edit_registration(registration_id):
    verified_email = session.get("verified_email")

    if not verified_email:
        return redirect(url_for("my_registrations"))

    connection = sqlite3.connect("instance/cleanup.db")
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    try:
        # Only retrieve registrations belonging to the verified email
        cursor.execute("""
            SELECT *
            FROM registrations
            WHERE id = ? AND LOWER(email) = ?
        """, (registration_id, verified_email))

        registration = cursor.fetchone()

        if registration is None:
            return "Registration not found or access denied", 403

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()

            if not name or not email:
                return "Name and email are required", 400

            # Prevent duplicate registrations for the same event
            cursor.execute("""
                SELECT id
                FROM registrations
                WHERE event_id = ?
                  AND LOWER(email) = ?
                  AND id != ?
            """, (registration["event_id"], email, registration_id))

            if cursor.fetchone():
                return "Email already registered for this event", 400

            # Update only the verified participant's registration
            try:
                cursor.execute("""
                    UPDATE registrations
                    SET name = ?, email = ?
                    WHERE id = ? AND LOWER(email) = ?
                """, (name, email, registration_id, verified_email))

                connection.commit()

            except sqlite3.IntegrityError:
                return "Email already registered for this event", 400

            # A changed email must be verified again
            if email != verified_email:
                session.pop("verified_email", None)
                return redirect(url_for("my_registrations"))

            return redirect(url_for("my_registrations", updated=1))

        return render_template(
            "edit_registration.html",
            registration=registration
        )

    finally:
        connection.close()

@app.route("/my-registrations", methods=["GET", "POST"])
def my_registrations():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()

        if not email:
            return "Email address is required", 400

        code = str(secrets.randbelow(900000) + 100000)

        verification_codes[email] = {
            "code": code,
            "expires": datetime.now() + timedelta(minutes=10)
        }

        print(f"Verification code for {email}: {code}")

        return render_template(
            "my_registrations.html",
            message="Enter the verification code shown in your VS Code terminal.",
            show_verification=True,
            email=email,
        )

    verified_email = session.get("verified_email")

    if verified_email:
        connection = sqlite3.connect("instance/cleanup.db")
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                registrations.id AS registration_id,
                registrations.name AS participant_name,
                events.id AS event_id,
                events.name AS event_name,
                events.date,
                events.time,
                events.location
            FROM registrations
            JOIN events ON registrations.event_id = events.id
            WHERE LOWER(registrations.email) = ?
            ORDER BY events.date ASC
        """, (verified_email,))

        my_events = [dict(row) for row in cursor.fetchall()]
        connection.close()

        return render_template(
            "my_registrations.html",
            my_events=my_events,
            message=(
                "Registration updated successfully!"
                if request.args.get("updated") == "1"
                else None
            )
        )

    return render_template("my_registrations.html")

@app.route("/registrations/<int:registration_id>/confirm-cancel")
def confirm_cancellation(registration_id):
    verified_email = session.get("verified_email")

    if not verified_email:
        return redirect(url_for("my_registrations"))

    connection = sqlite3.connect("instance/cleanup.db")
    connection.row_factory = sqlite3.Row

    registration = connection.execute("""
        SELECT events.name AS event_name
        FROM registrations
        JOIN events ON registrations.event_id = events.id
        WHERE registrations.id = ?
        AND LOWER(registrations.email) = ?
    """, (registration_id, verified_email)).fetchone()

    connection.close()

    if registration is None:
        return "Registration not found or access denied.", 403

    return render_template(
        "confirm_cancellation.html",
        registration_id=registration_id,
        event_name=registration["event_name"]
    )

@app.route("/verify-registration", methods=["POST"])
def verify_registration():
    email = request.form.get("email", "").strip().lower()
    code = request.form.get("code", "").strip()

    saved = verification_codes.get(email)

    print("Submitted email:", repr(email))
    print("Submitted code:", repr(code))
    print("Stored verification:", saved)

    if saved is None:
        return "No verification code found. Request a new one.", 400

    if datetime.now() > saved["expires"]:
        verification_codes.pop(email, None)
        return "Verification code expired. Request a new one.", 400

    if not secrets.compare_digest(code, saved["code"]):
        return "Incorrect verification code", 400

    # Prevent the same code being reused
    verification_codes.pop(email, None)

    session["verified_email"] = email

    # Retrieve events belonging to the verified email
    connection = sqlite3.connect("instance/cleanup.db")
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            registrations.id AS registration_id,
            registrations.name AS participant_name,
            events.id AS event_id,
            events.name AS event_name,
            events.date,
            events.time,
            events.location
        FROM registrations
        JOIN events
            ON registrations.event_id = events.id
        WHERE registrations.email = ?
        ORDER BY events.date ASC
    """, (email,))

    my_events = [dict(row) for row in cursor.fetchall()]

    connection.close()

    return render_template(
        "my_registrations.html",
        message="Email verified successfully!",
        my_events=my_events
    )

@app.route("/registrations/<int:registration_id>/cancel", methods=["POST"])
def cancel_registration(registration_id):

    verified_email = session.get("verified_email")

    if not verified_email:
        return "Please verify your email first.", 403

    connection = sqlite3.connect("instance/cleanup.db")
    cursor = connection.cursor()

    # Find the registration belonging to the verified email
    cursor.execute("""
        SELECT event_id
        FROM registrations
        WHERE id = ? AND LOWER(email) = ?
    """, (registration_id, verified_email))

    registration = cursor.fetchone()

    if registration is None:
        connection.close()
        return "Registration not found or access denied.", 403

    event_id = registration[0]

    # Delete the registration
    cursor.execute("""
        DELETE FROM registrations
        WHERE id = ? AND LOWER(email) = ?
    """, (registration_id, verified_email))

    # Update the event's registered count
    cursor.execute("""
        UPDATE events
        SET registered = MAX(0, registered - 1)
        WHERE id = ?
    """, (event_id,))

    connection.commit()
    connection.close()

    return redirect(url_for("cancellation_success"))

@app.route("/cancellation-success")
def cancellation_success():
    if not session.get("verified_email"):
        return redirect(url_for("my_registrations"))

    return render_template("cancellation_success.html")

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
    organiser_id = session.get("organiser_id")  
    if not organiser_id:
        return redirect(url_for("organiser_login")) 
    connection = sqlite3.connect("instance/cleanup.db") 
    organiser = connection.execute("""
        SELECT id FROM users
        WHERE id = ?
          AND role = 'organiser'
          AND approved = 1
    """, (organiser_id,)).fetchone()    
    connection.close()  
    if organiser is None:
        session.pop("organiser_id", None)
        return redirect(url_for("organiser_login"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        location = request.form.get("location", "").strip()

        try:
            latitude = float(request.form.get("latitude", ""))
            longitude = float(request.form.get("longitude", ""))
        except (ValueError, TypeError):
            return "Valid coordinates are required", 400

        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            return "Coordinates are out of range", 400
        
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
            (name, location, latitude, longitude, date, time, capacity,
            registered, description, equipment, safety_instructions)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
        """, (
            name, location, latitude, longitude, event_date, time,
            capacity, description, equipment, "Safety checklist reviewed"
        ))
        connection.commit()
        event_id = cursor.lastrowid
        connection.close()
        return redirect(url_for("event_created", event_id=event_id))

    return render_template("create_event.html")

@app.route("/events/<int:event_id>/created")
def event_created(event_id):
    connection = sqlite3.connect("instance/cleanup.db")
    connection.row_factory = sqlite3.Row

    cursor = connection.cursor()
    cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
    event = cursor.fetchone()
    connection.close()

    if event is None:
        return "Event not found", 404

    return render_template("event_created.html", event=event)

@app.route("/register-organiser", methods=["GET", "POST"])
def register_organiser():

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            return "All fields are required", 400

        if len(password) < 8:
            return "Password must be at least 8 characters", 400

        password_hash = generate_password_hash(password)

        connection = sqlite3.connect("instance/cleanup.db")

        try:
            connection.execute("""
                INSERT INTO users
                    (name, email, password_hash, role, approved)
                VALUES (?, ?, ?, 'organiser', 0)
            """, (name, email, password_hash))

            connection.commit()

        except sqlite3.IntegrityError:
            return "An account with this email already exists", 400

        finally:
            connection.close()

        return render_template("organiser_pending.html")

    return render_template("register_organiser.html")

@app.route("/organiser-login", methods=["GET", "POST"])
def organiser_login():

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        connection = sqlite3.connect("instance/cleanup.db")
        connection.row_factory = sqlite3.Row

        user = connection.execute("""
            SELECT * FROM users
            WHERE email = ? AND role = 'organiser'
        """, (email,)).fetchone()

        connection.close()

        if user is None or not check_password_hash(user["password_hash"], password):
            return "Incorrect email or password", 401

        if not user["approved"]:
            return render_template("organiser_pending.html")

        session.clear()
        session["organiser_id"] = user["id"]

        return redirect(url_for("create_event"))

    return render_template("organiser_login.html")
if __name__ == "__main__":
    app.run(debug=True, port=5001)