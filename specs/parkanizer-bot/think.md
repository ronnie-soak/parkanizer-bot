# Think: Tidaro Parkanizer Parking Reservation Bot

## Business Need & Outcome
- **Backlog Issue:** User-provided request in `prompt.txt`; no GitHub issue or triage record was supplied.
- **Problem Statement:** The user needs to monitor Tidaro Parkanizer for newly available parking and book spots for a configured location without repeatedly checking the site manually.
- **Consumer:** The user, running the tool locally on macOS or Ubuntu, either on demand or on a schedule.
- **Desired Outcome:** A Python Playwright command-line tool that reads credentials and booking settings from `.env`, monitors the configured location within an optional future-day limit and maximum run duration, and books available spots. It also provides non-booking `--list` and `--dry-run` modes, per-run logs and timestamped screenshots, and OS-specific setup, testing, and scheduling documentation.

## Options Considered
### Option 1: Python Playwright browser automation
- **Approach:** Use Playwright's Python API to sign in through the normal website UI, navigate to the configured booking tab, inspect the configured location and eligible future dates, and handle each available booking and any confirmation step. Load settings from `.env`; expose `--list` and `--dry-run` CLI flags.
- **Trade-offs:** Closely follows the requested Python and browser workflow and avoids depending on undocumented service endpoints. Requires selectors resilient to UI changes and a compatible browser/runtime installation on both operating systems.
- **Cost:** Moderate; implement the workflow, safe mode handling, structured per-run artifacts, and two OS guides.
- **Risk:** The vendor UI may change or behave differently from assumptions; a mistaken action could make an unintended reservation. Mitigate with location/date checks, sequential actions, confirmation verification, and a dry-run that never commits a booking.

### Option 2: Python Selenium browser automation
- **Approach:** Implement the same normal-UI workflow using Selenium WebDriver, `.env`, and CLI flags.
- **Trade-offs:** Meets the language and platform requirements and uses a familiar browser-automation ecosystem. Adds WebDriver/browser setup and does not improve the key uncertainty around the vendor's UI or booking semantics.
- **Cost:** Moderate to high; browser-driver setup and lifecycle support are additional work.
- **Risk:** Driver/browser compatibility can complicate installation and scheduled execution across macOS and Ubuntu; booking safety requirements remain.

### Option 3: Python direct HTTP integration
- **Approach:** Call service endpoints directly to authenticate, poll availability, make reservations, and list bookings.
- **Trade-offs:** Could avoid browser startup and UI rendering, but no supported API or endpoint contract is provided. It would depend on undocumented implementation details instead of the explicitly requested browser workflow.
- **Cost:** High; endpoint discovery, session/CSRF handling, and ongoing compatibility work would be required.
- **Risk:** Highest; unsupported requests may bypass intended UI safeguards, break without notice, or cause unintended account changes.

## Chosen Approach
- **Selected:** Option 1: Python Playwright browser automation.
- **Reasoning:** Playwright directly satisfies the requested Python browser-based interaction and supports macOS and Ubuntu. Use only the normal site UI, keep all actions serial and location/date-scoped, and make non-commit behavior explicit for `--dry-run`. No existing application code or browser automation dependency exists in this repository to reuse.
- **Approved By:** Pending

