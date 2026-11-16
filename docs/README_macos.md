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
- `PARKANIZER_REFRESH_SECONDS`
- `PARKANIZER_MAX_RUN_SECONDS`
- `PARKANIZER_FUTURE_DAYS_LIMIT` (optional; leave blank for unlimited future dates)

## 5. Test the bot safely

```bash
python parkanizer_bot.py --help
python parkanizer_bot.py --list
python parkanizer_bot.py --dry-run
```

The `--list` mode inspects current bookable and waiting-queue state without taking any reservation action. The `--dry-run` mode evaluates availability without clicking the booking or confirmation control.

## 6. Run the bot normally

```bash
python parkanizer_bot.py
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
