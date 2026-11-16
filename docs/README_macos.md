# Parkanizer bot on macOS

## 1. Install Python

Use Python 3.12+ or the exact local target version the machine supports. The bot is written for Python 3.12 and expects `python3` in the shell.

```bash
python3 --version
```

If Python is missing, install it with Homebrew:

```bash
brew install python
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

Copy the sample file and fill in real values:

```bash
cp .env.example .env
```

Required values:

- `PARKANIZER_EMAIL`
- `PARKANIZER_PASSWORD`
- `PARKANIZER_LOCATION`
- `PARKANIZER_BOOKING_TAB_LABEL`
- `PARKANIZER_AVAILABILITY_BUTTON_LABEL`
- `PARKANIZER_REFRESH_MILLISECONDS`
- `PARKANIZER_MAX_RUN_SECONDS`
- `PARKANIZER_FUTURE_DAYS_LIMIT` (optional; leave blank for unlimited future dates)

Optional:

- `PARKANIZER_SESSION_DIR` (defaults to `.parkanizer-browser` and reuses a saved authenticated browser profile across runs)

## 5. Test the bot safely

```bash
python parkanizer_bot.py --help
python parkanizer_bot.py --list
python parkanizer_bot.py --dry-run
```

The bot keeps a persistent browser session in `.parkanizer-browser` by default. It considers a session valid when the configured `PARKANIZER_BOOKING_TAB_LABEL` control is visible; `SIGN IN`/`SIGN UP` controls are not used to validate the session. If automatic session recovery fails, complete sign-in in the opened browser, then enter `y` in the terminal prompt to continue or `q` to quit. The bot waits until the configured booking tab is visible, saves the validated browser state, and continues the requested workflow. The `--list` mode inspects current bookable and waiting-queue state without taking any reservation action. The `--dry-run` mode evaluates availability without clicking the booking or confirmation control.

## 6. Run the bot normally

```bash
python parkanizer_bot.py
```

You can override the persisted session directory with:

```bash
python parkanizer_bot.py --session-dir .my-session
```

## 7. Schedule the daily run

The requested macOS schedule is a daily 7:58 a.m. run using the local user crontab.

```bash
crontab -e
```

Then add a line similar to:

```cron
58 7 * * * cd /path/to/parkanizer-bot && source .venv/bin/activate && python parkanizer_bot.py >> ~/parkanizer.log 2>&1
```

This uses the machine local timezone and writes the bot stdout/stderr to `~/parkanizer.log`.
