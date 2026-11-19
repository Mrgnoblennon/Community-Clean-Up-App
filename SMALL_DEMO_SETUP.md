# Smaller demo dataset (30 events)

The demo generator now defaults to **30 events** across Australia, including past, upcoming and fully booked events. It retains all four demo accounts and all application features.

## Update your existing database on Mac

From the project folder, run:

```bash
python3 database.py
python3 seed_test_data.py --count 30 --reduce-demo
ENABLE_ATTENDANCE_TEST_MODE=1 python3 app.py
```

`--reduce-demo` deletes generated `[DEMO AU ...]` events numbered above 30 **only when they have no real participant registrations**. It deletes their generated fictional bookings too. Events you created manually and accounts are not removed. Demo events with real bookings are kept, so you may have slightly more than 30 events. Your original non-demo events also remain.

**Important:** The ZIP deliberately does not include `instance/cleanup.db`. Keep your existing database. Back it up before running the cleanup if you want to preserve every test booking.

Run `python3 seed_test_data.py` on later runs to keep the 30-event default without deleting other data.
