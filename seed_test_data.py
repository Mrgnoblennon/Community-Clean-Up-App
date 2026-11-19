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



# Internal tracking means event titles don't need a visible test-data label.
def setup_tracking(connection):
    connection.execute('''CREATE TABLE IF NOT EXISTS seeded_events (
        seed_key TEXT PRIMARY KEY,
        event_id INTEGER NOT NULL UNIQUE
    )''')


def old_seed_number(name):
    import re
    match = re.match(r'^\[DEMO AU\s+(\d+)\]\s*', name)
    return int(match.group(1)) if match else None


def clean_title(name):
    import re
    return re.sub(r'^\[DEMO(?: AU(?:\s+\d+)?)?\]\s*', '', name).strip()


def migrate_old_names(connection):
    # Rename only recognisable old seeded records, preserving manual titles.
    renamed = 0
    for event_id, name in connection.execute('SELECT id, name FROM events').fetchall():
        if not (name.startswith('[DEMO AU') or name.startswith('[DEMO]')):
            continue
        new_name = clean_title(name)
        if not new_name or new_name == name:
            continue
        connection.execute('UPDATE events SET name = ? WHERE id = ?', (new_name, event_id))
        index = old_seed_number(name)
        if index is not None:
            connection.execute('INSERT OR IGNORE INTO seeded_events(seed_key,event_id) VALUES (?,?)',
                               (f'au-{index:04d}', event_id))
        renamed += 1
    return renamed


def has_real_bookings(connection, event_id):
    cols = {row[1] for row in connection.execute('PRAGMA table_info(registrations)')}
    rows = connection.execute('SELECT * FROM registrations WHERE event_id=?', (event_id,)).fetchall()
    names = [row[1] for row in connection.execute('PRAGMA table_info(registrations)')]
    for row in rows:
        reg = dict(zip(names, row))
        email = str(reg.get('email') or '')
        if not (email.startswith('demo-au-') and email.endswith('@example.invalid')):
            return True
        if any(reg.get(field) is not None for field in ('user_id','participant_id') if field in cols):
            return True
    return False


def reduce_generated(connection, count):
    # Only delete entries explicitly tracked as generated, never manual events.
    removed = protected = 0
    for key, event_id in connection.execute('SELECT seed_key,event_id FROM seeded_events').fetchall():
        if not key.startswith('au-') or int(key[3:]) <= count:
            continue
        if has_real_bookings(connection, event_id):
            protected += 1
            continue
        connection.execute('DELETE FROM registrations WHERE event_id=?', (event_id,))
        connection.execute('DELETE FROM events WHERE id=?', (event_id,))
        connection.execute('DELETE FROM seeded_events WHERE seed_key=?', (key,))
        removed += 1
    return removed, protected


def seed(count, database, reduce=False):
    if not database.is_file():
        raise SystemExit('Database not found. Run python3 database.py first.')
    rng = random.Random(20261119)
    today = date.today()
    with sqlite3.connect(database) as connection:
        connection.execute('PRAGMA foreign_keys=ON')
        required = {'name','location','latitude','longitude','date','time','registered',
                    'capacity','description','equipment','safety_instructions'}
        columns = {row[1] for row in connection.execute('PRAGMA table_info(events)')}
        if not required.issubset(columns):
            raise SystemExit('Missing event columns. Run python3 database.py first.')
        setup_tracking(connection)
        # Every generated event belongs to the approved sample organiser.
        organiser = connection.execute("SELECT id FROM users WHERE email=? AND role='organiser' AND approved=1", ('demo.organiser@example.invalid',)).fetchone()
        if not organiser:
            raise SystemExit('Run python3 seed_test_data.py --accounts-only first to create the organiser account.')
        organiser_id = organiser[0]
        # Register old numbered seed rows BEFORE renaming so --reduce works.
        for event_id, name in connection.execute('SELECT id,name FROM events').fetchall():
            n = old_seed_number(name)
            if n is not None:
                connection.execute('INSERT OR IGNORE INTO seeded_events(seed_key,event_id) VALUES (?,?)',
                                   (f'au-{n:04d}',event_id))
        removed, protected = reduce_generated(connection,count) if reduce else (0,0)
        renamed = migrate_old_names(connection)
        created = skipped = full_count = 0
        for index in range(1,count+1):
            city,state,lat,lon = LOCATIONS[(index-1)%len(LOCATIONS)]
            activity,description,equipment = ACTIVITIES[(index-1)%len(ACTIVITIES)]
            title = f'{city} {activity}'
            key = f'au-{index:04d}'
            # Keep any existing seeded row; don't recreate it after renaming.
            if connection.execute('SELECT 1 FROM seeded_events WHERE seed_key=?',(key,)).fetchone():
                skipped += 1
                continue
            # Older unnumbered seed events may already have this title.
            if connection.execute('SELECT 1 FROM events WHERE name=?',(title,)).fetchone():
                skipped += 1
                continue
            offset = rng.randint(-75,-1) if index%5==0 else rng.randint(2,120)
            event_date = (today+timedelta(days=offset)).isoformat()
            start_hour = rng.choice([7,8,9,10,13,15])
            event_time = f'{start_hour:02d}:00-{start_hour+2:02d}:00'
            capacity = rng.choice([10,15,20,25,30,40])
            full = index%7==0
            cursor = connection.execute('''INSERT INTO events
                (name,location,latitude,longitude,date,time,registered,capacity,
                 description,equipment,safety_instructions,organiser_id)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
                (title,f'{city}, {state}, Australia',lat,lon,event_date,event_time,
                 capacity if full else 0,capacity,description,equipment,
                 'Follow organiser instructions, wear enclosed shoes, and avoid hazardous items.',organiser_id))
            event_id=cursor.lastrowid
            connection.execute('INSERT INTO seeded_events(seed_key,event_id) VALUES (?,?)',(key,event_id))
            if full:
                portions=[capacity//3,capacity//3,capacity-2*(capacity//3)]
                for booking_number,attendees in enumerate(portions,1):
                    connection.execute('''INSERT INTO registrations
                        (event_id,name,email,attendee_count) VALUES (?,?,?,?)''',
                        (event_id,f'Guest {booking_number}',
                         f'demo-au-{index:03d}-{booking_number}@example.invalid',attendees))
                full_count+=1
            created+=1
    print(f'Created {created} events; {skipped} already existed; renamed {renamed} older event titles.')
    print(f'Created {full_count} fully booked events.')
    if reduce:
        print(f'Removed {removed} excess tracked events; protected {protected} with real bookings.')
    print('Generated events are tracked internally in SQLite, not labelled on the website.')

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
    parser = argparse.ArgumentParser(description='Add Australian clean-up events for testing')
    parser.add_argument('--count',type=int,default=30,help='Number of generated events (default 30)')
    parser.add_argument('--reduce-demo',action='store_true',help='Remove excess tracked generated events without real bookings')
    parser.add_argument('--accounts-only',action='store_true',help='Create sample accounts without adding events')
    args=parser.parse_args()
    if not 1 <= args.count <= 2000:
        parser.error('--count must be between 1 and 2000')
    database=Path(__file__).resolve().parent/'instance'/'cleanup.db'
    seed_accounts(database)
    if not args.accounts_only:
        seed(args.count,database,reduce=args.reduce_demo)
