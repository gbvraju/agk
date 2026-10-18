# ADR-0039: intake, part 3 of 3: `next-steps`, the `/agk:spec "<sentence>"` form, the template and form edits, kit 0.19.0

- Status: Proposed
- Date: 2026-10-18
- Deciders: maintainers
- Related: ADR-0019, ADR-0021, ADR-0037, ADR-0038
- Requirements: REQ-019

Protected classes: `scripts/agk/`, `skills/`, `tests/kit/`, `tests/kit_dev/`, `kit/`, `.github/`, `.claude-plugin/`

## Context

The last of the three parts of SPEC-0012 (ADR-0037, ADR-0038). `intake.py` can allocate ids, render the ADR stub and check a draft; nothing yet
prints the next steps, the skill has no sentence form, and the facts do not treat the `## Open questions` section of a Draft spec file as an open
place. This part installs the pieces a target needs and applies the two amendments the maintainers ruled to be applied at implementation
(`docs/runs/proposed-spec-amendments-14.md`).

## Decision

1. **`python3 scripts/agk/intake.py next-steps [--base REF] [--date D]`** (rule 13) runs the checks first; if any fails it prints the failures and
   no next steps (exit 1). Otherwise it prints the commit message (`intake: add REQ-nnn <title>`), the push command for the current branch and a
   pull request body: `Advances: REQ-nnn`, a dated `Build-state row:`, `Decisions taken:`, `Questions:`, `Verified:`, and the statement that the
   checks cannot say that the criteria are the right ones (rule 12). The body passes `check_pr_body`. The commands are printed by the script,
   so the skill names no forbidden verb.
2. **The skill `/agk:spec`** (`skills/spec/SKILL.md`) gains the sentence form and `--from-issue N` on a proposal issue (rules 1, 3, 9, 10, 13, 15):
   a clean work tree, `git fetch`, `intake.py ids`, a branch cut from `origin/<default branch>`, at most three questions and `Q-S<spec>-<n>` ids for what
   stays open, `intake.py stub`, the two model-written pieces (the requirement section; the Draft spec) and no other file, `intake.py check`
   then `make governance` (at most three correction rounds), and `intake.py next-steps` last. The skill never commits, pushes or opens a pull
   request (SPEC-0005 rules 8 and 10; Q-K4-61 ruled). The forms of SPEC-0005 are unchanged.
3. **Amendments applied** (`proposed-spec-amendments-14.md`): SPEC-0005 rule 8, the `/agk:spec` row names `intake.py`; SPEC-0009 rule 13,
   `open_in` also lists a Draft spec file whose `## Open questions` section names the id. `facts.py` reads the section for Draft specs; the fixture
   `question-forms` gains a Draft spec with an open question, an id named in a rule outside the section, and an Approved spec with a question in the
   section (not an open place); its golden and the two report goldens built from it (`facts-question-forms`) are regenerated and read: the inbox now lists the Draft spec's question as waiting.
4. **Installed text**: `docs/specs/TEMPLATE.md` gains `## Open questions` (rule 18); the proposal issue form says to propose in one plain
   sentence of at most 300 characters (rule 15).
5. **Tests**: next steps (commit, push, body passes `check_pr_body`, refusal on a failing draft); the skill (no forbidden verb, no file other than the
   three of rule 4, user-invoked, the four script calls in order, the questions limit); after a merge the requirement is `planned`, the spec `Draft`,
   the ADR `Proposed`, the question is open and waiting in the inbox, and nothing is delivered (rule 14); the end-to-end test (`test_end_to_end.py`)
   runs a sentence through `ids`, `stub`, the written files, `check`, `make governance`, the merge, `facts.py` and the report. `test_distribution.py`
   now expects `intake` among the scripts the spec skill runs.
6. **Kit 0.19.0**: manifest, hashes and plugin version (installed files changed: `facts.py`, the template, the issue form, the tests).

## Consequences

- REQ-019 can be proven live: one real intake in this repository, then the pilot's from the issue form, by the pilot's own session (rule 17). The
  record `docs/runs/intake-proof.md` is the maintainers' step with the sessions' help and is not part of this change.
- A target upgraded to 0.19.0 gets the `facts.py` and template changes; the skill arrives with the plugin.

## Residual

- 2026-10-18: the live proofs of SPEC-0012 rule 17 (this repository, then the pilot from the issue form) are not done; the requirement stays `planned`
  until they are (due 2026-11-07).
