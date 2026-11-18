# ADR-0609: The local-mode guide uses the autopilot

- Status: Proposed
- Date: 2026-11-17
- Deciders: maintainers
- Related: brief #1451, ADR-0587, ADR-0589
- Requirements: REQ-071

Protected classes: `tests/kit/`

## Context

With `[autopilot]` set, `doctor.py` fails `autopilot-settings` for `auto_start`, `launch_adapter` and `[capacity]`
(ADR-0587). `docs/guides/local-mode.md`, "Running unattended", still told the person to set them and to install
the watchdog's scheduler task, while `docs/guides/getting-started.md` already describes `agk autopilot on`. Following
the local-mode guide gave a setup that doctor fails.

## Decision

1. "Running unattended" is one path: the adapter, then `[autopilot] mode`, `interval_minutes` and `daily_budget`, then
   `agk autopilot on`, then the capacity (`[flow] builder_memory_gb`). The replaced settings and the watchdog task appear
   once, in a note headed `**Older settings**`, saying they are read only while `[autopilot]` is absent.
2. `tests/kit/test_guide_autopilot.py` reads the section and fails when it names `auto_start`, `launch_adapter` or
   `[capacity]` (the names `config.legacy_autopilot` gives, which doctor reports as not read) outside that note, when
   the note is missing or names one twice, or when the table is not set before `agk autopilot on`. It reads saved text
   only: no network, no model.
3. Local mode only; hosted and personal guides are unchanged.

## Consequences

The guide and doctor cannot drift apart unseen. The watchdog's own paragraphs stay under the note for the release in
which it is still read.

## Residual

- Whether `[capacity] profile` has an `[autopilot]` successor is open (Q-1451-1); the guide names `builder_memory_gb` only.
