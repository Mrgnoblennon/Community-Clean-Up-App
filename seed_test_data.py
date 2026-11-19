"""Add repeatable demo clean-up events without changing real events."""
import argparse
import random
import sqlite3
import secrets
import json
from werkzeug.security import generate_password_hash
from datetime import date, timedelta
from pathlib import Path

# Test locations around Australia (approximate city-centre coordinates)
LOCATIONS = [
    ('Perth', 'WA', -31.9523, 115.8613), ('Fremantle', 'WA', -32.0569, 115.7439),
    ('Bunbury', 'WA', -33.3271, 115.6414), ('Albany', 'WA', -35.0269, 117.8837),
    ('Broome', 'WA', -17.9614, 122.2359), ('Geraldton', 'WA', -28.7744, 114.6146),
    ('Sydney', 'NSW', -33.8688, 151.2093), ('Newcastle', 'NSW', -32.9283, 151.7817),
    ('Wollongong', 'NSW', -34.4278, 150.8931), ('Byron Bay', 'NSW', -28.6474, 153.6020),
    ('Melbourne', 'VIC', -37.8136, 144.9631), ('Geelong', 'VIC', -38.1499, 144.3617),
    ('Ballarat', 'VIC', -37.5622, 143.8503), ('Bendigo', 'VIC', -36.7570, 144.2794),
    ('Brisbane', 'QLD', -27.4698, 153.0251), ('Gold Coast', 'QLD', -28.0167, 153.4000),
    ('Sunshine Coast', 'QLD', -26.6500, 153.0667), ('Cairns', 'QLD', -16.9203, 145.7710),
    ('Townsville', 'QLD', -19.2589, 146.8169), ('Toowoomba', 'QLD', -27.5598, 151.9507),
    ('Adelaide', 'SA', -34.9285, 138.6007), ('Mount Gambier', 'SA', -37.8318, 140.7792),
    ('Port Lincoln', 'SA', -34.7240, 135.8580), ('Darwin', 'NT', -12.4634, 130.8456),
    ('Alice Springs', 'NT', -23.6980, 133.8807), ('Hobart', 'TAS', -42.8821, 147.3272),
    ('Launceston', 'TAS', -41.4332, 147.1441), ('Devonport', 'TAS', -41.1767, 146.3515),
    ('Canberra', 'ACT', -35.2809, 149.1300), ('Queanbeyan', 'NSW', -35.3533, 149.2342),
]
ACTIVITIES = [
    ('Park Litter Pick', 'Help collect litter in public parkland.', 'Gloves, bags and closed shoes'),
    ('Riverbank Clean-Up', 'Remove rubbish from local waterways and riverbanks.', 'Gloves, bags and sturdy shoes'),
    ('Community Street Clean-Up', 'Collect litter from community streets and shared spaces.', 'Gloves, bags and high-visibility vest'),
    ('Coastal Clean-Up', 'Help remove litter from coastal public areas.', 'Gloves, bags and sun protection'),
    ('Bushland Care Day', 'Remove rubbish from bushland trails and public reserves.', 'Gloves, bags and sturdy shoes'),
]


