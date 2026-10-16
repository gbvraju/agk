# ADR-0024: every acceptance criterion needs a test (SPEC-0010 (a)), kit 0.13.0

- Status: Accepted
- Date: 2026-10-16
- Deciders: maintainers
- Related: ADR-0021, ADR-0022, ADR-0023
- Requirements: REQ-015, REQ-003

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`, `agk.toml`, `.claude-plugin/`, `docs/requirements.md`

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
   the audit's kinds and to its summary line. The facts document counts it too (`Q-K4-122`, item 8).
4. **This repository is set to `block`** in its own `agk.toml` (Q-K4-20), because it complies (rule 6): the recomputed list is in
   `docs/runs/proof-checks-live-1.md`; no `done` requirement fails today, so no status is changed. `agk.toml` is a protected path;
   this ADR names the class.
5. **Tests.** `tests/kit/test_check_requirements_ac.py` (12 tests: the fixture of criterion b, `warn` and `block`, the default, a bare
   marker, runs of requirements, unstructured and repeated lines, a stray marker, an invalid value, this repository's real
   requirements). Two existing tests carried literal `REQ-nnn ACn` data lines that this repository's own check would read as markers
   or strays; the data is now written so that no line of the file is a marker (`Q-K4-125`).
6. **REQ-003 gains AC4** (`Q-K4-121`, ruled): "every acceptance criterion of a `done` requirement has a test marker `REQ-nnn ACn`"
   (ADR-0021 decision 3). `docs/requirements.md` is a protected path and this ADR names the class. REQ-003 stays `done`: the fixture
   test of the new check carries the marker `REQ-003 AC4`, so the check stays `ok` in `block` mode on this repository.
7. **Kit 0.13.0** (a minor: a new rule and setting in installed scripts and templates); the plugin version follows;
   `kit/hashes.json` is regenerated.
8. **The facts document counts `D7`** (`Q-K4-122`, ruled). `facts.py` counts every kind of `drift_audit.CODES` and `total` is the
   number of findings of all of them. `docs/runs/proposed-spec-amendments-17.md` changes SPEC-0009 rule 15 (and the sentence of
   rule 20) from `D1` to `D6` to every kind the audit defines; this ADR applies it to `docs/specs/0009-facts.md`. `kit/facts-schema.json`
   gains `D7` and the goldens are regenerated. **`schema` stays `1`**: no consumer reads the document yet, so no reader can break.
   From the first consumer on, a change to a key raises it (SPEC-0009 rule 19).

## Consequences

- Questions `Q-K4-121` to `Q-K4-125` were ruled by the maintainers on 2026-10-16; the readings above are accepted.
- Installed repositories get the rule as a warning at their next `agk upgrade`; nothing blocks until they set `block` in their own
  pull request (with an ADR: `agk.toml` is protected).
- The weekly drift audit of an installed repository may open a `D7` finding for each stray marker.

## Questions

| Q | Question | Ruling |
| --- | --- | --- |
| Q-K4-121 ruled | SPEC-0010 rule 6 says REQ-003's acceptance gains AC4 "by an ADR when this spec is Approved". Adding it makes `done` REQ-003 fail in `block` until a marker `REQ-003 AC4` exists. | AC4 is added now (item 6); the check stays `ok` in `block` mode |
| Q-K4-122 ruled | The audit has a new kind `D7`; SPEC-0009 rule 15 lists `D1` to `D6`, and any change to a key raises `schema`. | the document counts every kind the audit defines, `D7` included; amendment 17 applied by this ADR; `schema` stays 1 (item 8) |
| Q-K4-123 ruled | In `block` mode a shortfall fails the check; should the audit also list it? | accepted: no: the audit lists stray markers always and shortfalls in `warn` only |
| Q-K4-124 ruled | The default value when `ac_coverage` is absent: SPEC-0010 says `warn` is "the default of the template". | accepted: `warn` in code as well, so existing targets migrate on their own time |
| Q-K4-125 ruled | Test data that looks like a marker counts as one in this repository. | accepted: two existing tests and the new ones write such data indirectly (`@` for `REQ-`) |

## Residual

- 2026-10-16: the sandbox run of criterion b (SPEC-0010 rule 21 (c)) needs the sandbox attached to a session; the implementation
  session asks for it and does not assume it (due 2026-11-16).
- 2026-10-16: a marker in a comment or a string counts alike (SPEC-0009 rule 9); a test file that quotes a marker as data therefore
  covers the criterion; the red-then-green check (part (b)) is the answer for new tests (due 2027-01-31).
