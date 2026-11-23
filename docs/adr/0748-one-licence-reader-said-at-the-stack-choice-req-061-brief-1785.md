# ADR-0748: One licence reader, an off-list licence said at the stack choice, and the check names the accept's refusals (REQ-061)

- Status: Proposed
- Date: 2026-11-23
- Deciders: maintainers
- Related: SPEC-0054 rule 4, SPEC-0029 rule 5, ADR-0676, ADR-0671, ADR-0744, brief #1785, plan #661
- Requirements: REQ-061

Protected classes this pull request changes: `scripts/agk/` (`gates/licences.py`, `engines.py`), `skills/`
(`stack/SKILL.md`), `tests/kit/` (`test_product_deps.py`) and `tests/kit_dev/` (`test_engines_stack.py`).
`kit/hashes.json` is not edited by hand.

## Context

On main at 608f073 (2026-11-23) `engines.py` read a stack record's licence with its own pattern, which wants a first
character that is a digit or a capital, so real SPDX ids that start in lower case (SQLite's `blessing`, `curl`,
`bzip2-1.0.6`) failed `stack-check` as `has no licence id`. The `licences` gate kept a second reading of an expression
and compared ids exactly, so a lock stating `mit` failed a list holding `MIT`. A part whose licence was off the
project's list was first said by the gate, after the stack was accepted and the lock made. And `stack-accept` refused
records that `stack-check` passed (an option with no one profile in its `test selection` practice), because the check
did not run the accept's own conditions.

## Decision

1. `scripts/agk/gates/licences.py` holds the one reader of a licence: `LICENCE_ID` (an SPDX `idstring` of any case
   with an optional `+`, or `LicenseRef-<id>`, or `DocumentRef-<id>:LicenseRef-<id>`), `expression(text)` (ids joined
   by `AND`, `OR` and `WITH`, with balanced parentheses; a function, since nested parentheses are no regular pattern)
   and `ids(text)`, the ids case-folded. `engines.py` reads each part's licence with `expression` in place of its own
   pattern. `passes` evaluates the parsed expression: `OR` needs one side, `AND` every side, and an id or an
   `<id> WITH <exception>` term is compared case-folded against the list; `MIT+` is compared as `MIT+`.
2. `engines.py stack-check`, on records that pass, prints one note per part whose licence `passes` refuses against the
   project's list (`config/licences.toml`, else the gate's `DEFAULT`): `note: option <X> part <n> licence is not on the
   allowed list (setting: config/licences.toml); choosing it needs a project ADR that widens the list (principle 11)`,
   never a failure and never naming the id; a list not of its form prints `note: the allowed list is not of its form
   (setting: config/licences.toml)` once and no per-part note. The gate still fails on it after, as before.
3. `engines.py` gains `accept_problems(root, text, letter)`: the refusals of `stack-accept` that depend on the record
   (every refusal of `testing_copy`, and an accepted text that would fail the check). `stack-accept` refuses with its
   first before writing; `stack-check` prints each, for every option of a Proposed record that passes, as `note:
   option <X> cannot be accepted: <the refusal>`. A test reads the source and fails when a refusal is added to the
   accept that neither the check reaches nor the test names as independent of the record.
4. Any future tool's licence takes this one path: its real SPDX id is read; the project's list is the policy, said at
   the choice and enforced at the gate; widening is one project ADR that edits `config/licences.toml`, as the `stack`
   skill's step 4 says. The kit's `DEFAULT` list is not changed (`Q-F2-1`).

## Consequences

A project choosing SQLite, curl or any other tool with a real SPDX id passes `stack-check`, and is told at the choice,
not after the lock, that the licence needs its own ADR. A record that the accept would refuse is named by the check
first. GitHub, local (`prepush.py`) and personal modes run the same readers; no workflow changes and no licence list is
fetched or vendored.

## Residual

- 2026-11-23: whether the kit's default list should also allow `blessing`, `0BSD`, `Unlicense`, `CC0-1.0`, `Zlib` and
  `BSL-1.0` is open with the owner as `Q-F2-1`.
- 2026-11-23: a lower-case word that is no SPDX id (`mit-ish`) now passes the form; the note and the gate catch it as
  off the list.
