import re
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import date, datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import secrets, os , sqlite3
 
app = Flask(__name__)


@app.context_processor
def inject_current_user():

    user_id = session.get("participant_id")
    role = "participant"

    if not user_id:
        user_id = session.get("organiser_id")
        role = "organiser"

    if not user_id:
        return {"current_user": None}

    connection = sqlite3.connect("instance/cleanup.db")
    connection.row_factory = sqlite3.Row

    user = connection.execute("""
        SELECT id, name, email, role, is_admin
        FROM users
        WHERE id = ? AND role = ?
    """, (user_id, role)).fetchone()

    connection.close()

    return {"current_user": dict(user) if user else None}


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
        "SELECT * FROM events WHERE name LIKE ? OR location LIKE ?",
        (f"%{search}%", f"%{search}%",)
    )

    cleanup_events = cursor.fetchall()
    connection.close()
    
    
    map_events = []

    for event in cleanup_events:
        if event["latitude"] is None or event["longitude"] is None:
            continue

        event_start = datetime.strptime(
            f"{event['date']} {event['time'].split('-')[0].strip()}",
            "%Y-%m-%d %H:%M"
        )

        spaces_left = max(0, event["capacity"] - event["registered"])
        has_started = event_start <= datetime.now()

        map_events.append({
            "id": event["id"],
            "name": event["name"],
            "date": event["date"],
            "time": event["time"],
            "location": event["location"],
            "description": event["description"] or "No description provided.",
            "latitude": event["latitude"],
            "longitude": event["longitude"],
            "spaces_left": spaces_left,
            "has_started": has_started,
            "is_full": spaces_left == 0,
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
    
    event_start = datetime.strptime(
        f"{event['date']} {event['time'].split('-')[0].strip()}",
        "%Y-%m-%d %H:%M"
    )

    event_has_started = event_start <= datetime.now()

    return render_template(
        "event_details.html",
        event=event,
        event_has_started=event_has_started
    )


@app.route("/events/<int:event_id>/join", methods=["POST"])
def join_event(event_id):
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()

    try:
        attendee_count = int(request.form.get("attendee_count", "1"))
    except ValueError:
        return "Please enter a valid attendee count", 400

    if not name or not email:
        return "Name and email are required", 400

    if attendee_count < 1:
        return "You must register at least one attendee", 400

    connection = sqlite3.connect("instance/cleanup.db")
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    try:
        # Lock the database for this registration transaction
        cursor.execute("BEGIN IMMEDIATE")

        event = cursor.execute("""
            SELECT capacity, registered, date, time
            FROM events
            WHERE id = ?
        """, (event_id,)).fetchone()

        if event is None:
            return "Event not found", 404

        event_start = datetime.strptime(
            f"{event['date']} {event['time'].split('-')[0].strip()}",
            "%Y-%m-%d %H:%M"
        )

        if event_start <= datetime.now():
            return "This event has already started or finished", 400

        # Check for an existing registration first
        existing = cursor.execute("""
            SELECT id FROM registrations
            WHERE event_id = ? AND LOWER(email) = ?
        """, (event_id, email)).fetchone()

        if existing:
            return redirect(url_for("already_registered", event_id=event_id))

        spaces_left = event["capacity"] - event["registered"]

        if attendee_count > spaces_left:
            return (
                f"Only {spaces_left} spaces remain. "
                "Please reduce your attendee count.",
                400
            )

        
        # Link the booking to the logged-in participant
        participant_id = session.get("participant_id")
        registration_user_id = None

        if participant_id:
            participant = cursor.execute("""
                SELECT id, email
                FROM users
                WHERE id = ? AND role = 'participant'
            """, (participant_id,)).fetchone()

            if participant is None:
                return "Participant account not found", 403

            # Prevent linking another person's email
            if email != participant["email"].lower():
                return "Please use your account email when registering", 400

            registration_user_id = participant["id"]

        cursor.execute("""
            INSERT INTO registrations
                (event_id, name, email, attendee_count, user_id)
            VALUES (?, ?, ?, ?, ?)
        """, (
            event_id,
            name,
            email,
            attendee_count,
            registration_user_id
        ))


        cursor.execute("""
            UPDATE events
            SET registered = registered + ?
            WHERE id = ?
        """, (attendee_count, event_id))

        connection.commit()

    except sqlite3.IntegrityError:
        connection.rollback()
        return redirect(url_for("already_registered", event_id=event_id))

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
        if request.method == "POST":
            cursor.execute("BEGIN IMMEDIATE")

        # Only allow access to the verified user's booking
        registration = cursor.execute("""
            SELECT *
            FROM registrations
            WHERE id = ? AND LOWER(email) = ?
        """, (registration_id, verified_email.lower())).fetchone()

        if registration is None:
            return "Registration not found or access denied", 403

        # Get current event capacity
        event = cursor.execute("""
            SELECT capacity, registered, date, time
            FROM events
            WHERE id = ?
        """, (registration["event_id"],)).fetchone()

        if event is None:
            return "Event not found", 404

        if request.method == "POST":
            name = request.form.get("name", "").strip()

            try:
                attendee_count = int(request.form.get("attendee_count", ""))
            except (ValueError, TypeError):
                return "Please enter a valid attendee count", 400

            if not name:
                return "Name is required", 400

            if attendee_count < 1:
                return "You must have at least one attendee", 400

            # Don't allow changing bookings after an event starts
            event_start = datetime.strptime(
                f"{event['date']} {event['time'].split('-')[0].strip()}",
                "%Y-%m-%d %H:%M"
            )

            if event_start <= datetime.now():
                return "This event has already started", 400

            # Calculate the difference from the original booking
            difference = attendee_count - registration["attendee_count"]

            # Check capacity when increasing a booking
            if difference > 0:
                spaces_left = event["capacity"] - event["registered"]

                if difference > spaces_left:
                    return (
                        f"Only {spaces_left} additional spaces are available.",
                        400
                    )

            # Update booking details
            cursor.execute("""
                UPDATE registrations
                SET name = ?, attendee_count = ?
                WHERE id = ? AND LOWER(email) = ?
            """, (
                name,
                attendee_count,
                registration_id,
                verified_email.lower()
            ))

            # Adjust event attendance by the difference
            cursor.execute("""
                UPDATE events
                SET registered = registered + ?
                WHERE id = ?
            """, (difference, registration["event_id"]))

            connection.commit()

            return redirect(url_for("my_registrations", updated=1))

        return render_template(
            "edit_registration.html",
            registration=registration,
            max_attendees=(
                registration["attendee_count"]
                + max(0, event["capacity"] - event["registered"])
            )
        )

    except sqlite3.Error:
        connection.rollback()
        raise

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
                events.location,
                registrations.attendee_count,
                events.registered,
                events.capacity
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
            events.location,
            registrations.attendee_count,
            events.registered,
            events.capacity
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

    try:
        # Start transaction to keep registration and capacity in sync
        cursor.execute("BEGIN IMMEDIATE")

        # Find the booking belonging to the verified email
        cursor.execute("""
            SELECT event_id, attendee_count
            FROM registrations
            WHERE id = ? AND LOWER(email) = ?
        """, (registration_id, verified_email.lower()))

        registration = cursor.fetchone()

        if registration is None:
            return "Registration not found or access denied.", 403

        event_id, attendee_count = registration

        # Delete the entire booking
        cursor.execute("""
            DELETE FROM registrations
            WHERE id = ? AND LOWER(email) = ?
        """, (registration_id, verified_email.lower()))

        # Release every space reserved by this booking
        cursor.execute("""
            UPDATE events
            SET registered = MAX(0, registered - ?)
            WHERE id = ?
        """, (attendee_count, event_id))

        connection.commit()

    except sqlite3.Error:
        connection.rollback()
        raise

    finally:
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

    # Check organiser approval
    connection = sqlite3.connect("instance/cleanup.db")
    connection.row_factory = sqlite3.Row

    organiser = connection.execute("""
        SELECT id
        FROM users
        WHERE id = ?
          AND role = 'organiser'
          AND approved = 1
    """, (organiser_id,)).fetchone()

    connection.close()

    if organiser is None:
        session.pop("organiser_id", None)
        return redirect(url_for("organiser_login"))

    # Display the form
    if request.method == "GET":
        return render_template(
            "create_event.html",
            form={},
            error=None
        )

    # Preserve submitted values when errors occur
    form = request.form

    def form_error(message):
        return render_template(
            "create_event.html",
            form=form,
            error=message
        ), 400

    # Collect form data
    name = form.get("name", "").strip()
    location = form.get("location", "").strip()
    event_date = form.get("date", "").strip()
    start_time = form.get("start_time", "").strip()
    end_time = form.get("end_time", "").strip()
    description = form.get("description", "").strip()
    equipment = form.get("equipment", "").strip()

    # Validate event name
    if not name:
        return form_error(
            "Please enter a name for your clean-up event."
        )

    # Validate location
    if not location:
        return form_error(
            "Please enter the location of your event."
        )

    # Validate map selection
    latitude_value = form.get("latitude", "").strip()
    longitude_value = form.get("longitude", "").strip()

    if not latitude_value or not longitude_value:
        return form_error(
            "Please select your event location by clicking on the map."
        )

    try:
        latitude = float(latitude_value)
        longitude = float(longitude_value)
    except ValueError:
        return form_error(
            "The selected map location is invalid. Please choose another point."
        )

    # Check coordinates
    import math

    if (
        not math.isfinite(latitude)
        or not math.isfinite(longitude)
        or not (-90 <= latitude <= 90)
        or not (-180 <= longitude <= 180)
    ):
        return form_error(
            "Please select a valid location on the map."
        )

    # Validate date
    if not event_date:
        return form_error(
            "Please select a date for your event."
        )

    try:
        parsed_date = date.fromisoformat(event_date)
    except ValueError:
        return form_error(
            "Please enter a valid event date."
        )

    # Validate start and end times
    if not start_time or not end_time:
        return form_error(
            "Please select a start and end time."
        )

    try:
        parsed_start = datetime.strptime(start_time, "%H:%M").time()
        parsed_end = datetime.strptime(end_time, "%H:%M").time()
    except ValueError:
        return form_error(
            "Please enter valid event times."
        )

    if parsed_end <= parsed_start:
        return form_error(
            "End time must be after start time."
        )

    # Prevent past events
    event_start = datetime.combine(
        parsed_date, parsed_start
    )

    if event_start <= datetime.now():
        return form_error(
            "Your event must start in the future. "
            "Please choose a later date or time."
        )

    # Store both times in existing column
    event_time = f"{start_time}-{end_time}"

    # Validate participant capacity
    capacity_value = form.get("capacity", "").strip()

    if not capacity_value:
        return form_error(
            "Please enter the maximum number of participants."
        )

    try:
        capacity = int(capacity_value)
    except ValueError:
        return form_error(
            "Participant limit must be a valid whole number."
        )

    if capacity < 1:
        return form_error(
            "Your event must allow at least one participant."
        )

    # Validate safety checklist
    safety_items = [
        "safety_weather",
        "safety_hazards",
        "safety_equipment",
        "safety_emergency",
        "safety_disposal"
    ]

    missing_safety = [
        item for item in safety_items
        if form.get(item) != "on"
    ]

    if missing_safety:
        return form_error(
            "Please complete all five safety checklist "
            "requirements before creating your event."
        )

    # Save the event
    connection = sqlite3.connect("instance/cleanup.db")

    try:
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO events (
                name,
                location,
                latitude,
                longitude,
                date,
                time,
                capacity,
                registered,
                description,
                equipment,
                safety_instructions,
                organiser_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
        """, (
            name,
            location,
            latitude,
            longitude,
            parsed_date.isoformat(),
            event_time,
            capacity,
            description,
            equipment,
            "All five safety requirements confirmed",
            organiser_id
        ))

        event_id = cursor.lastrowid
        connection.commit()

    except sqlite3.Error:
        connection.rollback()
        app.logger.exception("Event creation failed")
        return form_error(
            "We couldn't save your event right now. "
            "Please try again."
        )

    finally:
        connection.close()

    return redirect(
        url_for("event_created", event_id=event_id)
    )


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


@app.route("/register-participant", methods=["GET", "POST"])
def register_participant():

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
            cursor = connection.cursor()

            cursor.execute("""
                INSERT INTO users
                    (name, email, password_hash, role, approved)
                VALUES (?, ?, ?, 'participant', 1)
            """, (name, email, password_hash))

            connection.commit()

        except sqlite3.IntegrityError:
            return "An account with this email already exists", 400

        finally:
            connection.close()

        return redirect(url_for("participant_login"))

    return render_template("register_participant.html")


@app.route("/participant-login", methods=["GET", "POST"])
def participant_login():

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        connection = sqlite3.connect("instance/cleanup.db")
        connection.row_factory = sqlite3.Row

        user = connection.execute("""
            SELECT * FROM users
            WHERE email = ? AND role = 'participant'
        """, (email,)).fetchone()

        connection.close()

        if user is None or not check_password_hash(user["password_hash"], password):
            return "Incorrect email or password", 401

        session.clear()
        session["participant_id"] = user["id"]

        return redirect(url_for("participant_dashboard"))

    return render_template("participant_login.html")


@app.route("/participant-logout", methods=["POST"])
def participant_logout():
    session.clear()
    return redirect(url_for("home"))



@app.route("/participant-dashboard")
def participant_dashboard():
    participant_id = session.get("participant_id")

    if not participant_id:
        return redirect(url_for("participant_login"))

    connection = sqlite3.connect("instance/cleanup.db")
    connection.row_factory = sqlite3.Row

    user = connection.execute("""
        SELECT id, name, email
        FROM users
        WHERE id = ? AND role = 'participant'
    """, (participant_id,)).fetchone()

    if user is None:
        connection.close()
        session.clear()
        return redirect(url_for("participant_login"))

    upcoming_events = connection.execute("""
        SELECT
            events.id,
            events.name,
            events.date,
            events.time,
            events.location,
            registrations.attendee_count
        FROM registrations
        JOIN events ON registrations.event_id = events.id
        WHERE registrations.user_id = ?
        ORDER BY events.date, events.time
    """, (participant_id,)).fetchall()

<<<<<<< HEAD
    # Count confirmed attendance, not future bookings
    attendance = connection.execute("""
        SELECT COUNT(*) AS attended_events,
               COALESCE(SUM(attendee_count), 0) AS confirmed_places
        FROM registrations
        WHERE user_id = ? AND attended = 1
    """, (participant_id,)).fetchone()
=======
    # Count confirmed events and their scheduled volunteer hours
    confirmed_events = connection.execute("""
        SELECT events.date, events.time
        FROM registrations
        JOIN events ON events.id = registrations.event_id
        WHERE registrations.user_id = ? AND registrations.attended = 1
    """, (participant_id,)).fetchall()

    volunteer_minutes = 0
    for event in confirmed_events:
        # Time ranges use HH:MM-HH:MM; single start times have no known duration
        time_range = re.fullmatch(
            r"\s*(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})\s*",
            event["time"] or ""
        )
        if not time_range:
            continue
        try:
            start = datetime.strptime(time_range.group(1), "%H:%M")
            end = datetime.strptime(time_range.group(2), "%H:%M")
        except ValueError:
            continue
        minutes = int((end - start).total_seconds() / 60)
        if minutes < 0:
            minutes += 24 * 60  # Events can run past midnight
        volunteer_minutes += minutes

    volunteer_hours = round(volunteer_minutes / 60, 2)
>>>>>>> US-04-track-stats

    connection.close()

    upcoming = []
    for event in upcoming_events:
        try:
            start_time = datetime.strptime(
                f"{event['date']} {event['time'].split('-')[0].strip()}",
                "%Y-%m-%d %H:%M"
            )
            if start_time > datetime.now():
                upcoming.append(event)
        except (ValueError, AttributeError):
            continue

    return render_template(
        "participant_dashboard.html",
        user=user,
        upcoming_events=upcoming,
        upcoming_count=len(upcoming),
<<<<<<< HEAD
        attended_count=attendance["attended_events"],
        confirmed_places=attendance["confirmed_places"]
    )


# Organisers can confirm attendance after an event starts
=======
        attended_count=len(confirmed_events),
        volunteer_hours=volunteer_hours
    )


# Organisers can review all events and confirm attendance after they start
>>>>>>> US-04-track-stats
@app.route("/organiser/attendance", methods=["GET", "POST"])
def organiser_attendance():
    organiser_id = session.get("organiser_id")
    if not organiser_id:
        return redirect(url_for("organiser_login"))

    connection = sqlite3.connect("instance/cleanup.db")
    connection.row_factory = sqlite3.Row
    organiser = connection.execute("""
<<<<<<< HEAD
        SELECT id FROM users
        WHERE id = ? AND role = 'organiser' AND approved = 1
    """, (organiser_id,)).fetchone()

=======
        SELECT id, is_admin FROM users
        WHERE id = ? AND role = 'organiser' AND approved = 1
    """, (organiser_id,)).fetchone()
>>>>>>> US-04-track-stats
    if not organiser:
        connection.close()
        session.pop("organiser_id", None)
        return redirect(url_for("organiser_login"))

<<<<<<< HEAD
    # Use a session token for attendance updates
    if "attendance_token" not in session:
        session["attendance_token"] = secrets.token_urlsafe(32)

    error = None
    if request.method == "POST":
        if not secrets.compare_digest(
            request.form.get("attendance_token", ""), session["attendance_token"]
        ):
            connection.close()
            return "Invalid request", 400

=======
    if "attendance_token" not in session:
        session["attendance_token"] = secrets.token_urlsafe(32)

    # Explicitly opt in to test mode; never enable on a deployed server
    test_mode = os.environ.get("ENABLE_ATTENDANCE_TEST_MODE") == "1" and request.remote_addr in ("127.0.0.1", "::1")
    simulated = set(session.get("simulated_started_events", [])) if test_mode else set()

    if request.method == "POST":
        if not secrets.compare_digest(request.form.get("attendance_token", ""), session["attendance_token"]):
            connection.close()
            return "Invalid request", 400

        action = request.form.get("action", "attendance")
        if action == "simulate":
            if not test_mode:
                connection.close()
                return "Test mode is disabled", 403
            try:
                event_id = int(request.form.get("event_id", ""))
            except ValueError:
                connection.close()
                return "Invalid event", 400
            exists = connection.execute(
                "SELECT 1 FROM events WHERE id = ? AND (organiser_id = ? OR ? = 1)",
                (event_id, organiser_id, organiser["is_admin"])
            ).fetchone()
            if not exists:
                connection.close()
                return "Event not found", 404
            if event_id in simulated:
                simulated.remove(event_id)
            else:
                simulated.add(event_id)
            session["simulated_started_events"] = sorted(simulated)
            connection.close()
            return redirect(url_for("organiser_attendance"))

>>>>>>> US-04-track-stats
        try:
            registration_id = int(request.form.get("registration_id", ""))
            attended = int(request.form.get("attended", ""))
            if attended not in (0, 1):
                raise ValueError
        except (ValueError, TypeError):
            connection.close()
            return "Invalid attendance update", 400

<<<<<<< HEAD
        # Only allow attendance changes once the event has started
        registration = connection.execute("""
            SELECT registrations.id, events.date, events.time
            FROM registrations
            JOIN events ON events.id = registrations.event_id
            WHERE registrations.id = ?
        """, (registration_id,)).fetchone()

        if not registration:
            connection.close()
            return "Registration not found", 404

=======
        registration = connection.execute("""
            SELECT registrations.id, events.id AS event_id, events.date, events.time
            FROM registrations JOIN events ON events.id = registrations.event_id
            WHERE registrations.id = ?
              AND (events.organiser_id = ? OR ? = 1)
        """, (registration_id, organiser_id, organiser["is_admin"])).fetchone()
        if not registration:
            connection.close()
            return "Registration not found", 404
>>>>>>> US-04-track-stats
        try:
            start_time = datetime.strptime(
                f"{registration['date']} {registration['time'].split('-')[0].strip()}",
                "%Y-%m-%d %H:%M"
            )
        except (ValueError, AttributeError):
            connection.close()
            return "Invalid event date or time", 400
<<<<<<< HEAD

        if start_time > datetime.now():
=======
        if start_time > datetime.now() and registration["event_id"] not in simulated:
>>>>>>> US-04-track-stats
            connection.close()
            return "Attendance cannot be recorded before an event starts", 400

        connection.execute("""
            UPDATE registrations
            SET attended = ?, attendance_marked_at = ?, attendance_marked_by = ?
            WHERE id = ?
        """, (
            attended,
            datetime.now().isoformat(timespec="seconds") if attended else None,
            organiser_id if attended else None,
            registration_id
        ))
        connection.commit()
        connection.close()
        return redirect(url_for("organiser_attendance", updated=1))

<<<<<<< HEAD
    # Show bookings for events that have started
    rows = connection.execute("""
        SELECT registrations.id AS registration_id, registrations.name AS participant_name,
               registrations.email, registrations.attendee_count,
               registrations.attended, registrations.user_id,
               events.id AS event_id, events.name AS event_name,
               events.date, events.time, events.location
        FROM registrations
        JOIN events ON events.id = registrations.event_id
        ORDER BY events.date DESC, events.time DESC, registrations.id
    """).fetchall()
    connection.close()

    started_events = []
    for row in rows:
        try:
            start_time = datetime.strptime(
                f"{row['date']} {row['time'].split('-')[0].strip()}",
=======
    # Show every event, including future events and those without registrations
    events = connection.execute("""
        SELECT id, name, date, time, location FROM events
        WHERE organiser_id = ? OR ? = 1
        ORDER BY date DESC, time DESC, id DESC
    """, (organiser_id, organiser["is_admin"])).fetchall()
    rows = connection.execute("""
        SELECT id AS registration_id, event_id, name AS participant_name,
               email, attendee_count, attended, user_id
        FROM registrations
        WHERE event_id IN (SELECT id FROM events WHERE organiser_id = ? OR ? = 1)
        ORDER BY id
    """, (organiser_id, organiser["is_admin"])).fetchall()
    connection.close()
    by_event = {}
    for row in rows:
        by_event.setdefault(row["event_id"], []).append(dict(row))

    event_groups = []
    for event in events:
        try:
            start_time = datetime.strptime(
                f"{event['date']} {event['time'].split('-')[0].strip()}",
>>>>>>> US-04-track-stats
                "%Y-%m-%d %H:%M"
            )
        except (ValueError, AttributeError):
            continue
<<<<<<< HEAD
        if start_time <= datetime.now():
            started_events.append(row)

    return render_template(
        "organiser_attendance.html",
        registrations=started_events,
        attendance_token=session["attendance_token"]
=======
        event_groups.append({
            **dict(event),
            "registrations": by_event.get(event["id"], []),
            "can_confirm": start_time <= datetime.now() or event["id"] in simulated,
            "simulated": event["id"] in simulated
        })

    return render_template(
        "organiser_attendance.html",
        event_groups=event_groups,
        attendance_token=session["attendance_token"],
        test_mode=test_mode
>>>>>>> US-04-track-stats
    )


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

@app.route("/organiser-logout", methods=["POST"])
def organiser_logout():
    session.pop("organiser_id", None)
    return redirect(url_for("home"))

@app.route("/events/<int:event_id>/already-registered")
def already_registered(event_id):
    connection = sqlite3.connect("instance/cleanup.db")
    connection.row_factory = sqlite3.Row

    event = connection.execute(
        "SELECT * FROM events WHERE id = ?",
        (event_id,)
    ).fetchone()

    connection.close()

    if event is None:
        return "Event not found", 404

    return render_template("already_registered.html", event=event)

@app.route("/admin", methods=["GET", "POST"])
def admin_dashboard():
    organiser_id = session.get("organiser_id")
    if not organiser_id:
        return redirect(url_for("organiser_login"))
    connection = sqlite3.connect("instance/cleanup.db")
    connection.row_factory = sqlite3.Row
    admin = connection.execute("SELECT id FROM users WHERE id=? AND role='organiser' AND is_admin=1", (organiser_id,)).fetchone()
    if not admin:
        connection.close()
        return "Admin access required", 403
    message = None
    if request.method == "POST":
        try:
            target_id = int(request.form.get("user_id", "0"))
        except ValueError:
            target_id = 0
        action = request.form.get("action")
        if action in ("approve", "revoke"):
            connection.execute("UPDATE users SET approved=? WHERE id=? AND role='organiser' AND is_admin=0", (1 if action == "approve" else 0, target_id))
            connection.commit()
            message = "Organiser approval updated."
    organisers = connection.execute("SELECT id,name,email,approved FROM users WHERE role='organiser' AND is_admin=0 ORDER BY id DESC").fetchall()
    connection.close()
    return render_template("admin.html", organisers=organisers, message=message)


if __name__ == "__main__":
    app.run(debug=True, port=5001)

<<<<<<< HEAD
@app.route("/admin", methods=["GET", "POST"])
def admin_dashboard():
    organiser_id = session.get("organiser_id")
    if not organiser_id:
        return redirect(url_for("organiser_login"))
    connection = sqlite3.connect("instance/cleanup.db")
    connection.row_factory = sqlite3.Row
    admin = connection.execute("SELECT id FROM users WHERE id=? AND role='organiser' AND is_admin=1", (organiser_id,)).fetchone()
    if not admin:
        connection.close()
        return "Admin access required", 403
    message = None
    if request.method == "POST":
        try:
            target_id = int(request.form.get("user_id", "0"))
        except ValueError:
            target_id = 0
        action = request.form.get("action")
        if action in ("approve", "revoke"):
            connection.execute("UPDATE users SET approved=? WHERE id=? AND role='organiser' AND is_admin=0", (1 if action == "approve" else 0, target_id))
            connection.commit()
            message = "Organiser approval updated."
    organisers = connection.execute("SELECT id,name,email,approved FROM users WHERE role='organiser' AND is_admin=0 ORDER BY id DESC").fetchall()
    connection.close()
    return render_template("admin.html", organisers=organisers, message=message)
=======
>>>>>>> US-04-track-stats
