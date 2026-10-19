# ADR-0043: `/agk:start` and its checks (SPEC-0013 rules 1 to 5), kit 0.23.0

- Status: Accepted
- Date: 2026-10-19
- Deciders: maintainers
- Related: ADR-0001, ADR-0021, ADR-0042
- Requirements: REQ-020

Protected classes: `scripts/agk/`, `skills/`, `tests/kit_dev/`, `kit/`, `.claude-plugin/`

## Context

G4, the last part of the four-part build of SPEC-0013 (ADR-0040 to ADR-0042). G5 follows it: rule 18's "At risk" line (ruled 2026-10-19). Nothing here is
installed in a target: `playbook.py` is kit-only and the skill ships in the plugin. The kit version is bumped because the plugin gains a skill (SPEC-0013 rule 29).

## Decision

1. **`/agk:start "<problem statement>"`** (rules 1 to 4; `skills/start/SKILL.md`, user-invoked): a statement of at most 1,500 characters in one or more paragraphs; it
   refuses, with the instruction to run `/agk:init` or `/agk:adopt` first, when `agk.toml` is absent and installs nothing (`playbook.py start-ids`); it cuts a branch
   `start/<slug>` from `origin/<default branch>` and writes exactly two files: `constitution/vision.md` (the installed placeholder replaced by the four headings and,
   optionally, `## Project rules` with every line marked `<!-- project-specific -->`) and the project charter ADR `docs/adr/<next free>-project-charter.md` (Proposed, a
   `Protected classes:` line naming `constitution/`, a Decision with the numbered items **Milestones**, **Non-goals**, **Done means**). `constitution/principles.md` is not
   edited. It never commits, pushes or opens a pull request: `playbook.py next-steps` prints the commit message, the push command and a pull request body.
2. **`playbook.py check-start [--base REF]`** (rule 5; messages name the rule, never the text): the difference from the merge base is the vision (modified) and one new
   charter ADR; `constitution/principles.md` is byte-identical to the base; the vision has no `TODO(maintainers)`, has the four headings in order, and every non-blank
   line under `## Project rules` carries the marker; the charter passes `check_adrs.validate`, is Proposed, has the three headed items, every milestone line has `exit:`
   and a measurable statement (a digit, or all, every, none, zero), names `constitution/`, and its number is the next free ADR number read from the merge base by
   `common.next_free_ids`. The skill then runs `make governance`; at most three correction rounds.
3. **`playbook.py next-steps`** refuses (exit 1, no commands) on a detached HEAD, on the default branch, or when `check-start` fails, as `intake.py next-steps` does.
4. **The existing-codebase path** (the brief's words): `/agk:start` works after `/agk:adopt` as it does after `/agk:init`. A test runs the whole start in a target made by
   `init` and in a target made by `adopt` on a repository that already has code, with the target's own `Makefile` (`make -f agk.mk agk-governance` passes in both).
5. **Amendment applied** (`proposed-spec-amendments-15.md` item 1, the last part): SPEC-0005 rules 8 and 9 gain `/agk:start`; the plugin now has eleven skills, as the amendment
   says the test of rule 19 expects.
6. **Tests** (`tests/kit_dev/test_playbook.py`, `test_distribution.py`): ids from the base, the refusals, the statement limits (empty, 1,501, exactly 1,500 in two paragraphs),
   a good start, each failing check, the optional project rules, messages that never carry the text, the printed next steps (passing `check_pr_body`) and their refusals,
   the skill text (user-invoked, two files, no forbidden verb, the three script calls), and the two real targets.
7. **Kit 0.23.0**: manifest, hashes, plugin version.

## Consequences

- The first sequence of SPEC-0013 rule 1 is complete: install, protect (`/agk:ruleset`), start, architect, brief, build, review, merge. What remains is the maintainers' proof
  of criterion g (rule 28) and G5.

## Questions

| Q | Question | Reading taken, and the ruling (maintainers, 2026-10-19: Q-K4-185 to 187 ruled as read) |
| --- | --- | --- |
| Q-K4-185 ruled | "The existing-codebase path" (the brief's phrase) is not a rule of SPEC-0013. | `/agk:start` after `/agk:adopt`: the same skill and checks, proven by a test in an adopted target (Decision 4). Nothing else is built. Ruled as read; the baseline-requirements guide for existing codebases is a launch-docs item, not G4. |
| Q-K4-186 ruled | The start pull request needs `Advances: REQ-nnn` (`check_pr_body`), and a start has no requirement of its own. | `REQ-001` (protected paths change only with an ADR): the vision is under `constitution/`, which the charter's ADR names. `check_specs` rule a exempts it (no spec names it and ADR-0001 does). Ruled as read. |
| Q-K4-187 ruled | The charter's `Requirements:` field. | `REQ-001`, for the same reason. Ruled as read. |

## Residual

- 2026-10-19: the checks cannot tell that the milestones are the right ones or that the vision says what the person meant; that is the review (SPEC-0013 rule 5).
