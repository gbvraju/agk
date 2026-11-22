# ADR-0700: A new Python product passes the standards pack on day one (REQ-079)

- Status: Proposed
- Date: 2026-11-22
- Deciders: maintainers
- Related: SPEC-0072, ADR-0669, ADR-0674, brief #1683, plan #661
- Requirements: REQ-079

Protected classes this pull request changes: `kit/` (the Python skeleton under `kit/templates/skeleton/python/` and
`kit/templates/project-readme.md`), `scripts/agk/` (`gates/python_pack.py`) and `tests/kit/`
(`test_skeleton_basics.py`, `test_python_pack.py`). `kit/hashes.json` is not edited by hand.

## Context

On the default branch at ad938271 (2026-11-22) the skeleton that `basics.py write` writes for a web app, an API
service and a data pipeline fails the kit's own Python pack (ADR-0669): ruff `E501` on two lines longer than the
stack's `line-length = 100`, and mypy `union-attr` in the settings check. A pack tool missing from the running Python
is refused naming the tool and the setting, but not how to install it, so a person who has `ruff` only as a command
does not know what to do.

## Decision

1. The skeleton is clean under the pack: the two long lines are shortened and `_set` narrows `None` before it reads
   the value. No rule of the pack and no configuration changes (principle 11).
2. The refusal of a missing tool stays one line per tool, naming the tool and the setting, and ends
   `; install: <line>`: `python3 -m pip install -r "${CLAUDE_PLUGIN_ROOT}/config/ci-tools.txt"` with
   `[kit] layout = "plugin"`, otherwise `python3 -m pip install -r config/ci-tools.txt`. It never names a version
   (principle 8). The product's README template says the same once.
3. A tool found only as a command on `PATH` still counts as missing: the pack runs the module of the running Python
   so that the pinned version is the one that checks (the brief's Q-1, its recommendation).

## Consequences

A new Python product's first governance run passes the pack; the skeleton's test now runs the pack over each shape,
so a skeleton change that breaks it fails in the kit. A project's own code is checked as before; nothing in it is
rewritten.

## Residual

- None.
