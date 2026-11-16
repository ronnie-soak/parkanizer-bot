import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from parkanizer_bot import (
    _has_valid_session,
    _login_with_manual_fallback,
    _prepare_login_state,
    find_matching_booking_candidates,
    load_config,
)


class FakeLocator:
    def __init__(self, page, label):
        self.page = page
        self.label = label
        self.first = self

    def count(self):
        return int(self.page.is_control_visible(self.label))

    def is_visible(self):
        return self.page.is_control_visible(self.label)

    def click(self):
        self.page.click_control(self.label)

    def fill(self, value):
        self.page.filled[self.label] = value

    def filter(self, **_kwargs):
        return self


class FakePage:
    def __init__(self, cookie_visible=True, sign_in_visible=True, booking_tab_visible=False):
        self.cookie_visible = cookie_visible
        self.sign_in_visible = sign_in_visible
        self.booking_tab_visible = booking_tab_visible
        self.login_fields_visible = False
        self.clicks = []

    def get_by_role(self, role, name):
        for label in ("Reject all", "SIGN IN", "Book a spot"):
            if name.fullmatch(label):
                return FakeLocator(self, label)
        return FakeLocator(self, "")

    def locator(self, selector):
        return FakeLocator(self, "login fields" if self.login_fields_visible else "")

    def wait_for_timeout(self, _milliseconds):
        pass

    def is_control_visible(self, label):
        if label == "login fields":
            return self.login_fields_visible
        if label == "Reject all":
            return self.cookie_visible
        if label == "SIGN IN":
            return self.sign_in_visible
        if label == "Book a spot":
            return self.booking_tab_visible
        return False

    def click_control(self, label):
        self.clicks.append(label)
        if label == "Reject all":
            self.cookie_visible = False
        elif label == "SIGN IN":
            self.sign_in_visible = False
            self.login_fields_visible = True
        elif label == "Book a spot":
            self.booking_tab_visible = True


class FakeContext:
    def __init__(self):
        self.saved_paths = []

    def storage_state(self, path):
        self.saved_paths.append(path)


class FakeLoginPage:
    def __init__(self):
        self.filled = {}

    def locator(self, selector):
        return FakeLocator(self, selector)

    def get_by_role(self, role, name):
        return FakeLocator(self, "submit")

    def is_control_visible(self, label):
        return label in {"input[name='signInName']", "input[name='password']", "submit"}

    def click_control(self, _label):
        pass


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

    def test_load_config_accepts_optional_day_limit_and_session_dir(self):
        env_path = Path("/tmp/parkanizer-bot-test.env")
        env_path.write_text(
            "PARKANIZER_EMAIL=user@example.com\n"
            "PARKANIZER_PASSWORD=secret\n"
            "PARKANIZER_LOCATION=North Garage\n"
            "PARKANIZER_BOOKING_TAB_LABEL=Book a spot\n"
            "PARKANIZER_AVAILABILITY_BUTTON_LABEL=Book now\n"
            "PARKANIZER_REFRESH_MILLISECONDS=250\n"
            "PARKANIZER_MAX_RUN_SECONDS=600\n"
            "PARKANIZER_FUTURE_DAYS_LIMIT=\n"
            "PARKANIZER_SESSION_DIR=.custom-browser\n",
            encoding="utf-8",
        )
        try:
            config = load_config(env_path)
            self.assertIsNone(config.future_days_limit)
            self.assertEqual(config.refresh_milliseconds, 250)
            self.assertEqual(config.session_dir, Path(".custom-browser"))
        finally:
            env_path.unlink(missing_ok=True)

    def test_dry_run_guard_keeps_booking_hidden(self):
        values = ["North Garage - Book now", "Choose another lot"]
        matches = find_matching_booking_candidates(values, "North Garage", "Book now")
        self.assertEqual(matches, ["North Garage - Book now"])

    def test_expired_session_rejects_cookies_then_opens_sign_in(self):
        page = FakePage()
        self.assertTrue(_prepare_login_state(page, self.config()))
        self.assertEqual(page.clicks, ["Reject all", "SIGN IN"])
        self.assertTrue(page.login_fields_visible)

    def test_valid_session_only_rejects_cookie_popup(self):
        page = FakePage(cookie_visible=True, sign_in_visible=False)
        page.booking_tab_visible = True
        self.assertFalse(_prepare_login_state(page, self.config()))
        self.assertEqual(page.clicks, ["Reject all"])

    def test_missing_session_opens_sign_in_without_cookie_popup(self):
        page = FakePage(cookie_visible=False, sign_in_visible=True)
        self.assertTrue(_prepare_login_state(page, self.config()))
        self.assertEqual(page.clicks, ["SIGN IN"])
        self.assertTrue(page.login_fields_visible)

    def test_booking_tab_validates_session_even_if_sign_in_is_visible(self):
        page = FakePage(cookie_visible=False, sign_in_visible=True, booking_tab_visible=True)
        self.assertTrue(_has_valid_session(page, self.config()))
        self.assertFalse(_prepare_login_state(page, self.config()))
        self.assertEqual(page.clicks, [])

    def test_failed_automatic_login_waits_for_manual_confirmation_then_saves_session(self):
        page = FakePage(cookie_visible=False, sign_in_visible=False)
        page.login_fields_visible = True
        context = FakeContext()
        confirmations = iter(["not yet", "y"])

        def confirm_login(_prompt):
            answer = next(confirmations)
            if answer == "y":
                page.login_fields_visible = False
                page.booking_tab_visible = True
            return answer

        with patch("parkanizer_bot._login", side_effect=RuntimeError("automatic login failed")):
            recovered = _login_with_manual_fallback(
                page,
                config=self.config(),
                context=context,
                state_path=Path("/tmp/browser-state.json"),
                input_fn=confirm_login,
            )

        self.assertTrue(recovered)
        self.assertEqual(context.saved_paths, ["/tmp/browser-state.json"])

    def test_manual_session_recovery_quit_does_not_save_session(self):
        page = FakePage(cookie_visible=False, sign_in_visible=False)
        page.login_fields_visible = True
        context = FakeContext()
        with patch("parkanizer_bot._login", side_effect=RuntimeError("automatic login failed")):
            recovered = _login_with_manual_fallback(
                page,
                config=self.config(),
                context=context,
                state_path=Path("/tmp/browser-state.json"),
                input_fn=lambda _prompt: "q",
            )
        self.assertFalse(recovered)
        self.assertEqual(context.saved_paths, [])

    def test_login_fills_named_signin_and_password_fields(self):
        page = FakeLoginPage()
        config = SimpleNamespace(email="person@example.com", password="secret")
        with patch("parkanizer_bot._reach_login_form"):
            from parkanizer_bot import _login

            _login(page, config)
        self.assertEqual(page.filled["input[name='signInName']"], "person@example.com")
        self.assertEqual(page.filled["input[name='password']"], "secret")

    def config(self):
        return SimpleNamespace(booking_tab_label="Book a spot")


if __name__ == "__main__":
    unittest.main()
