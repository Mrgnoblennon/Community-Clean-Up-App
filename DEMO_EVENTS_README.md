# Demo events

<<<<<<< HEAD
Run `python database.py` then `python seed_test_data.py` from the project root.

Adds 200 fictional events in 30 Australian locations. Reruns skip existing demo event names. All events are marked `[DEMO AU ...]`; no real records are changed.

All events begin with zero registrations. Full event testing requires creating bookings through the app.
=======
The generator now creates **30 fictional Australian events** by default (with past, future and fully booked examples), rather than 200. Existing demo events are not removed unless you explicitly run:

```bash
python3 seed_test_data.py --count 30 --reduce-demo
```

This preserves manually created events and demo events with non-demo bookings. See `SMALL_DEMO_SETUP.md`.
>>>>>>> US-04-track-stats
