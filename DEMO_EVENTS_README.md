# Demo events

The generator now creates **30 fictional Australian events** by default (with past, future and fully booked examples), rather than 200. Existing demo events are not removed unless you explicitly run:

```bash
python3 seed_test_data.py --count 30 --reduce-demo
```

This preserves manually created events and demo events with non-demo bookings. See `SMALL_DEMO_SETUP.md`.

