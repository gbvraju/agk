# ADR-0537: Pull request bodies and verdicts open with a plain summary

- Status: Proposed
- Date: 2026-11-14
- Deciders: maintainers
- Related: brief #1270, plan #661
- Requirements: REQ-050

## Context

The owner said (2026-11-14, quoted in brief #1270) that pull request bodies carry too much machine-readable text and
should open with a summary a developer can read, to cut the tokens every session spends re-reading them. In the last
20 merged pull requests of the kit a body averaged about 4,600 characters and the comments about 6,000, mostly
verdicts that walk every file read; each is re-read on every conductor pass and builder poll. The governance job,
prepush and the conductor parse the body's fields and the verdict's lines, so those must not change.

## Decision

1. `.github/PULL_REQUEST_TEMPLATE.md` opens with `Summary:` (one sentence of at most 120 characters, as before) and at
   most three plain lines under it: what changed, why, how to try it. The checked fields follow, one line each or one
   line per item, with no prose under them; `Verified:` lists commands and verbatim counts only. No field is removed,
   renamed or made optional.
2. `scripts/agk/pr_body.py` prints one information line after a printed body that passes 1,500 characters outside its
   `Verified:` lines: `pr body: <n> characters; the summary-first form keeps it under 1,500`. The exit, the body and
   the body check are unchanged.
3. `.claude/agents/conductor.md` and `skills/review-pass/SKILL.md` name the short verdict form: only the failing and
   not-proven items, one line each, and one line `Passed: <n> rules` for the rest; `Read: <n> files` instead of each
   file; a re-review names only what changed since the last verdict on that pull request. The review protocol block
   (the architect's, kept verbatim) is unchanged; the form only shortens how its steps 2 and 3 are written. Every line
   `merge_cleared.py` and `route.py` parse (`Verdict:`, `Final:`, `Local evidence:`, `Evidence check:`, `Checklist:`,
   `Playbook evidence:`, `Approval:`) keeps its name and form, and the verdict's section labels (`Read:`, `Rules:`,
   `Not proven:`, `Lens:`, `Gaps:`, `Checklist:`) stay, as `shadow_count.py` reads them.
   The role file stays within its rule budget (`config/rule-budget.txt`, unchanged): two sentences it repeated from the
   skill (the `Depends-on` order and the timed loop's guide) are cut and one is shortened.

## Consequences

Bodies and verdicts get shorter for people and for every session that re-reads them; nothing parsed changes. In CI
mode the governance job reads the same fields; in local mode prepush and the conductor do; in personal mode there are
no pull requests and nothing changes. No workflow and no stack's test or build step changes. Tests:
`tests/kit_dev/test_pr_body_size_note.py` (the note over the limit, none under it, `Verified:` not counted) and
`tests/kit/test_short_bodies_and_verdicts.py` (the template's order and one-line fields; the agent and the skill name
the short form and every parsed line); `tests/kit/test_pr_summary.py` now asserts the summary-first order. Protected
path classes changed: `.github/` (`.github/PULL_REQUEST_TEMPLATE.md`), `.claude/` (`.claude/agents/conductor.md`),
`skills/` (`skills/review-pass/SKILL.md`), `scripts/agk/` (`scripts/agk/pr_body.py`), `tests/kit/` and
`tests/kit_dev/` (the test files above).

## Residual

- 2026-11-14: a body a builder writes by hand passes through `prepush.py --body` and `check_pr_body.py`, which print
  no size note; brief #1270 names only `pr_body.py`, the printer of the kit commands' bodies.
