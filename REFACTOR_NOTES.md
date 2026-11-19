# Template refactor notes

- `templates/base.html` contains the shared HTML document, stylesheet and Jinja blocks.
- `templates/partials/navbar.html` contains the reusable role-aware navigation.
- `templates/partials/site_header.html` adds the shared header to standard pages.
- The four redesigned pages keep their existing custom headers to preserve their layout.
- All nonempty templates now extend `base.html` and retain their existing forms, routes and scripts.
- `app.py`: event start-time comparisons now accept a time range such as `09:00-11:00`.
- Existing empty templates (`admin.html`, `login.html`, `register.html`) remain empty.
- Your original ZIP is unchanged. The project database and `.git` history are excluded from this handoff ZIP. Keep your existing `instance/cleanup.db` and `.git` folder.
- Test the app from the project root with `FLASK_SECRET_KEY` set in your environment.

## Full template update

- Added `partials/profile_link.html` to share the account shortcut across redesigned and standard headers.
- Removed duplicate brand headers on standard pages: the logo and navigation now come from `base.html`.
- Applied `standard-page` to all active standard templates for consistent layout, cards, form focus and mobile spacing.
- Added input autocomplete attributes on participant login and registration.
- Kept form field names, URLs, methods, conditional branches, scripts and map behaviour unchanged.
- The three unused empty templates remain as documented placeholders; no routes currently use them.
- Test login, event creation, event joining, email verification, registration editing and cancellation before deploying.
