# ADR-0024: every acceptance criterion needs a test (SPEC-0010 (a)), kit 0.13.0

- Status: Proposed
- Date: 2026-10-16
- Deciders: maintainers
- Related: ADR-0021, ADR-0022, ADR-0023
- Requirements: REQ-015, REQ-003

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`, `agk.toml`, `.claude-plugin/`

## Context

SPEC-0010 (Approved) has two parts: (a) every acceptance criterion of a `done` requirement needs a `REQ-nnn ACn` test marker, and
(b) red-then-green. The day-12 brief splits them (measured: the whole is well over 600 changed lines of code and tests). This is
the first pull request, part (a), serving exit criterion b of ADR-0021; part (b) follows.

## Decision

1. **The rule** (SPEC-0010 rules 1 to 3). `check_requirements.py` fails or warns, for each `done` requirement, on a criterion with no
   `REQ-nnn ACn` marker (`done requires a test marker for AC2`), on an acceptance line with no `ACn` token, and on a repeated number
   (`acceptance repeats AC2`). The message names the requirement and the criterion id, never the criterion's text. The criteria
   and the markers are those of `common.parse_acceptance` and `common.find_ac_markers`; the shortfall logic is one function,
   `common.ac_shortfalls`, used by the check and by the drift audit. The existing rule (some marker) is unchanged.
2. **The switch** (rule 5). `agk.toml` gains `ac_coverage`, `warn` or `block`; the default when the key is absent, and the value in
   both templates, is `warn`; any other value is a refusal that names the setting. `common.DEFAULT_CONFIG` carries the key.
3. **Drift finding `D7`** (rules 4 and 5). The drift audit reports each stray marker (`REQ-nnn ACn` where the requirement has no
   `ACn` or does not exist) and, in `warn` mode only, each shortfall (in `block` mode the check fails instead). `D7` is added to
   the audit's kinds and to its summary line. The facts document keeps counting `D1` to `D6` (SPEC-0009 rule 15 names them); `D7`
   is in the audit and not yet in the document (`Q-K4-122`).
4. **This repository is set to `block`** in its own `agk.toml` (Q-K4-20), because it complies (rule 6): the recomputed list is in
   `docs/runs/proof-checks-live-1.md`; no `done` requirement fails today, so no status is changed. `agk.toml` is a protected path;
   this ADR names the class.
5. **Tests.** `tests/kit/test_check_requirements_ac.py` (12 tests: the fixture of criterion b, `warn` and `block`, the default, a bare
   marker, runs of requirements, unstructured and repeated lines, a stray marker, an invalid value, this repository's real
   requirements). Two existing tests carried literal `REQ-nnn ACn` data lines that this repository's own check would read as markers
   or strays; the data is now written so that no line of the file is a marker (`Q-K4-125`).
6. **Kit 0.13.0** (a minor: a new rule and setting in installed scripts and templates); the plugin version follows;
   `kit/hashes.json` is regenerated.

## Consequences

- Installed repositories get the rule as a warning at their next `agk upgrade`; nothing blocks until they set `block` in their own
  pull request (with an ADR: `agk.toml` is protected).
- The weekly drift audit of an installed repository may open a `D7` finding for each stray marker.

## Questions

| Q | Question | Reading taken |
| --- | --- | --- |
| Q-K4-121 | SPEC-0010 rule 6 says REQ-003's acceptance gains AC4 "by an ADR when this spec is Approved". Adding it makes `done` REQ-003 fail in `block` until a marker `REQ-003 AC4` exists. | not done here: `docs/requirements.md` is unchanged; the maintainers decide whether to add AC4 with its test |
| Q-K4-122 | The audit has a new kind `D7`; SPEC-0009 rule 15 lists `D1` to `D6`, and any change to a key raises `schema`. | the document counts `D1` to `D6` only (`FACT_CODES`); `total` is their sum; the weekly drift issue shows `D7`; whether the document should carry it is for the maintainers (an amendment and `schema` 2) |
| Q-K4-123 | In `block` mode a shortfall fails the check; should the audit also list it? | no: the audit lists stray markers always and shortfalls in `warn` only |
| Q-K4-124 | The default value when `ac_coverage` is absent: SPEC-0010 says `warn` is "the default of the template". | `warn` in code as well, so existing targets migrate on their own time |
| Q-K4-125 | Test data that looks like a marker counts as one in this repository. | two existing tests and the new ones write such data indirectly (`@` for `REQ-`) |

## Residual

- 2026-10-16: the sandbox run of criterion b (SPEC-0010 rule 21 (c)) needs the sandbox attached to a session; the implementation
  session asks for it and does not assume it (due 2026-11-16).
- 2026-10-16: a marker in a comment or a string counts alike (SPEC-0009 rule 9); a test file that quotes a marker as data therefore
  covers the criterion; the red-then-green check (part (b)) is the answer for new tests (due 2027-01-31).
