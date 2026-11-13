# ADR-0510: The runtime task texts match the running autopilot

- Status: Proposed
- Date: 2026-11-13
- Deciders: maintainers
- Related: ADR-0477, ADR-0489, SPEC-0045, brief #1117, brief #1151, brief #1179, brief #1202, plan #661
- Requirements: REQ-039

## Context

ADR-0477 shipped the round-the-clock task texts under `kit/templates/runtime/` with a `<long-run rules>` placeholder in
`conductor.txt`, whose last paragraph forbade every scheduled-task action, so a project's conductor set up from it starts
no builder. The texts that run this repository have since moved on: the conductor starts builders itself by kind on every
`START` line of its watch (briefs #1151 and #1179) and after every merge and verdict, restarts handed-over and silent
builders, reviews held verdicts again on an answer and posts owner asks on the pull request; the launcher is its backup,
at 45 minutes of silence rather than 90; and the builders carry the CI-red, answer, hand-over, `Finishes:` and
`[[testing.map]]` rules (brief #1202).

## Decision

1. `conductor.txt` replaces `<long-run rules>` with numbered steps 8 to 13: starts by kind (`<mid builder task>` for
   `kind: small`, `<strongest builder task>` otherwise) with the standard message and a `Started: cb` line, never for a
   brief started or taken in the last 2 hours and never past the plan's `Capacity:`; restarts of handed-over pull
   requests and of ones silent 45 minutes under a build, fix, CI-red or conflict label; held verdicts reviewed again on
   an answer or approval; `Owner needed:` asks on the pull request with a pointer on `<plan issue>`, never a fix list;
   reserved numbers checked free when splitting a brief; and the merge left to the merger job (`merger.yml` with `pr`).
   Step 6 names the watch's current ends, `START` lines among them. The last paragraph allows firing the two builder
   tasks and no other scheduled-task action.
2. `launcher.txt` and `builder.txt` take the running texts with placeholders only. The builder's kit-only rules (the
   `ALWAYS ALSO` tests, `changelog.d`, `kit_hashes.py`, the release exception) sit under one line
   `Kit repository only (where kit/agk-kit.mk exists):`; every project lists a new test file in its own
   `[[testing.map]]` entry.
3. The folder's README and the guide's "Running around the clock" say in one sentence that the conductor starts
   builders itself and the launcher is its backup. The kit still installs and starts none of the texts (ADR-0477).

## Consequences

A project set up from the templates gets the same autopilot as this repository. `tests/kit/test_runtime_templates.py`
checks the replaced placeholder, the start rules and limits, the conductor's one scheduled-task permission, the
launcher's 45 minutes and the builder's rules by their first words. Protected path classes changed: `kit/` (the
templates) and `tests/kit/` (their test). No workflow, script or installed file changes, and `kit/hashes.json` does not
change: the templates are not hashed.

## Residual

- 2026-11-13: the texts remain copies of the rules of `config/session-rules.md`, the role files and the running tasks;
  nothing checks that a later change reaches them beyond the first-words tests (due 2026-12-31).
- 2026-11-13: step 13 leaves the merge to the merger job while `.claude/agents/conductor.md` still describes the
  guarded `merge_cleared.py` merge; the maintainers may align the role file (due 2026-11-30).
