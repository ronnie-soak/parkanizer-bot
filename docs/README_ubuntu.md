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
- `PARKANIZER_REFRESH_SECONDS`
- `PARKANIZER_MAX_RUN_SECONDS`
- `PARKANIZER_FUTURE_DAYS_LIMIT` (optional; leave blank for unlimited future dates)

## 5. Test the bot safely

```bash
python parkanizer_bot.py --help
python parkanizer_bot.py --list
python parkanizer_bot.py --dry-run
```

Use `--list` to inspect current bookings or waitlist data without making a reservation, and `--dry-run` to check for availability without clicking any booking action.

## 6. Run the bot normally

```bash
python parkanizer_bot.py
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
