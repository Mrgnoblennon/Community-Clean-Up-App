# Main-branch cleanup – 20 November 2026

## Fixes applied
- Resolved Git merge conflicts in `seed_test_data.py`, keeping the newer tracked demo-event implementation and its CLI options.
- Resolved conflicting attendance CSS while retaining the attendance-event styles.
- Resolved the demo-events README conflict, retaining the newer 30-event instructions.
- Resolved conflicting demo credential JSON using the password that matches the existing demo organiser account.
- Updated `.gitignore` to exclude local demo credentials and database backups from future commits.
- Kept the existing `app.py` and `create_event.html` functionality intact, including the US-04 attendance dashboard and the event time-range fix.

## Checks completed
- Python syntax compilation: all 5 Python scripts passed.
- Merge conflict scan: no unresolved markers in source, templates or documentation.
- Flask template `url_for` endpoint references: no missing named routes found by static inspection.
- SQLite `PRAGMA integrity_check`: OK.

## Limits
- Flask/Werkzeug are unavailable in this review environment, so end-to-end browser and Flask runtime tests could not be run here.
- US-05 Business Rewards has **not** been implemented in this cleanup ZIP.
- The existing `instance/cleanup.db` is preserved. This ZIP includes local database data and demo credentials; keep it private.
- The `.git` history and macOS metadata were excluded to keep the ZIP clean.

## Run on your Mac
```bash
cd Community-Clean-Up-App
python3 -m pip install -r requirements.txt
export FLASK_SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
ENABLE_ATTENDANCE_TEST_MODE=1 python3 app.py
```

For repeatable demo data: `python3 seed_test_data.py --count 30`. Back up your database before testing changes.
