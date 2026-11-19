# Attendance tracking

- Run `python database.py` once to add the attendance columns to your existing SQLite database. This migration is safe to rerun.
- Log in as an approved organiser, then choose **Attendance** in the navigation.
- Once an event has started, mark each registration as attended. You can undo an accidental confirmation.
- The participant dashboard shows confirmed events attended and the total attendee places in confirmed bookings.
- Guest bookings without `user_id` can be marked attended, but cannot contribute to a participant account dashboard.
- Existing bookings default to **not confirmed**; attendance is never inferred from a past event.
- Any approved organiser can currently manage attendance for all events because this app does not track event ownership.
- A registration is a booking, not a separate record for every attendee. Marking a booking confirms its whole party; individual guest attendance is not tracked.
- Keep your existing `instance/cleanup.db` and `.git` directory. Do not overwrite them.
