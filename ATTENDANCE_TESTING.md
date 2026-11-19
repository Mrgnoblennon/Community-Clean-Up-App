# Attendance testing (macOS)

Run from the project folder:

```bash
python3 database.py
ENABLE_ATTENDANCE_TEST_MODE=1 python3 app.py
```

The site uses http://127.0.0.1:5001 by default. If you already set `FLASK_SECRET_KEY`, keep it set. Otherwise set a local development-only secret first:

```bash
export FLASK_SECRET_KEY="local-development-only-secret-change-me"
```

1. Register or log in as a participant, then join a future event while signed in.
2. Log out and sign in as an approved organiser.
3. Open Attendance. All events appear, even those with no bookings.
4. Find your future event, click **Simulate Event Started**, then **Confirm Attendance** for your linked participant booking.
5. Log in as the participant and check **Events Attended** increased by one.
6. As organiser, undo attendance and check the participant count decreases.

**Important:** Simulation is enabled only with the environment variable and from localhost. The simulated start is stored in the organiser session, not in the event's date. Attendance confirmations themselves are saved in SQLite. Undo confirmations after testing. Do not enable test mode in production. Events are not yet assigned to individual organisers, so any approved organiser can see them.
