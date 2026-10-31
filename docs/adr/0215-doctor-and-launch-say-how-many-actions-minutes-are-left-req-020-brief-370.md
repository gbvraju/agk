# ADR-0215: doctor and launch say how many Actions minutes are left (REQ-020, brief 370)

- Status: Accepted
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0184
- Requirements: REQ-020

Protected classes: `scripts/agk/`, `tests/kit/`, `skills/`

## Context

Brief #370 (priority 1, #287 answer 7). `minutes.py` (#324, ADR-0184) has to be remembered and warns once, at `minutes_warn`
percent; in the pilot the minutes ran out on day 2. The doctor and `/agk:launch` are what a person runs anyway. The tests were
written first, with saved API responses and no network (`tests/kit/test_minutes.py`, `tests/kit/test_doctor_ci.py`).

## Decision

1. **The level and the day (answer 1).** `minutes.py` gives a `level`: the highest of `50%`, `<minutes_warn>%` (80 when unset)
   and `95%` that the higher of the billing figure and the estimate has reached of the included minutes (`used * 100 >= level *
   included`), else `ok`; `unknown` when the included minutes are unknown. `runs_out` is the day the included minutes are used up
   at this month's daily rate so far (used minutes over the days of the month through today, UTC): today plus the whole days,
   rounded up, that the rest lasts; `not this month` when that day is in the next month or nothing was used; today when they are
   used up already; `null` when unknown. `--json` gains both; the text report gains `level: <level>; runs out ...`. No new
   setting; the exit codes are unchanged.
2. **One line (answers 2 and 3).** `minutes.py --line` prints one line, reading billing first and the run history only when
   billing cannot be read: `actions minutes: <used> of <included> used (<n>%), level <level>; runs out about <date>` (or
   `runs out not this month`), with `; at this level, see local mode in docs/guides/local-mode.md` at `95%`;
   `actions minutes: <n> used this month (estimate from run history), included minutes unknown (<reason>); level unknown`; or
   `actions minutes: unknown (the token cannot read billing: <reason>, nor the run history: <reason>)`. It exits 3 past
   `minutes_warn`, as the report does.
3. **The doctor (answer 2).** `doctor.py` gains `actions-minutes` (severity `warn`, in the report order after the CI checks and before the engines checks, which stay last) with that line in its
   message: `ok` under `50%` or with the level unknown but an estimate read; `fail` (a warning, exit 4, never 1) from `50%` on;
   `cannot-check` with the new reason `minutes-unknown` when neither billing nor the run history can be read, and with the
   repository's own reason when the repository cannot be read. The doctor imports `minutes.py` (installed beside it) and reads,
   with GET, the account's billing endpoint and, only when that does not answer, the month's runs and their jobs; a repository
   answer without an owner object is read by the owner in its full name. Each read of the doctor is made once (the repository is
   read by two checks).
4. **Launch (answer 3).** `/agk:launch` runs `python3 scripts/agk/minutes.py --line` after the plan and before it asks to confirm,
   and at `95%` recommends local mode (`docs/guides/local-mode.md`); the line starts and stops nothing.
5. **The guide.** `docs/guides/project-ci.md` names the check in its table and describes the level, the day and `--line`.
   Flow mode: fragment `changelog.d/minutes-level.md`; no version bump.

## Consequences

- A person who runs the doctor or launch sees, from half of the plan's minutes on, how close the month is and when CI stops.
- With billing unreadable, the doctor reads the run history of the month (one read per run), as `minutes.py` does; that is slower
  but only happens when billing cannot answer.
- The doctor's test fixtures carry a billing answer (`tests/kit/fixtures/doctor/ok/api/billing.json`, nothing used); the
  doctor's counts and its live-read list grow by the one check and the one billing read.
- `minutes.py` is now imported by an installed script (the doctor); the reference test that recorded it as imported by none
  already reads only that the reference names it (changed on the default branch by brief #376), so this change leaves it as is.

## Residual

- 2026-10-30: the rate is a plain average of the month so far, so a busy first day gives an early day; a weighted rate is not
  part of this brief (due 2026-12-31).