def seed(count, database):
    if not database.is_file():
        raise SystemExit('Database not found. Run python database.py first from your project folder.')

    rng = random.Random(20261119)
    today = date.today()
    created = 0
    skipped = 0
    full_count = 0

    with sqlite3.connect(database) as connection:
        connection.execute('PRAGMA foreign_keys = ON')
        required = {'name', 'location', 'latitude', 'longitude', 'date', 'time', 'registered', 'capacity', 'description', 'equipment', 'safety_instructions'}
        columns = {row[1] for row in connection.execute('PRAGMA table_info(events)')}
        if not required.issubset(columns):
            raise SystemExit('Missing event columns. Run python database.py first.')

        for index in range(1, count + 1):
            city, state, lat, lon = LOCATIONS[(index - 1) % len(LOCATIONS)]
            activity, description, equipment = ACTIVITIES[(index - 1) % len(ACTIVITIES)]
            # Fixed IDs in event names make reruns safe without changing existing events
            name = f'[DEMO AU {index:03d}] {city} {activity}'
            exists = connection.execute('SELECT 1 FROM events WHERE name = ?', (name,)).fetchone()
            if exists:
                skipped += 1
                continue

            # Mix past, upcoming, full and available events for filter testing
            offset = rng.randint(-75, -1) if index % 5 == 0 else rng.randint(2, 120)
            event_date = (today + timedelta(days=offset)).isoformat()
            start_hour = rng.choice([7, 8, 9, 10, 13, 15])
            event_time = f'{start_hour:02d}:00-{start_hour + 2:02d}:00'
            capacity = rng.choice([10, 15, 20, 25, 30, 40])
            full = index % 7 == 0
            # Full demo events have fictional bookings that occupy every place.
            cursor = connection.execute('''
                INSERT INTO events
                (name, location, latitude, longitude, date, time, registered,
                 capacity, description, equipment, safety_instructions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                name, f'{city}, {state}, Australia', lat, lon, event_date, event_time,
                capacity if full else 0, capacity,
                f'[DEMO DATA] {description} This is a fictional event for app testing.',
                equipment,
                'Follow organiser instructions, wear enclosed shoes, and avoid hazardous items.'
            ))
            if full:
                event_id = cursor.lastrowid
                # Each fictional booking has a unique email; counts add up to capacity.
                portions = [capacity // 3, capacity // 3, capacity - 2 * (capacity // 3)]
                for booking_number, attendees in enumerate(portions, start=1):
                    connection.execute("""INSERT INTO registrations
                        (event_id, name, email, attendee_count)
                        VALUES (?, ?, ?, ?)""", (
                        event_id, f'Demo Guest {booking_number}',
                        f'demo-au-{index:03d}-{booking_number}@example.invalid', attendees
                    ))
                full_count += 1
            created += 1

    print(f'Added {created} demo events; skipped {skipped} already present.')
    print(f'New fully booked events: {full_count} (with matching fictional registrations).')
    print('Existing events and registrations were not modified.')




def seed_accounts(database):
    # Password is random and only stored locally, never in the downloadable ZIP.
    credential_path = database.parent / 'demo_credentials.json'
    if credential_path.exists():
        credentials = json.loads(credential_path.read_text())
    else:
        credentials = {'password': secrets.token_urlsafe(16)}
        credential_path.write_text(json.dumps(credentials, indent=2))
        try:
            credential_path.chmod(0o600)
        except OSError:
            pass

    accounts = [
        ('Demo Admin', 'demo.admin@example.invalid', 'organiser', 1, 1),
        ('Demo Organiser', 'demo.organiser@example.invalid', 'organiser', 1, 0),
        ('Demo Pending Organiser', 'demo.pending@example.invalid', 'organiser', 0, 0),
        ('Demo Participant', 'demo.participant@example.invalid', 'participant', 1, 0),
    ]
    created = 0
    with sqlite3.connect(database) as connection:
        columns = {row[1] for row in connection.execute('PRAGMA table_info(users)')}
        if 'is_admin' not in columns:
            raise SystemExit('Run python database.py first (missing admin column).')
        for name, email, role, approved, is_admin in accounts:
            exists = connection.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone()
            if exists:
                continue
            connection.execute('''INSERT INTO users (name,email,password_hash,role,approved,is_admin)
                VALUES (?,?,?,?,?,?)''', (name, email,
                generate_password_hash(credentials['password']), role, approved, is_admin))
            created += 1
    print(f'Created {created} demo accounts (existing accounts unchanged).')
    print('Demo login emails:')
    for _, email, role, approved, is_admin in accounts:
        print(f'  {email} — {"admin" if is_admin else role + (" (pending)" if not approved else "")}')
    print(f'Password for demo accounts: {credentials["password"]}')
    print(f'Credentials saved locally to: {credential_path}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Seed fictional Australian clean-up events')
    parser.add_argument('--count', type=int, default=200, help='Number of demo events (default: 200)')
    args = parser.parse_args()
    if not 1 <= args.count <= 2000:
        parser.error('--count must be between 1 and 2000')
    seed(args.count, Path(__file__).resolve().parent / 'instance' / 'cleanup.db')
    seed_accounts(Path(__file__).resolve().parent / 'instance' / 'cleanup.db')

