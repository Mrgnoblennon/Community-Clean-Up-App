"""Back up the SQLite database, then reset only events and registrations."""
from pathlib import Path
import argparse
import sqlite3
from datetime import datetime

ROOT = Path(__file__).resolve().parent
DB = ROOT / 'instance' / 'cleanup.db'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--confirm-delete-all-events', action='store_true')
    args = parser.parse_args()
    if not args.confirm_delete_all_events:
        parser.error('Add --confirm-delete-all-events to proceed. This deletes all events, bookings and attendance.')
    if not DB.is_file():
        parser.error('Database not found. Run python3 database.py first.')

    backup = DB.with_name('cleanup-before-event-reset-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.db')
    with sqlite3.connect(DB) as src, sqlite3.connect(backup) as dst:
        src.backup(dst)
    with sqlite3.connect(DB) as conn:
        conn.execute('PRAGMA foreign_keys=ON')
        with conn:
            registrations = conn.execute('SELECT COUNT(*) FROM registrations').fetchone()[0]
            events = conn.execute('SELECT COUNT(*) FROM events').fetchone()[0]
            conn.execute('DELETE FROM registrations')
            if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='seeded_events'").fetchone():
                conn.execute('DELETE FROM seeded_events')
            conn.execute('DELETE FROM events')
    print(f'Deleted {events} events and {registrations} registrations; user accounts preserved.')
    print(f'Backup saved: {backup}')


if __name__ == '__main__':
    main()
