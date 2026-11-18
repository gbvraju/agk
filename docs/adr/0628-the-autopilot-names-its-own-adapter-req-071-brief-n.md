# ADR-0628: The autopilot names its own launch adapter

- Status: Proposed
- Date: 2026-11-17
- Deciders: maintainers
- Related: brief #1480, Q-1451-2 (b) (on pull request #1473), ADR-0587, ADR-0589, SPEC-0064, plan #661
- Requirements: REQ-071

## Context

ADR-0587 decision 2 makes `doctor.py` fail `autopilot-settings` when `[flow] launch_adapter` is set beside an
`[autopilot]` table (`not read: [autopilot] is set`), but `autopilot.py` (ADR-0587 decision 5, `on`'s machine check;
ADR-0589 decision 5, `agk next`) still read the adapter from `[flow] launch_adapter` only. So no `agk.toml` both passed
the health check and let the autopilot start a job. The owner chose Q-1451-2 (b): the autopilot gets its own setting.

## Decision

1. **The key.** `config.autopilot_settings` reads `[autopilot] adapter`, the launch adapter in the command form
   `[flow] launch_adapter` takes (`""` is unset, as there). A value that is not a string, or only blanks, is refused
   naming `adapter of the autopilot table` and `setting: autopilot.adapter`, never the value.
2. **Who reads it.** `launch.autopilot_adapter(root)` gives the adapter and the setting it came from: with an
   `[autopilot]` table its `adapter` (`autopilot.adapter`), never `[flow] launch_adapter`; with none, today's
   `launch_adapter` (`flow.launch_adapter`) for one release (ADR-0587). `autopilot.py`'s machine check of `on` and
   `agk next`'s start read it, so their `warn:` and `nothing started` lines name `autopilot.adapter` when the table is
   set; the starts `agk next` makes through `launch.py` take that adapter.
3. **The health check.** `autopilot-settings` keeps naming `launch_adapter` as replaced while `[autopilot]` is set; its
   fix names `[autopilot] adapter`. `model-names` also warns when `[autopilot] mode = "on"` has an `adapter` and
   `[models.names]` is unset, as it does for `auto_start` with `launch_adapter`.
4. **By mode.** Local mode is the case it is for; hosted mode (no machine scheduler) and personal mode without an
   adapter are unchanged.

ADR-0587 decision 5 (the adapter check named `flow.launch_adapter`) and ADR-0589 decision 5 (`agk next` starts through
`[flow] launch_adapter`) read, with an `[autopilot]` table, `[autopilot] adapter` instead.

Protected path classes changed: `scripts/agk/` (`config.py`, `launch.py`, `autopilot.py`, `doctor.py`), `tests/kit/`
(`test_autopilot_adapter.py`), `agk.toml` (the `[[testing.map]]` entries), `docs/adr/` (this file) and `changelog.d/`
(one fragment).

## Consequences

An `agk.toml` with `[autopilot]` and its `adapter`, and no `[flow] launch_adapter`, passes the health check and lets
`agk next` start a job. The conductor's `watchdog` pass, the reviewer start and the steward line still read `[flow]
auto_start` and `launch_adapter` (Q-1480-1); `kit/templates/agk.toml` does not list the key yet, as the brief's
`Touches:` does not name it.

## Residual

- 2026-11-17: the scripted `watchdog --pass` (`conductor.py`) still needs `[flow] auto_start` and `launch_adapter`,
  which `autopilot-settings` fails beside `[autopilot]` (Q-1480-1) (due 2027-03-31).
