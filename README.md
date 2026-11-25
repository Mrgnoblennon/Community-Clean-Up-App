# Community Clean-Up App 🌱

Welcome! This guide shows you how to get the app running, even if you've never used Python before.

**What you need:** a Mac or Windows computer, an internet connection for the first setup, and **Google Chrome**.

## Which version should I use?

For final testing, use the [feature-donations branch](https://github.com/Mrgnoblennon/Community-Clean-Up-App/tree/feature-donations). It contains the latest development work for all nine user stories and the additional donations feature. The main branch may not yet contain these changes.

On GitHub, select **feature-donations** from the branch dropdown, then **Code → Download ZIP**. If you already use Git, run:

```bash
git fetch origin
git switch feature-donations
git pull origin feature-donations
```

## 1. Get ready (only once)

1. Install **Python 3** from https://www.python.org/downloads/
   - **Windows:** During installation, tick **Add Python to PATH** if offered.
2. Install **Visual Studio Code (VS Code)** from https://code.visualstudio.com/
3. Unzip the Community Clean-Up App download.
4. Open VS Code, click **File → Open Folder**, and choose the **Community-Clean-Up-App** folder.
5. In VS Code, click **Terminal → New Terminal**.

**Important:** Run all the commands below in that terminal, with the project folder open.

## 2. First-time setup (only once)

Choose the instructions for your computer.

### 🍎 Mac

Run these commands **one at a time**, pressing **Enter** after each:

```bash
python3 -m pip install -r requirements.txt
python3 database.py
```

### 🪟 Windows (VS Code PowerShell terminal)

Run these commands **one at a time**, pressing **Enter** after each:

```powershell
py -m pip install -r requirements.txt
py database.py
```

**If `py` isn't recognised:** try `python` instead of `py`.

You only need to install the requirements and set up the database once.

## 3. Start the app (every time you want to use it)

### 🍎 Mac

Copy and run these two commands:

```bash
export FLASK_SECRET_KEY="local-demo-key-change-me-123456789"
python3 app.py
```

### 🪟 Windows (VS Code PowerShell terminal)

Copy and run these two commands:

```powershell
$env:FLASK_SECRET_KEY="local-demo-key-change-me-123456789"
py app.py
```

**Leave the terminal open while using the app.**

## 4. Open the app in Google Chrome

1. Open **Google Chrome**.
2. Type this into the address bar:

   **http://127.0.0.1:5001**

3. Press **Enter**. The home page should appear!

This is a local website running on **your own computer**. You don't need to search for it on Google.

## 5. What can you do?

### 🙋 Join a clean-up
1. Click **Explore**.
2. Choose an event.
3. Click **Join** and enter your details. You can join as a guest.

### 🌟 Track your volunteering
1. Create a participant account or log in.
2. Join an event using the same email as your account.
3. Once the organiser confirms you attended, your dashboard updates.

### 🎁 Earn and spend points
1. Get **100 points** when your attendance is confirmed.
2. Get an extra **150 points** for every three different events attended in the same month.
3. Open **Rewards Shop** to spend points on rewards offered by businesses.

### 🧹 Organise an event
1. Register as an organiser.
2. Wait for an admin to approve your account.
3. Log in, create an event and confirm attendance afterwards.

### 🏪 Offer business rewards
1. Open **Rewards Shop** and choose the option to register a business.
2. Wait for admin approval.
3. Log in to your business dashboard and add rewards.

### 📋 Manage your events (latest testing branch)
1. Log in as an approved organiser and open **My Events**.
2. View registrations and participant contact details where provided.
3. Mark attendance as attended or absent, or reset attendance if needed.
4. Edit upcoming event details, including the map location and capacity. Capacity cannot be reduced below existing registrations.
5. During an event, only safety, meeting point and contact information can be edited.
6. To cancel an upcoming event, provide a reason and confirm. Cancelled events cannot accept new registrations.

### 📍 Report litter (latest testing branch)
1. Log in and open **Report Litter**.
2. Select a location on the map and optionally add a description or photo.
3. Supported photos: JPEG, PNG and WebP, up to 10 MB. HEIC is not supported.
4. Submit the report and check that it appears on the litter map.

### 💚 Make a donation (latest testing branch)
1. Open **Donate** or visit http://127.0.0.1:5001/donations.
2. Select a preset amount or enter a custom amount.
3. Optionally provide your name or donate anonymously.
4. Confirm and check the donation total.

Donations are simulated in AUD. No actual money or card details are collected.

## 6. Want to test the app with demo accounts? (Optional)

If you need sample accounts and events, **stop the app first** (see step 7), then run:

**Mac:**
```bash
python3 seed_test_data.py
```

**Windows:**
```powershell
py seed_test_data.py
```

The script shows the demo account details and password in the terminal. You can also find them in `instance/demo_credentials.json`.

Available demo accounts:

| Role | Email |
| --- | --- |
| Administrator | demo.admin@example.invalid |
| Approved organiser | demo.organiser@example.invalid |
| Pending organiser | demo.pending@example.invalid |
| Participant | demo.participant@example.invalid |

Use the password printed by the seed script. Register a separate demo business through the Rewards Shop if testing business approval.

Restart the app using the commands in **step 3**.

### Final acceptance testing

Use the [User Story Test Cases in Confluence](https://softwarestudents12345.atlassian.net/wiki/spaces/~5ef181a32116eb0a7ba9ee36/pages/12779526/User+Story+Test+Cases). Test on the latest testing branch, tick only verified passes, and record bugs and screenshots. Include the additional donations feature in regression testing.

### Known limitations

- Email verification codes are available in the local terminal; real email delivery is not configured.
- Cancellation and event-change notices are recorded locally; actual email notifications are not sent.
- Donations are simulated, not real payments.
- The latest features require final browser testing; implementation does not imply acceptance tests have passed.

### Testing attendance before an event starts (local testing only)

Normally organisers can confirm attendance only after an event starts. For a classroom demonstration, stop the app and use:

**Mac:**
```bash
export FLASK_SECRET_KEY="local-demo-key-change-me-123456789"
ENABLE_ATTENDANCE_TEST_MODE=1 python3 app.py
```

**Windows (PowerShell):**
```powershell
$env:FLASK_SECRET_KEY="local-demo-key-change-me-123456789"
$env:ENABLE_ATTENDANCE_TEST_MODE="1"
py app.py
```

**Do not use attendance test mode on a public website.**

## 7. How to stop and restart

- **Stop:** click inside the VS Code terminal and press **Control + C**.
- **Restart:** run the two commands in **step 3** again.
- **Next time:** you can skip the first-time setup in **step 2**.

## 8. Something not working?

| Problem | What to try |
| --- | --- |
| `python3` or `py` not found | Install Python 3, then close and reopen VS Code. |
| `No module named flask` | Repeat the first command in step 2. |
| `requirements.txt` not found | Open the correct project folder in VS Code. |
| Chrome says the page can't be reached | Make sure the app is running and the terminal is still open. |
| `FLASK_SECRET_KEY` error | Run **both** commands in step 3, in the same terminal. |
| Missing database or tables | Stop the app, run the database setup command in step 2, then restart. |
| Photo upload rejected | Use JPEG, PNG or WebP under 10 MB. Convert HEIC images first. |
| New features missing | Confirm you downloaded or switched to the latest testing branch. |
| Port 5001 already in use | Stop the other running copy of the app, then try again. |

**Please note:** This guide is for running the app locally for learning and demonstrations. The included demo secret key is not suitable for a public deployment. Keep the `instance` folder private because it contains the database and demo credentials.
