# ADR-0047: launch docs L1: the README, the getting-started guide, the "I got stuck" form and the docs check

- Status: Accepted
- Date: 2026-10-19
- Deciders: maintainers
- Related: ADR-0025, ADR-0021, ADR-0046
- Requirements: REQ-020

Protected classes: `.github/`, `tests/kit_dev/`

## Context

The maintainers' launch-docs brief (2026-10-19) asks for the documents a first outside developer needs, who has Claude Code and a GitHub repository, works alone and has no
maintainer in the session. L1 is the first of two pull requests: the README, the getting-started guide, the "I got stuck" issue form and a check that the documents name only what
exists. L2 (product-owner guide, existing-codebase path, security page) follows.

ADR-0025 sets the launch minimum (README, product-owner guide, one-page security posture, existing-codebase path) for 2026-11-20. The brief pulls these rows forward: **L1 merged by
2026-10-26, L2 by 2026-10-28**, and the first outside developer starts about 2026-11-02. The ADR-0025 dates of the rows are not changed by this ADR; they are met earlier.

## Decision

1. **`README.md` is rewritten** (73 lines): what AGK is in five lines, who it is for and what it needs, the 10-minute path as a numbered list, what arrives each week, honest
   limits and links. The former command reference moves to `docs/guides/reference.md`; three rows (`/agk:ruleset`, `/agk:start`, `/agk:architect`) and the intake form of
   `/agk:spec` are added to its command table (Q-K4-195). The tests that read the README for those sections (`test_distribution.py`, `test_experimental_reviewer.py`,
   `test_kit_manifest.py`) now read `docs/guides/reference.md`.
2. **`docs/guides/getting-started.md`** takes a new repository from nothing to the first governed merge: twelve steps, each with its command and what to see, and a section "When
   something goes wrong". It claims only what a live proof in `docs/runs/` shows and links the proof; the two steps with no live proof (applying the ruleset, the architect session)
   say so in their headings. The README says the same in its limits. It makes no claim that AGK catches defects, saves money or beats another tool.
3. **`.github/ISSUE_TEMPLATE/stuck.md`** ("I got stuck", label `agk-stuck`) asks five things and nothing else. It is for this repository only: it is not in `kit/manifest.json` and
   not installed in targets (Q-K4-192). The label does not exist yet; the maintainers create it (the session has no label write).
4. **`tests/kit_dev/test_docs.py`** is the docs check: it reads every fenced block, indented code block and inline code span of `README.md` and `docs/guides/*.md` and fails on a
   script under `scripts/agk/`, a skill `/agk:<name>`, a make target or a workflow file that does not exist on the branch, and on a relative link to a missing file. It carries tests
   of the check on small trees and tests of the shape the brief asks for. `test_kit_manifest.py` learns the one repository-only file, `stuck.md`.
5. **Live walk**: `docs/runs/docs-walk-1.md` records the walk of the guide on a throwaway repository, what was walked and what was not, and nine findings; eight are fixed in the
   guide, the ninth is a script message and is a question (Q-K4-191).
6. **No kit bump**: no installed file changes (the README, the guides, `stuck.md`, `tests/kit_dev/` and this ADR are not installed).

## Consequences

- A reader can follow the guide as far as the live proofs go. Where a step has no proof, the guide says so, and the first outside developer is the proof.
- A command, skill, make target or workflow that is renamed or removed fails `make test` until the guides are changed.
- Every outside "I got stuck" issue names a guide and a step number, so it can become a fix to the guide or a check.

## Questions

| Q | Question | Reading taken (conservative) |
| --- | --- | --- |
| Q-K4-191 | `playbook.py check-start` prints "the Decision lacks the numbered items Milestones, Non-goals, Done means" also when the three items exist but have no list lines under them | ruled (maintainers, 2026-10-19): a residual, not fixed here; the guide does not depend on it because the session writes the files |
| Q-K4-192 | Is the "I got stuck" form installed in targets? | ruled: the maintainers create the label `agk-stuck`; the form is repository-only, exempted by name in `test_kit_manifest.py`. **Done** (maintainers, 2026-10-19): the label `agk-stuck` exists on the repository, so the template label is applied |
| Q-K4-193 | No requirement names the launch docs | the pull request advances REQ-020 (the requirement ADR-0025 names) and marks its tests `REQ-020 AC1`; nothing is marked done and no requirement is added |
| Q-K4-194 | The README sections that tests read (installing, plugin, scanners, experimental reviewer) moved | the tests follow the sections to `docs/guides/reference.md`; no assertion was weakened |
| Q-K4-195 | "Moved unchanged in substance" versus the command table lacking four commands | the rows are added, because the guide links the reference as the full list and a missing row would be a false statement |
| Q-K4-196 | The brief names a "10-minute path"; no one has timed it | the section keeps the brief's name and says in its first sentence that the time is not measured `(verify)` |

## Evidence recorded on 2026-10-19

- K3 criterion d (ADR-0015) is met by the scheduled metrics run of 2026-10-19: issue #86, no manual trigger. The first scheduled product report is issue #88.
- The metrics issues of this repository (#86) and of the fork ran about 7 hours after their slot, the report (#88) about 7.5 hours. The guide and the README say to expect the Monday
  issues hours late. The fork's scheduled metrics run (run 2, Scheduled) shows that scheduled runs work on a fork once Actions are on; the guide's earlier statement that a fork
  does not run scheduled workflows was wrong and is corrected.
- The At risk section of #88 flagged #79, #45 and #50 as merged before their last commit was cleared. That is correct and the rule stands: merge only after the latest head is cleared.

## Residual

- 2026-10-19: the fix-list verdicts on the pull requests numbered 76 to 84 were not posted as comments (they were given in the conversation), so the metrics field `review_rounds`
  and the report's fix counts for those pull requests are understated. Note it in the K4 close record; the comments are not back-filled. (due 2026-11-30)
- 2026-10-19: the example id in SPEC-0012 rule 10 (`Q-S0014-1`) collides with a real spec's question. Use a number no spec has when the spec is next amended. (due 2026-12-31)
- 2026-10-19: `playbook.py check-start` names the three items when one has no list under it; its message should name the item that lacks a list. (due 2026-11-15)
- 2026-10-19: no one outside the project has followed the guide; the first outside developer's "I got stuck" issues are the findings (about 2026-11-02, then the weekly review). (due 2026-11-20)
- 2026-10-19: the two steps marked "not yet proven live" (applying the ruleset; the architect session) wait for the maintainers' sandbox proof and the first live architect run. (due 2026-11-20)
