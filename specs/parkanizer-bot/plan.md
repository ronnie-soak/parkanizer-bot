# Plan: Parkanizer reservation bot

## File Scope & Boundaries
- **In Scope:** `parkanizer_bot.py`, `.env.example`, `requirements.txt`, `docs/README_macos.md`, `docs/README_ubuntu.md`
- **Out of Scope:** _None._
- **Irreversible Changes:** _None._

## Prerequisites & Context
- **Reference:** `specs/parkanizer-bot/think.md`
- **Required before Step 1:** Python 3.15.2, Playwright browser support, a live Tidaro Parkanizer account, and local `.env` values for login, password, desired location, booking tab label, availability button label, refresh delay, and optional future-day limit.

## Acceptance Criteria
- **AC-1:** Given a valid `.env` and a `--list` invocation, then the CLI reports current bookings and waiting queues without creating or confirming a reservation.
- **AC-2:** Given a configured location/date match and a `--dry-run`, then the tool never clicks a booking action or confirms a reservation.
- **AC-3:** Given a matching available slot in normal mode, then the tool books only the configured location and date and verifies the resulting reservation state.
- **AC-4:** Given polling reaches the configured maximum duration or location/date limit without a match, then the tool exits without booking and records the final unavailable state in logs and screenshots.
- **AC-5:** Given missing or malformed configuration values, then the tool exits cleanly with a validation error before any browser action is attempted.
- **AC-6:** Given a completed run, then a timestamped log and screenshots are written for key states without capturing credentials.

## Implementation Checklist
### Step 1: Define CLI and configuration contract
- **Files:** `parkanizer_bot.py`, `.env.example`, `requirements.txt`
- **Action:** Define the Python CLI, required `.env` values, execution modes, validation rules, and safe failure behavior for missing or ambiguous configuration.
- **Verification:** `python parkanizer_bot.py --help`
- **Bootable Check:** `python parkanizer_bot.py --help >/dev/null`
- **Serves:** AC-1, AC-2, AC-5

### Step 2: Implement browser workflow and site checks
- **Files:** `parkanizer_bot.py`
- **Action:** Add the Playwright login flow, booking-tab navigation, location/date filtering, refresh loop, and booking verification while restricting actions to the configured location and range.
- **Verification:** `python -m compileall parkanizer_bot.py`
- **Bootable Check:** `python parkanizer_bot.py --help >/dev/null`
- **Serves:** AC-3, AC-4, AC-5

### Step 3: Add non-committing safety modes
- **Files:** `parkanizer_bot.py`
- **Action:** Ensure `--list` reports booked or waitlisted state without reservation logic, and `--dry-run` blocks any booking action or confirmation step while still evaluating availability.
- **Verification:** `python -m compileall parkanizer_bot.py`
- **Bootable Check:** `python parkanizer_bot.py --list >/dev/null`
- **Serves:** AC-1, AC-2

### Step 4: Add run artifacts and screenshot capture
- **Files:** `parkanizer_bot.py`
- **Action:** Record start/end timestamps, refresh and booking counts, execution errors, and timestamped screenshots for login, booking-tab navigation, available decisions, and the final unavailable state while keeping credentials out of artifacts.
- **Verification:** `python -m compileall parkanizer_bot.py`
- **Bootable Check:** `python parkanizer_bot.py --help >/dev/null`
- **Serves:** AC-4, AC-6

### Step 5: Publish macOS and Ubuntu setup guidance
- **Files:** `docs/README_macos.md`, `docs/README_ubuntu.md`
- **Action:** Document Python installation, Playwright/browser setup, local configuration, testing commands, and scheduling examples for both operating systems, including the requested macOS daily 7:58 a.m. invocation.
- **Verification:** `test -f docs/README_macos.md && test -f docs/README_ubuntu.md`
- **Bootable Check:** `python -m compileall parkanizer_bot.py`
- **Serves:** AC-1, AC-3, AC-5, AC-6

## Test Plan
| Criterion | Test | Step |
|---|---|---|
| AC-1 | `python parkanizer_bot.py --list` exits without reserving a spot and prints current bookings or queue state | Step 3 |
| AC-2 | `python parkanizer_bot.py --dry-run` evaluates a matching slot and never clicks the booking control | Step 3 |
| AC-3 | Normal mode with a matching slot books only the configured location/date and verifies the state | Step 2 |
| AC-4 | Polling stops at the configured duration/date limit and records the final unavailable screenshot | Step 4 |
| AC-5 | Missing or malformed `.env` values fail before the browser opens | Step 1 |
| AC-6 | A completed run produces the required log and screenshots without credential leakage | Step 4 |

## Open Questions & Assumptions
- **Assumption:** Local `.env` values remain untracked and are validated before any browser interaction.
- **Assumption:** The tool fails safely when the vendor UI is ambiguous instead of risking an unintended booking.
- **Question:** What is the default maximum day horizon when the value is unset? **Answer:** Treat an unset day limit as unlimited future dates until a user-specified cap is added.

## Blast Radius Check
- **Tier from Think:** High
- **Still Holds:** Yes
- **Reason:** _None._
- **Rollback:** Disable or remove the scheduled invocation, stop the process, and cancel any unintended reservation or waiting-queue entry through the vendor UI; rotate the password if credentials may have been exposed.

## Done When
- All implementation steps above are complete.
- All verification and bootable checks pass, and the CLI remains runnable with `--help` and compile checks.
- The tool enforces `.env` validation, non-booking safety modes, and per-run artifact capture without credential leakage.
- The macOS and Ubuntu documentation covers setup, testing, and scheduling for the configured workflow.

## Approval
- **Approved By:** JPRE
