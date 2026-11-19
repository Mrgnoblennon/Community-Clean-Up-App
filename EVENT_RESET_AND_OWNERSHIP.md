# Event reset and ownership update

From the project root on macOS, stop Flask first and run:

```bash
python3 database.py
python3 reset_events.py --confirm-delete-all-events
python3 seed_test_data.py --count 30
ENABLE_ATTENDANCE_TEST_MODE=1 python3 app.py
```

The reset **deletes ALL events, ALL registrations and ALL recorded attendance**, including manually created events. It automatically creates a timestamped backup of `instance/cleanup.db` before deleting anything. User accounts remain unchanged.

The generator creates 30 naturally named Australian events, some full and some past. New generated events belong to the approved sample organiser `demo.organiser@example.invalid`. New events created through the web form belong to the currently signed-in organiser. Admin organisers can manage attendance for all events. Other organisers can only see and manage attendance for their own events. Older, unassigned events remain visible to admins only on the attendance page.

`database.py` no longer automatically adds built-in sample events. To intentionally restore those original samples, run `SEED_SAMPLE_EVENTS=1 python3 database.py`.

The schema adds nullable `events.organiser_id` with an index. Existing event rows are not assigned automatically. The public Explore page still shows all events, regardless of ownership.

This update scopes **attendance** permissions, not every possible event editing/deleting action; those features require equivalent ownership checks if introduced later. Demo accounts retain their existing passwords in `instance/demo_credentials.json`.
