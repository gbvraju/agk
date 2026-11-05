# Proposed spec amendments 119 (SPEC-0041: the levels in team mode, owner ruling D2; REQ-048)

Date: 2026-11-05 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written
for ADR-0280 (brief #562), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0041-one-developer-adopts-agk-alone-with-nothing-of-agk-in-the-product-repository.md`. The number 119 is
the one the conductor reserved on #562. Brief #562 applies every item in the same pull request; because that pull
request also changes `constitution/` and `config/session-rules.md`, the owner merges it by hand. No safety rule
weakens: the floor of rule 18 is fixed in both modes, and no existing team-mode check is turned off by any item.

The owner's ruling D2 on plan #542 (comment 6635044641), quoted as data: "`light` is the default governance level for a
new adopter in team mode too, with the floor fixed at every level."

1. **A new rule 31, the levels in team mode.** A new section "Team mode (owner ruling D2, amendment 119)" after rule 30
   holds rule 31: the five levels of rule 17 also apply in team mode through a `[governance] level` setting in the
   repository's `agk.toml`, a new table that accepts exactly one key, `level`, with one of the five values of rule 17;
   `light` for a project that `init.py` or `adopt.py` sets up after build (o) lands; an existing project with no
   `[governance]` table or no `level` key reads as today, every team-mode check running as before; the floor of rule
   18 fixed in both modes and at every level; an unknown value, a value of the wrong type and any other key of the
   table refused naming the setting, never the value; in a sidecar the level stays `[personal] level`. The rule
   decides no existing team-mode check that a level leaves out: build (o) names each one with its own ADR
   (`Q-562-1`), and decides whether a team-mode `prepush.py` without gitleaks fails the floor (`Q-562-2`). The rule
   is appended after rule 30, so no number of rules 1 to 30 moves.
2. **Rule 30, build (o).** The build list gains, after (n): "(o) The `[governance] level` setting of rule 31: the
   table and its refusals in `scripts/agk/common.py` and `scripts/agk/doctor.py`, the `light` line in the `agk.toml`
   that `init.py` and `adopt.py` write (`kit/templates/agk.toml` and `kit/templates/agk.adopt.toml`), and, with its own
   ADR, each existing team-mode check that a level leaves out (rule 31, `Q-562-1`): `scripts/agk/`, `kit/`,
   `tests/kit/`. Depends on (h)." It is named here and not built.
3. **Tests, rule 31.** The Tests section gains, after the rule 30 bullet: after build (o), a team-mode fixture with no
   `[governance]` table runs every check it runs today; `init.py` and `adopt.py` on an invented project write
   `level = "light"`; each of the five values is accepted, and an unknown value, a value of the wrong type and a second
   key (for example `skip_floor`) are refused naming the setting and never the value; at every level a planted secret
   and a test that passed on the base and fails on the head fail the run; a sidecar reads `[personal] level` and never
   the `[governance]` table; REQ-048 AC5.
4. **The new session rule's number.** Amendment 113 named it session rule 36; the `Covered-by:` rule of ADR-0271 took
   36 first, and `session.py ids` gives 37 on 2026-11-05. The four places of SPEC-0041 that name it (rule 29, build
   (b) of rule 30, the first residual and `Q-S0041-16`) read "session rule 37". A number moved by a later merge is a
   mechanical change (session rule 15). The ruled row of `Q-S0041-16` in `docs/runs/decisions-log.md` is not edited.
5. **Tests of this amendment.** `tests/kit/test_personal_mode_rules.py` checks that this file names the spec's path,
   that rule 31 carries the setting, the `light` default for a new project, the unchanged reading of an existing one,
   the refusal and build (o), that build (o) and the rule 31 Tests bullet exist, and that the spec names the new
   session rule only as 37. Their marker is `REQ-048`.