## System Flow & Responsibilities
- **Request Tracing:** This repository contains no application runtime to trace; its current tracked context is the request in `prompt.txt` and agent/workflow documentation. The proposed tool starts from CLI arguments and `.env`, launches a browser with Playwright, signs in at `https://parkanizer.com/`, opens the configured `BOOK A SPOT` tab, and inspects only the configured parking location and dates within the configured range. In monitoring mode, it refreshes at the configured interval until a matching `Book any` action appears or the maximum duration expires. It processes matching actions sequentially, confirms only in normal mode when the UI requires it, and verifies the resulting state. `--list` reports current confirmed bookings and waiting queues ordered by date without entering the polling/booking loop. Every invocation records its start/end time, refresh and booking counts, errors, and requested screenshots.
- **Component Responsibilities:** Proposed CLI/configuration responsibility validates `.env` values and chooses normal, `--list`, or `--dry-run` behavior. Browser workflow responsibility performs login, navigation, location/date filtering, availability polling, and booking-state verification through visible UI controls. Artifact responsibility writes a separate timestamped log and screenshots for each execution. These are responsibilities for a new standalone tool, not existing repository components.
- **Boundaries:** The change begins and ends in a local Python process and its per-run artifacts. It interacts with the vendor only through the user's authenticated browser session and visible UI; it does not add a service, database, public API, or undocumented HTTP integration. Scheduling is configured by the user with the operating system's scheduler and documented per OS.

## Constraints & Invariants
- **Decision Records:** _None._
- **Non-Negotiable Rules:** Support macOS and Ubuntu with the requested Python 3.15.2 target, verifying Playwright and browser compatibility before implementation is considered complete. Read login, password, desired location, booking-tab label, availability-button label, refresh delay, maximum duration, and optional maximum days ahead from `.env`; an unset day limit means any future date. Keep `--list` and `--dry-run` as execution flags rather than secrets or hidden configuration. Match the configured location and date range before acting. `--list` must not reserve a spot. `--dry-run` must not create or confirm a booking; if opening a `Book any` control could itself commit, do not click it in dry-run. Do not log credentials or capture them in screenshots; keep generated artifacts and real `.env` credentials out of version control. Refreshes and bookings are sequential, and normal mode stops polling at the configured maximum duration. Logs include start/end time, refresh count, booking count, and execution errors; screenshots are timestamped and cover login, booking-tab navigation, an available-button page when found, and the final unavailable page when polling ends without a match.
- **Side-Effect Constraints:** Do not interact with other locations, dates outside the configured range, or unrelated account actions. Do not use parallel polling or undocumented service endpoints. Do not create a reservation in either `--list` or `--dry-run`.

## Blast Radius
- **Tier:** High
- **Affected:** The user's authenticated Tidaro Parkanizer account and its parking-reservation/waiting-queue UI; local `.env`, logs, screenshots, and scheduled invocations. No repository API, schema, or other consumer is affected.
- **Rationale:** The tool handles account credentials and can create externally visible reservations, so a UI or filtering error could affect the user's account. Its operation remains local and limited to explicit user settings and the normal website UI.
- **Rollback:** Disable or remove the scheduled invocation and stop the process. Cancel any unintended reservation or waiting-queue entry through the vendor UI; rotate the password through the vendor if credentials may have been exposed.

## Decision Record
- **Required:** no
- **Reason:** The selected approach adds a standalone local tool and does not change a public API, database schema, or existing service boundary.

## Persistent Context Updates
- **Docs:** `docs/README_macos.md` - document setup, installation, testing, configuration, and scheduling with a sample daily 7:58 a.m. macOS command.
- **Docs:** `docs/README_ubuntu.md` - document setup, installation, testing, configuration, and scheduling on Ubuntu.

## Ambiguities & Open Questions
- **Vendor UI details:** The exact login, location, booking, confirmation, and waiting-queue controls have not been inspected. The implementation must verify these through the normal browser UI; if booking semantics are ambiguous, it must fail safely rather than risk a reservation.
- **Date scope:** The day-limit setting is proposed as optional `.env` configuration, with an empty value meaning any future date. Confirm whether the user wants a particular default maximum.
- **Scheduling behavior:** The requested macOS example is daily at 7:58 a.m.; the user has not specified a timezone or an Ubuntu schedule. Use the machine's local timezone and document a suitable Ubuntu scheduler unless clarified otherwise.
- **Python compatibility:** Playwright/browser support for Python 3.15.2 must be verified against available releases on both target operating systems; if unavailable, the requested exact runtime target needs user clarification before implementation can claim support.
