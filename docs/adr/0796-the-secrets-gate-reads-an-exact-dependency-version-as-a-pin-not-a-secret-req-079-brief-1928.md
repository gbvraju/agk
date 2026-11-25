# ADR-0796: The secrets gate reads an exact dependency version as a pin, not a secret (REQ-079)

- Status: Proposed
- Date: 2026-11-25
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1928, SPEC-0072 rules 2 and 7, SPEC-0042 rule 10 (brief #561), ADR-0673, ADR-0743, #1772 (v1 acceptance AD-06)
- Requirements: REQ-079

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

In v1 acceptance plan 3 (#1772, AD-06) a builder pinned every dependency of the adopted project and prepush's `secrets`
gate failed: each finding was an exact version after a package name such as `@typescript-eslint/visitor-keys` in
`package-lock.json`. The data guard's `key_like` splits the name on `_ . -`, finds the part `keys`, and SPEC-0042 rule 10
flags a version string next to a key-like name, so pinning, which the pins gate asks for, turned the secrets gate red. A
loose range is not flagged. The owner's word (2026-11-25, the steward chat, quoted as data): "Yes, file draft briefs 1 to
5 and the first slices of SPEC-0073 and SPEC-0074".

## Decision

1. **Dependency files read package names as names.** `gates/committed_secrets.shapes` takes the file's path. In a
   dependency file (the closed tuple `DEPENDENCY_FILES`, compared on the last path part, case-folded) a `SECRET` finding
   is not counted only when its value fully matches `guard.VERSION` (an exact version; a range is not matched) and the
   key before it on its line holds `/` or `@` or is not one of the whole setting words `token`, `secret`, `password`,
   `passwd`, `pwd`, `auth`, `credential`, `api_key`. A `[guard] patterns` match on that value still counts, as does every
   other finding in the file (a gitleaks rule, a hex or high-entropy value, a `TOKEN`, a `JWT`).
2. **Nothing else changes.** `guard.py`, `scan_text`, SPEC-0042 rule 10, the data guard hook, every other caller and
   gitleaks are unchanged. The tuple skips no file and no rule and no ignore list grows (principle 9); the refusal still
   names the path class, never a value (principle 8).
3. **The class stays closed.** A test asserts that every build, lock and root requirements file name the pins gate reads
   is in `DEPENDENCY_FILES`.

This is not a weakening (principle 11): a version string is no secret shape on its own (SPEC-0042 rule 10), and a package
name in a dependency file is not a key-like setting name.

## Consequences

Pinned lock files pass the secrets gate in `prepush.py`, `make governance`, the `proof` job and `personal.py floor`. An
adopted project's baseline that held these false findings reads a lower count and stays green, while a new real finding
still fails (SPEC-0072 rule 7). SPEC-0072's text names no detector, so no amendment is proposed (`Q-F1-1`).

## Residual

- 2026-11-25: whether `guard.key_like` itself should stop splitting package names, for the data guard too, is open
  (`Q-F1-2`); not in this decision.
