# ADR-0706: The standards pack gets the plugin root from the resolver (REQ-079)

- Status: Proposed
- Date: 2026-11-22
- Deciders: maintainers
- Related: ADR-0630, ADR-0700, SPEC-0071, SPEC-0072, brief #1696, plan #661
- Requirements: REQ-079

Protected classes this pull request changes: `scripts/agk/` (`gates/python_pack.py`, `kit_root.py`) and `tests/kit/`
(`test_python_pack.py`). `kit/hashes.json` is not edited by hand.

## Context

On the default branch at 1e852015 (2026-11-22) `tests/kit_dev/test_distribution.py` fails two tests of REQ-014 AC3
(ADR-0630): `scripts/agk/gates/python_pack.py` holds the plugin variable in its install line of the clean layout
(ADR-0700, brief #1683), and `scripts/agk/kit_root.py` is the one verbatim script allowed to name it.

## Decision

1. `kit_root.py` holds the plugin root as a command names it (`PLUGIN_ROOT`); `PLUGIN_FORM` is built from it, with
   the same text as before.
2. `python_pack.install_line` builds the clean layout's install line from `kit_root.PLUGIN_ROOT`, so the printed line
   is unchanged: `python3 -m pip install -r "${CLAUDE_PLUGIN_ROOT}/config/ci-tools.txt"` with `[kit] layout =
   "plugin"`, otherwise `python3 -m pip install -r config/ci-tools.txt`; an unreadable or unknown layout keeps the
   installed line, as before. `python_pack.py` no longer names the variable.
3. No test is weakened (principle 11): `tests/kit_dev/test_distribution.py` is not edited.

## Consequences

The default branch's governance run is green again on these tests; every mode prints the same line as before.

## Residual

None.
