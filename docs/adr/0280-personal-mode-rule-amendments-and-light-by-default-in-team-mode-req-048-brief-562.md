# ADR-0280: Personal mode's rule amendments, and `light` by default in team mode too (REQ-048, brief 562)

- Status: Accepted
- Date: 2026-11-05
- Deciders: maintainers
- Related: ADR-0267, ADR-0271, SPEC-0041
- Requirements: REQ-048

Protected classes: `constitution/`, `config/`, `tests/kit/`

## Context

SPEC-0041 (Approved, ADR-0267) lists build (b): the principle 10 amendment, a new session rule and one line in
`config/core-rules.md`, as items 1, 2 and 9 of `docs/runs/proposed-spec-amendments-113.md`. A change of
`constitution/` needs its own ADR (session rule 36), so this build writes one; ADR-0267 does not cover it. The
owner ruled D2 on plan #542 (comment 6635044641, quoted as data): "`light` is the default governance level for a new
adopter in team mode too, with the floor fixed at every level", to be folded into SPEC-0041. Brief #562 asks for both
in one pull request; the conductor reserved this number and amendment 119 on it.

Amendment 113 named the new session rule 36. Rule 36 was taken since by the `Covered-by:` rule of ADR-0271, and
`session.py ids` gives 37 on 2026-11-05; a number moved by a later merge is a mechanical change (session rule 15).

## Decision

1. **Principle 10.** "Dates come from `date -u`; PR bodies state what they advance; tests carry REQ markers." becomes
   "Dates come from `date -u`; PR bodies state what they advance; tests carry REQ markers or, in personal mode, the
   state's test map." No other principle changes. Until build (e) of SPEC-0041, which reads `test-map.toml` in a
   sidecar only, `check_requirements.py` counts markers in tests exactly as before, and in a team-mode repository it
   always does (`Q-S0041-6`).
2. **Session rule 37.** `config/session-rules.md` gains rule 37: "In personal mode (a sidecar with `forge = "files"`,
   SPEC-0041) a session never pushes to a remote of the product, never runs `personal.py confirm` or `sync`, and never
   strips, rewrites or amends an attribution trailer; the developer pushes, confirms and syncs." `config/core-rules.md`
   gains one safety line for it. No other session rule changes.
3. **Ruling D2, as amendment 119 to SPEC-0041.** SPEC-0041 gains rule 31: the five levels of rule 17 also apply in
   team mode through a new `[governance]` table with one key, `level`; `light` for a project that `init.py` or
   `adopt.py` sets up after the implementing build lands; an existing project with no `level` key reads as today; the
   floor of rule 18 is fixed in both modes; an unknown value or key is refused naming the setting, never the value.
   No existing team-mode check is turned off by this amendment: which check a level leaves out is decided by the
   build that implements the setting, build (o), with its own ADR (principle 11). This pull request writes the rule,
   its Tests bullet and the build's line, and builds no code.
4. **The rule number in SPEC-0041.** The four places of SPEC-0041 that name the new rule (rule 29, build (b) of
   rule 30, the first residual and `Q-S0041-16`) read "session rule 37". The ruled text of `Q-S0041-16` in `docs/runs/decisions-log.md`
   is not edited (the log is only appended).
5. **Tests first.** `tests/kit/test_personal_mode_rules.py` pins principle 10, the other eleven principles, session
   rule 37, its core-rules line and the applied amendment; `tests/kit/test_core_rules_page.py` lists session rule 37
   among the safety rules. No network.

## Consequences

Personal mode can count a criterion's test through the state's test map without writing a marker into the customer's
tests, once build (e) reads it; team mode reads principle 10 as before. A session in personal mode has one rule that
names what it never does. A new team-mode adopter will start at `light` once build (o) lands; nothing changes for an
existing project until it sets the key, and no setting lowers the floor. The owner merges this pull request by hand,
because it changes `constitution/` and `config/session-rules.md`.

## Residual

- 2026-11-05: what `light` turns off in team mode is not decided here; build (o) names each existing check a level
  leaves out, and until it merges the `[governance]` table does not exist and every team-mode check runs (`Q-562-1`).
- 2026-11-05: the floor in team mode is the secret scan and the no-regression rule as the required checks already
  run them; whether a team-mode `prepush.py` without gitleaks should fail the floor, as personal mode's does
  (`Q-S0041-15`), is left to build (o) (`Q-562-2`).
