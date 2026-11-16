#!/usr/bin/env python3
"""Parkanizer reservation bot CLI."""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Mapping

from dotenv import dotenv_values
from playwright.sync_api import Locator, sync_playwright

REQUIRED_ENV_VARS = (
    "PARKANIZER_EMAIL",
    "PARKANIZER_PASSWORD",
    "PARKANIZER_LOCATION",
    "PARKANIZER_BOOKING_TAB_LABEL",
    "PARKANIZER_AVAILABILITY_BUTTON_LABEL",
    "PARKANIZER_REFRESH_SECONDS",
    "PARKANIZER_MAX_RUN_SECONDS",
)

DEFAULT_URL = "https://parkanizer.com/"


@dataclass(frozen=True)
class Config:
    env_path: Path
    email: str
    password: str
    location: str
    booking_tab_label: str
    availability_button_label: str
    refresh_seconds: int
    max_run_seconds: int
    future_days_limit: int | None


@dataclass
class RunArtifacts:
    run_dir: Path
    log_path: Path
    refresh_count: int = 0
    booking_count: int = 0


def create_run_artifacts(base_dir: str | Path = "artifacts") -> RunArtifacts:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = Path(base_dir) / stamp
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / "run.log"
    log_path.touch()
    return RunArtifacts(run_dir=run_dir, log_path=log_path)


def _log_event(artifacts: RunArtifacts | None, message: str) -> None:
    if artifacts is None:
        return
    timestamp = datetime.now().isoformat(timespec="seconds")
    with artifacts.log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"{timestamp} {message}\n")


def _capture_screenshot(page, artifacts: RunArtifacts | None, name: str) -> str | None:
    if artifacts is None:
        return None
    target = artifacts.run_dir / f"{name}.png"
    page.screenshot(path=str(target), full_page=True)
    _log_event(artifacts, f"screenshot:{name}:{target.name}")
    return str(target)


def _read_value(values: Mapping[str, str | None], key: str) -> str:
    value = values.get(key)
    if value is None:
        return ""
    return str(value).strip()


