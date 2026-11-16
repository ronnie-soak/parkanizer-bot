import unittest
from pathlib import Path

from parkanizer_bot import find_matching_booking_candidates, load_config


class TestParkanizerBot(unittest.TestCase):
    def test_find_matching_booking_candidates(self):
        text_values = [
            "North Garage",
            "Book now - North Garage",
            "Check availability at South Garage",
            "Reserve North Garage",
            "Waitlist for East Garage",
        ]
        matches = find_matching_booking_candidates(text_values, "North Garage", "Book now")
        self.assertEqual(matches, ["Book now - North Garage", "Reserve North Garage"])

    def test_find_matching_booking_candidates_returns_empty_for_unrelated_values(self):
        values = ["Book now - South Garage", "Waitlist for East Garage"]
        self.assertEqual(find_matching_booking_candidates(values, "North Garage", "Book now"), [])

    def test_load_config_accepts_optional_day_limit(self):
        env_path = Path("/tmp/parkanizer-bot-test.env")
        env_path.write_text(
            "PARKANIZER_EMAIL=user@example.com\n"
            "PARKANIZER_PASSWORD=secret\n"
            "PARKANIZER_LOCATION=North Garage\n"
            "PARKANIZER_BOOKING_TAB_LABEL=Book a spot\n"
            "PARKANIZER_AVAILABILITY_BUTTON_LABEL=Book now\n"
            "PARKANIZER_REFRESH_SECONDS=30\n"
            "PARKANIZER_MAX_RUN_SECONDS=600\n"
            "PARKANIZER_FUTURE_DAYS_LIMIT=\n",
            encoding="utf-8",
        )
        try:
            config = load_config(env_path)
            self.assertIsNone(config.future_days_limit)
        finally:
            env_path.unlink(missing_ok=True)

    def test_dry_run_guard_keeps_booking_hidden(self):
        values = ["North Garage - Book now", "Choose another lot"]
        matches = find_matching_booking_candidates(values, "North Garage", "Book now")
        self.assertEqual(matches, ["North Garage - Book now"])


if __name__ == "__main__":
    unittest.main()
