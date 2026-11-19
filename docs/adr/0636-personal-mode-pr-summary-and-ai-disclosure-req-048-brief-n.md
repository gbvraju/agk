# ADR-0636: Personal mode prints a summary of the change and always discloses AI use

- Status: Proposed
- Date: 2026-11-19
- Deciders: maintainers
- Related: ADR-0267, ADR-0634, SPEC-0041, brief #1505
- Requirements: REQ-048

Protected classes: `scripts/agk/`, `tests/kit/`, `agk.toml`

## Context

SPEC-0041 rule 21 asks for `personal.py pr-summary`, which prints, and never posts, a plain description of the change
for the developer to paste into the team's own pull request. Rule 22 asks that `[personal] ai_disclosure` makes AI use
visible by a commit trailer, a note in that description or both, and that no AGK command strips, rewrites or amends a
trailer or a commit. On main the `[personal]` table accepts `ai_disclosure` (`common.personal_table`, `both` by default,
`none` refused) but nothing reads it, and there is no `pr-summary` and no `status`. ADR-0267 asks each build of the spec
for its own ADR naming its classes; this is build (j).

## Decision

1. `personal.py pr-summary [--clone DIR] [--sidecar DIR]` reads `records/gates/<head>.json` of the sidecar for the
   clone's head and prints, from its steps only: the secret scan, the no-regression step (the tests), the
   tests-first step where the level ran it, whether a review was done, every other step by its name, and the gate's
   result and level. It writes nothing, posts nothing and runs no command but read-only git. With no record for the
   head it says so, prints no result and exits 1.
2. With `[personal] team_refs` off (the default) every `REQ-nnn`, `SPEC-nnnn` and `ADR-nnnn` is left out of what it
   prints; with `team_refs = true` they stay.
3. `pr-summary` and `personal.py status [--clone DIR] [--sidecar DIR]` print the disclosure in force, naming the
   setting `personal.ai_disclosure`. With `pr-note` or `both`, `pr-summary` ends with the fixed line `This change was
   made with the help of an AI coding assistant.` A value of `none` or any other value is refused by
   `common.personal_table` unchanged, naming the setting and never the value.
4. With `commit-trailer` or `both` the gate (ADR-0634) prints, for each commit of the branch whose message has no
   `Co-Authored-By:` trailer, one warning naming the setting. It is a warning: the gate's result does not change, and
   the gate never adds, amends or rewrites a trailer or a commit; the developer adds it.
5. No `personal*.py` script holds `--amend`, `rebase`, `filter-branch` or `notes` as a constant of an argument list; a
   test reads every such script's syntax tree.
6. `agk.toml` maps `scripts/agk/personal.py` to `tests/kit/test_personal_disclosure.py` as well.

## Consequences

A developer can paste a description of what the gate found, AI use shows in the description by default, and a commit
without a trailer is named before the push. The kit cannot tell which commit an agent session made, so the warning
names every commit of the branch without the trailer (`Q-1505-1`).

## Residual

- 2026-11-19: "the trailer the project's policy sets" has no setting among the ten keys of rule 18; the gate reads any
  `Co-Authored-By:` trailer as the trailer (`Q-1505-1`), and a project-specific trailer waits for a spec change.
