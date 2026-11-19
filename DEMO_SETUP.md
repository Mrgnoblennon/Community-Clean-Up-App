# Demo data and accounts

From the project root:

```bash
python database.py
python seed_test_data.py
python app.py
```

The seeder creates 200 fictional Australian events, including past and fully booked events. Full events have fictional registration records, so counts are consistent. It also creates four demo accounts (admin, approved organiser, pending organiser, participant). Existing data is not overwritten. Rerunning skips existing demo events and accounts.

**Account emails** (all fictional, not real inboxes):

- `demo.admin@example.invalid` — admin (sign in through Organiser Login; click Admin in nav)
- `demo.organiser@example.invalid` — approved organiser
- `demo.pending@example.invalid` — unapproved organiser
- `demo.participant@example.invalid` — participant

All demo accounts share a **randomly generated password** printed by the seeder and saved to `instance/demo_credentials.json` (gitignored). Do not publish this file. For local testing only; delete demo accounts and credentials before deployment. Admin can approve/revoke organiser accounts. Admin is an approved organiser with the additional `is_admin` permission; the existing SQLite role constraint only permits `organiser` and `participant`.

**Map location:** On Explore, choose a city, use your device location (browser permission/HTTPS or localhost required), or show all event markers. The city selection is remembered in this browser. On Create Event, change the map centre before clicking the exact event location. Changing map centre does not alter an account's stored address or filter events by distance.

**Important:** Keep your existing `instance/cleanup.db` and `.git` folder. The ZIP does not contain a database. The generated demo events are fictional and must not be presented as real events. `python database.py` can be rerun safely.
