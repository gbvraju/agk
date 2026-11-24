# ADR-0744: A capitalised runtime in the stack record is read as that runtime (REQ-079)

- Status: Accepted
- Date: 2026-11-23
- Deciders: maintainers
- Related: SPEC-0072 rule 4, SPEC-0029 rule 5, ADR-0672, ADR-0742, brief #1778, plan #661
- Requirements: REQ-079

Protected classes this pull request changes: `scripts/agk/` (`gates/pins.py`, `engines.py`), `tests/kit/`
(`test_pins.py`) and `tests/kit_dev/` (`test_engines_stack.py`). `kit/hashes.json` is not edited by hand.

## Context

On main at ee47218 (2026-11-23) `pins.option_parts` kept each part's name as written, and `pins.pick`, the tests floor
and the layers step keep a part only when its name is a key of `pins.STACKS` (`python`, `node`). A stack record written
as people write it, `Parts: Node 22.11.0 MIT, ...` or `Python 3.13.1 PSF-2.0, ...`, therefore read as `no stack chosen`:
the pins, the standards pack, `layers` and the tests floor's runtime said not run, and `engines.py stack-check` passed
the record without a word.

## Decision

1. `pins.option_parts` returns a part whose name equals a `STACKS` key when case is ignored as that key, in lower case
   (`Node` → `node`, `PYTHON` → `python`), and every other name as written. Its readers (`pick`, the tests floor,
   `layers`, the packs) find the runtime with no change of their own.
2. Only a difference of case of the exact key is read (`Q-F3-1`, its conservative reading): `Node.js` and `nodejs` are
   not `node`. Two runtime parts in one option still read as none. Versions and licences are unchanged.
3. With a `[delivery] work_type` declared, `engines.py stack-check` on a record that passes prints, after `ok
   engines-stack`, one line per option whose parts name no runtime the kit checks: `note: option <X> names no runtime
   the kit checks (python, node); its pins and standards pack will not run`. It is a note, never a failure; without a
   work type nothing is printed.

## Consequences

A project whose Accepted record names `Node` or `Python` gets its pins, standards pack, layers and tests floor in
`governance`, `make governance` and `prepush.py`, in GitHub, local and personal modes alike, with no workflow change.
The person or architect is told, before accepting, of an option whose checks would not run.

## Residual

- 2026-11-23: whether `Node.js` and `nodejs` should read as `node` too is open as `Q-F3-1`.
