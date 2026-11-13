# ADR-0492: The testing guide maps one entry per module

- Status: Proposed
- Date: 2026-11-12
- Deciders: maintainers
- Related: brief #1156, issue #487, ADR-0220, ADR-0242, ADR-0393
- Requirements: REQ-062

Protected classes: `agk.toml`, `tests/kit/`

## Context

Issue #487 (the pilot run of 2026-11-02 on AGK 0.63.0) found one `[[testing.map]]` entry `backend/** -> all backend tests`:
every back-end pull request ran the full 19-minute suite. `docs/guides/testing.md` described the `[testing]` table, its
profiles and `always_full`, but gave no worked map for a project with modules and no warning that one broad entry selects
everything.

## Decision

`docs/guides/testing.md` has a section "A map per module": a `[testing]` table for an invented project with
`backend/orders/`, `backend/users/` and `frontend/src/`, one `[[testing.map]]` entry per module naming its own tests, and the
shared `backend/common/**` in `always_full` with its `# full: <reason>` comment. It says that one `backend/**` entry runs every
back-end test on every change, and that the full suite still runs on each push to the default branch, once per merge wave.

`tests/kit/test_guide_testing_map.py` reads the example, parses it as TOML, checks its `code` and `tests` keys and the
`always_full` rule, and runs `test_plan.py` on a fixture repository: a change to `backend/orders/x.py` selects only
`tests/backend/orders/`, and a change to `backend/common/x.py` selects the full suite. The `scripts/agk/test_plan.py` entry of
`[[testing.map]]` in `agk.toml` lists the test. No script, setting or default changes.

## Consequences

A project that copies the guide's example gets a per-module selection on its pull requests, and the guide's example cannot
drift from what the selection does without a red test.

## Residual

None.