def _parse_positive_int(name: str, value: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer, got {value!r}.") from exc
    if number <= 0:
        raise ValueError(f"{name} must be greater than zero.")
    return number


def _parse_optional_non_negative_int(name: str, value: str) -> int | None:
    if value is None or value == "":
        return None
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer or empty, got {value!r}.") from exc
    if number < 0:
        raise ValueError(f"{name} must be zero or greater.")
    return number


def _merge_values(env_path: Path) -> dict[str, str | None]:
    values: dict[str, str | None] = {}
    file_values = dotenv_values(env_path)
    if file_values:
        values.update(file_values)
    for key in REQUIRED_ENV_VARS:
        if key in os.environ and os.environ.get(key, "") != "":
            values[key] = os.environ[key]
    return values


def load_config(env_path: Path) -> Config:
    values = _merge_values(env_path)
    missing = [key for key in REQUIRED_ENV_VARS if not _read_value(values, key)]
    if missing:
        formatted = ", ".join(missing)
        raise ValueError(
            f"Missing required configuration values: {formatted}. "
            f"Add them to {env_path} or export them in the shell."
        )

    future_days_limit = _parse_optional_non_negative_int(
        "PARKANIZER_FUTURE_DAYS_LIMIT",
        _read_value(values, "PARKANIZER_FUTURE_DAYS_LIMIT"),
    )

    try:
        refresh_seconds = _parse_positive_int(
            "PARKANIZER_REFRESH_SECONDS",
            _read_value(values, "PARKANIZER_REFRESH_SECONDS"),
        )
        max_run_seconds = _parse_positive_int(
            "PARKANIZER_MAX_RUN_SECONDS",
            _read_value(values, "PARKANIZER_MAX_RUN_SECONDS"),
        )
    except ValueError as exc:
        raise ValueError(f"Invalid timing configuration: {exc}") from exc

    email = _read_value(values, "PARKANIZER_EMAIL")
    password = _read_value(values, "PARKANIZER_PASSWORD")
    location = _read_value(values, "PARKANIZER_LOCATION")
    booking_tab_label = _read_value(values, "PARKANIZER_BOOKING_TAB_LABEL")
    availability_button_label = _read_value(values, "PARKANIZER_AVAILABILITY_BUTTON_LABEL")

    for name, value in {
        "PARKANIZER_EMAIL": email,
        "PARKANIZER_PASSWORD": password,
        "PARKANIZER_LOCATION": location,
        "PARKANIZER_BOOKING_TAB_LABEL": booking_tab_label,
        "PARKANIZER_AVAILABILITY_BUTTON_LABEL": availability_button_label,
    }.items():
        if not value:
            raise ValueError(f"{name} must not be empty.")

    return Config(
        env_path=env_path,
        email=email,
        password=password,
        location=location,
        booking_tab_label=booking_tab_label,
        availability_button_label=availability_button_label,
        refresh_seconds=refresh_seconds,
        max_run_seconds=max_run_seconds,
        future_days_limit=future_days_limit,
    )


def _candidate_matches(location: str, button_label: str, value: str) -> bool:
    text = (value or "").strip().lower()
    if not text:
        return False
    lo = location.lower()
    btn = button_label.lower()
    action_keywords = {"book", "reserve", "reservation", "available", "availability"}

    if lo in text:
        if btn in text:
            return True
        return any(keyword in text for keyword in action_keywords)

    if btn in text:
        return lo in text

    return False


def find_matching_booking_candidates(values: list[str], location: str, button_label: str) -> list[str]:
    return [value for value in values if _candidate_matches(location, button_label, value)]


def _login(page, config: Config) -> None:
    email_input = None
    for selector in [
        "input[type='email']",
        "input[name*='email' i]",
        "input[name*='username' i]",
        "input[autocomplete*='email' i]",
        "input",
    ]:
        candidate = page.locator(selector).first
        if candidate.count() and candidate.is_visible():
            email_input = candidate
            break
    if email_input is None:
        raise RuntimeError("Could not locate the Parkanizer email input.")
    email_input.fill(config.email)

    password_input = None
    for selector in [
        "input[type='password']",
        "input[name*='password' i]",
        "input[autocomplete*='current-password' i]",
        "input",
    ]:
        candidate = page.locator(selector).first
        if candidate.count() and candidate.is_visible() and candidate != email_input:
            password_input = candidate
            break
    if password_input is None:
        raise RuntimeError("Could not locate the Parkanizer password input.")
    password_input.fill(config.password)

    for locator in [
        page.get_by_role("button", name=re.compile(r"login|log in|sign in|continue|submit", re.I)),
        page.locator("button, input[type='submit']").filter(has_text=re.compile(r"login|log in|sign in|continue|submit", re.I)),
    ]:
        if locator.count() and locator.first.is_visible():
            locator.first.click()
            return

    raise RuntimeError("Could not find the login submit control.")


def _open_booking_tab(page, config: Config) -> None:
    for locator in [
        page.get_by_role("tab", name=re.compile(config.booking_tab_label, re.I)),
        page.locator("button, a, [role='tab']").filter(has_text=re.compile(config.booking_tab_label, re.I)),
        page.locator("button, a, [role='button']").filter(has_text=re.compile(config.booking_tab_label, re.I)),
    ]:
        if locator.count() and locator.first.is_visible():
            locator.first.click()
            page.wait_for_timeout(2000)
            return
    raise RuntimeError(f"Could not find the configured booking tab label: {config.booking_tab_label}")


def _matching_booking_candidates(page, config: Config) -> list[str]:
    texts = []
    locators = page.locator("button, a, [role='button'], [role='link'], input[type='submit']")
    for index in range(locators.count()):
        candidate = locators.nth(index)
        if not candidate.is_visible():
            continue
        text = (candidate.inner_text() or "").strip()
        if text:
            texts.append(text)
    return find_matching_booking_candidates(texts, config.location, config.availability_button_label)


def _install_booking_locator(page, config: Config) -> Locator | None:
    locators = page.locator("button, a, [role='button'], [role='link'], input[type='submit']")
    for index in range(locators.count()):
        candidate = locators.nth(index)
        if not candidate.is_visible():
            continue
        text = (candidate.inner_text() or "").strip()
        if not text:
            continue
        if _candidate_matches(config.location, config.availability_button_label, text):
            return candidate
    return None


def _describe_list_state(page, config: Config) -> str:
    candidates = _matching_booking_candidates(page, config)
    if candidates:
        return "Current page reports availability candidates for location '%s': %s" % (
            config.location,
            "; ".join(candidates[:5]),
        )
    return "Current page does not show a matching booking action for the configured location."


def _run_browser_mode(config: Config, mode: str, artifacts: RunArtifacts | None = None) -> int:
    if artifacts is None:
        artifacts = create_run_artifacts()

    _log_event(artifacts, f"run_start mode={mode} location={config.location}")
    _log_event(artifacts, f"config refresh_seconds={config.refresh_seconds} max_run_seconds={config.max_run_seconds}")

    with sync_playwright() as playwright_manager:
        browser = playwright_manager.chromium.launch(headless=False)
        page = browser.new_page()
        try:
            page.goto(DEFAULT_URL, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            _capture_screenshot(page, artifacts, "login")
            _log_event(artifacts, "login_page_loaded")

            _login(page, config)
            page.wait_for_timeout(2500)
            _capture_screenshot(page, artifacts, "post_login")
            _open_booking_tab(page, config)
            _capture_screenshot(page, artifacts, "booking_tab")

            if mode == "list":
                state = _describe_list_state(page, config)
                _log_event(artifacts, f"list_state={state}")
                _capture_screenshot(page, artifacts, "list_state")
                print(state)
                return 0

            deadline = time.monotonic() + config.max_run_seconds
            refresh_count = 0
            while time.monotonic() < deadline:
                locator = _install_booking_locator(page, config)
                if locator is not None:
                    label = (locator.inner_text() or "matching booking control").strip() or "matching booking control"
                    _log_event(artifacts, f"candidate_found={label}")
                    _capture_screenshot(page, artifacts, "candidate_available")
                    print(f"Found a candidate action for location '{config.location}': {label}")
                    if mode == "dry-run":
                        _log_event(artifacts, "dry_run_blocked_booking")
                        print("Dry-run active: the booking/button action was not clicked.")
                        return 0
                    locator.click()
                    artifacts.booking_count += 1
                    _log_event(artifacts, f"booking_count={artifacts.booking_count}")
                    page.wait_for_timeout(2500)
                    confirm_locator = page.locator("button, [role='button'], input[type='submit']").filter(
                        has_text=re.compile(r"confirm|book|reserve|yes", re.I)
                    )
                    if confirm_locator.count() and confirm_locator.first.is_visible():
                        confirm_locator.first.click()
                    _capture_screenshot(page, artifacts, "reservation_result")
                    _log_event(artifacts, "normal_mode_booking_complete")
                    print("Normal mode action completed; browser left on the resulting reservation state.")
                    return 0

                refresh_count += 1
                artifacts.refresh_count = refresh_count
                _log_event(artifacts, f"refresh_count={refresh_count}")
                print(f"No matching action yet for '{config.location}'; refreshing in {config.refresh_seconds}s")
                page.reload(wait_until="domcontentloaded")
                time.sleep(config.refresh_seconds)

            _capture_screenshot(page, artifacts, "final_unavailable")
            _log_event(artifacts, "final_unavailable_after_timeout")
            print("Polling ended without a matching available slot before the configured maximum run duration.")
            return 0
        except Exception as exc:
            _log_event(artifacts, f"error={exc}")
            _capture_screenshot(page, artifacts, "error_state")
            raise
        finally:
            _log_event(artifacts, f"run_end refresh_count={artifacts.refresh_count} booking_count={artifacts.booking_count}")
            browser.close()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Monitor Tidaro Parkanizer availability and book a configured spot safely.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env"),
        help="Path to the local environment file containing Parkanizer credentials and settings.",
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--list",
        action="store_true",
        help="List bookings and waiting queues without creating or confirming a reservation.",
    )
    mode_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Evaluate availability and never click the booking or confirmation control.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_config(args.env_file)
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    mode = "list" if args.list else "dry-run" if args.dry_run else "normal"
    artifacts = create_run_artifacts()

    print(f"Loaded config from {config.env_path}")
    print(f"Location: {config.location}")
    print(f"Refresh interval: {config.refresh_seconds}s")
    print(f"Max run duration: {config.max_run_seconds}s")
    if config.future_days_limit is None:
        print("Future-day limit: unlimited")
    else:
        print(f"Future-day limit: {config.future_days_limit} day(s)")

    if mode == "list":
        print("List mode selected. Querying booking and waiting-queue state without creating a reservation.")
    elif mode == "dry-run":
        print("Dry-run selected. Availability will be checked but the booking action will not be triggered.")
    else:
        print("Normal mode selected. Browser automation will proceed with the configured booking flow.")

    try:
        result = _run_browser_mode(config, mode, artifacts)
        print(f"Artifacts directory: {artifacts.run_dir}")
        print(f"Run log: {artifacts.log_path}")
        return result
    except Exception as exc:
        _log_event(artifacts, f"main_error={exc}")
        print(f"Browser workflow failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
