# Community Clean-Up App 🌱

Welcome! This guide shows you how to get the app running, even if you've never used Python before.

**What you need:** a Mac or Windows computer, an internet connection for the first setup, and **Google Chrome**.

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

Restart the app using the commands in **step 3**.

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
| Port 5001 already in use | Stop the other running copy of the app, then try again. |

**Please note:** This guide is for running the app locally for learning and demonstrations. The included demo secret key is not suitable for a public deployment. Keep the `instance` folder private because it contains the database and demo credentials.
