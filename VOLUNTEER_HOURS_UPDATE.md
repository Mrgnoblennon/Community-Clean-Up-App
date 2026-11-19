# Community Impact: Volunteer Hours

The Participant Dashboard now calculates Community Impact as the sum of scheduled event durations for confirmed attendance records linked to the participant account. It does not multiply by attendee_count.

- Example: one confirmed 09:00-11:00 event = 1 Event Attended and 2 Volunteer Hours.
- Supports HH:MM-HH:MM and HH:MM–HH:MM ranges, including overnight ranges.
- Events with only a start time or invalid time range contribute 0 hours until a duration is available.
- This is an estimate based on scheduled event length, not independently verified hours worked.
- Existing database and attendance records are retained. No migration needed.

On macOS, keep instance/cleanup.db, then start with:

    ENABLE_ATTENDANCE_TEST_MODE=1 python3 app.py

Test: confirm an account-linked registration, refresh participant dashboard, and undo confirmation to verify both metrics revert.
