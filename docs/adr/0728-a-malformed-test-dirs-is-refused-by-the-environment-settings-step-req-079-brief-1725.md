# ADR-0728: A malformed test_dirs is refused by the environment-settings step (REQ-079)

- Status: Proposed
- Date: 2026-11-22
- Deciders: maintainers
- Related: brief #1725, SPEC-0072, ADR-0673, ADR-0717
- Requirements: REQ-079

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

On the default branch at 7086c33 (2026-11-22) the `environment-settings` step (ADR-0673) reads `test_dirs` from
`agk.toml` as it stands, because `common.load_config` does not validate it. A list of non-strings, for example
`test_dirs = [1]`, stops `run_gates.py` with an `AttributeError` traceback in any git project with a tracked Python file,
whatever the work type, instead of a refusal naming the setting (principle 8). The `injection-set` step (ADR-0717
decision 5) already refuses such a value, but the run stops at this step first.

## Decision

1. The step refuses a `test_dirs` value that is not a list, or that holds an entry that is not a folder inside the
   repository (as `impact._folder_ok` reads one), with one `FAIL gates: ...` line naming `test_dirs`, never the value,
   and exit 1.
2. A leading `./` and a trailing `/` are dropped before an entry is read, as the tests floor does, so `./tests` stays a
   folder. An empty list stays valid here: no test folder.
3. The `injection-set` step's own rule (ADR-0717) and `common.load_config` are unchanged.

## Consequences

A malformed `test_dirs` gives one refusal naming the setting in `run_gates.py`, `make governance` and `prepush.py`,
for every work type and the default playbook. A value that was read before (a list of folders) gives the same result as
before. No workflow, ruleset or required check changes.

## Residual

- `common.load_config` still hands each reader the raw value; validating it once there is a separate change.
