# Parkanizer bot on Ubuntu

## 1. Install Python and browser support

Install Python 3.12 or the supported local version and the Playwright browser dependencies.

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip libnss3 libatk-bridge2.0-0 libgtk-3-0 libxss1
```

## 2. Create and activate a virtual environment

```bash
cd /path/to/parkanizer-bot
python3 -m venv .venv
source .venv/bin/activate
```

## 3. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m playwright install chromium
```

## 4. Configure credentials and booking settings

```bash
cp .env.example .env
```

Populate the required environment values before use:

- `PARKANIZER_EMAIL`
- `PARKANIZER_PASSWORD`
- `PARKANIZER_LOCATION`
- `PARKANIZER_BOOKING_TAB_LABEL`
- `PARKANIZER_AVAILABILITY_BUTTON_LABEL`
- `PARKANIZER_REFRESH_MILLISECONDS`
- `PARKANIZER_MAX_RUN_SECONDS`
- `PARKANIZER_FUTURE_DAYS_LIMIT` (optional; leave blank for unlimited future dates)
- `PARKANIZER_SESSION_DIR` (optional; defaults to `.parkanizer-browser`)

## 5. Test the bot safely

```bash
python parkanizer_bot.py --help
python parkanizer_bot.py --list
python parkanizer_bot.py --dry-run
```

The bot reuses a saved browser session in `.parkanizer-browser` by default. It considers a session valid when the configured `PARKANIZER_BOOKING_TAB_LABEL` control is visible; `SIGN IN`/`SIGN UP` controls are not used to validate the session. If the session is missing or stale, it attempts automatic sign-in and stores the validated state for the next run. If automatic recovery fails, complete sign-in in the opened browser, then enter `y` at the terminal prompt to continue or `q` to quit; the bot waits for the configured booking tab, saves the validated browser state, and continues the requested workflow. Use `--list` to inspect current bookings or waitlist data without making a reservation, and `--dry-run` to check for availability without clicking any booking action.

## 6. Run the bot normally

```bash
python parkanizer_bot.py
```

You can override the persisted browser profile with:

```bash
python parkanizer_bot.py --session-dir .my-session
```

## 7. Schedule the daily run with cron

Open the cron table:

```bash
crontab -e
```

Add a job in the local timezone, for example:

```cron
0 8 * * * cd /path/to/parkanizer-bot && source .venv/bin/activate && python parkanizer_bot.py >> ~/parkanizer.log 2>&1
```

This keeps the bot in a standard Linux crontab loop and records stdout/stderr to `~/parkanizer.log` for troubleshooting.
