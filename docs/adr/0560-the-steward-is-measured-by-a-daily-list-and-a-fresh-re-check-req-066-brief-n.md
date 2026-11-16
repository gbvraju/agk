# ADR-0560: The steward is measured by a daily list, its override share and a fresh re-check

- Status: Accepted
- Date: 2026-11-15
- Deciders: maintainers
- Related: SPEC-0059, ADR-0557, ADR-0558, ADR-0430, brief #1323, brief #1321, brief #1320, plan #661
- Requirements: REQ-066

## Context

SPEC-0059 (Approved, #1280) rule 17 orders six builds of the steward. Builds (a) (brief #1320, ADR-0557) and (b) (brief
#1321, ADR-0558) added the memory, the evidence rule and the answer form, and (b) holds every requirement answer back
until a re-check exists. On the default branch nothing shows what the steward answered, what it filed on its own or how
often the owner overrode it (brief #1323's `Measured:` line). This ADR covers build (d): rule 13 and rule 3's override
warning.

## Decision

1. **The daily list.** `scripts/agk/steward_daily.py daily` runs after `steward.py start`, from that start's cache of the
   memory issue. When no `Daily: <today>` comment is there it posts one, covering each UTC day from the date of the last
   list (or yesterday when there is none) to yesterday, at most 14 (`Q-S0059-9`: no scheduler; the days missed are
   named). For each day it lists each steward `Answer:` (a comment whose first line is the answer form and whose body
   ends `Who: AGK steward`) with its comment id, its issue and its evidence; each pass's calls and tokens from its
   `Ended:` marker; each issue the steward filed with no `Owner said (` line, with its priority; and the owner questions
   asked (`Owner question:` notes) and answered (`Decision:` notes). It reads the repository's comments once with
   `since=` seven days before the first day, and the issues once with `since=`; a figure it cannot read is `unknown`,
   never 0. It says which reads it used (rule 18). In personal mode it prints the list and keeps it in the sidecar's
   memory file.
2. **The pass's figures.** `steward.py end` takes `--calls` and `--tokens` and writes `Ended: steward <session> calls
   <n>; tokens <n>`, `not shown` for a figure not given.
3. **The override share.** An owner's `Maintainer answer: Q-<id>` whose answer differs from the steward's earlier
   `Answer: Q-<id>`, or a `Correction:` that names that Q id, is an override. The steward's `Answer:` carries the
   question's class as its second line `Class: <class>`, so each new override is posted as one `Override: Q-<id> class
   <class>: ...` note before the list. The share of each day is that day's overrides over that day's steward answers.
4. **The warning.** Two `Override:` notes of one class within seven days put a `Warning: class <class> ...` line in the
   list, and `steward_evidence.py answer` sends a question of that class to the owner, reading the start's cache (no
   GitHub call), until a later `Decision:` note names `class <class>`. Nothing else stops.
5. **The re-check.** `steward_daily.py bundle --question FILE` prints the question and its cited places and rules only,
   never the steward's answer; the steward gives it to a fresh `reviewer` agent (ADR-0430's form) and passes that
   agent's answer to `steward_evidence.py answer --recheck FILE`. A requirement answer is posted only when the two agree
   (case, spacing and a final full stop aside); with no re-check, or a different answer, the question goes to the owner
   with both answers and no `Answer:` is posted. Build (b)'s hold on requirement answers ends here. No check calls a
   model: the reviewer is the agent's, and the tests give it as a stub.
6. **The agent file** names the two commands; its words go from 645 to 704 in `config/rule-budget.txt` (ADR-0310), and
   no rule line is added.

## Consequences

The owner sees each day what the steward did and how often its answers were changed, and a requirement answer needs a
second reader that never saw the steward's reasoning. Protected path classes changed: `.claude/` (`agents/steward.md`),
`scripts/agk/` (`steward_daily.py`, `steward_evidence.py`, `steward.py`), `config/` (`rule-budget.txt`), `agk.toml`
(the `[[testing.map]]` entries), `tests/kit/` (one new test file, one docstring) and `kit/` (`manifest.json`).

## Residual

- 2026-11-15: the share is per day; a share over all days, carried at the roll-over of rule 8, is not built (due
  2026-12-31).
- 2026-11-15: "fresh" and "the bundle only" rest on the agent file, as ADR-0430's residual says; no guard can tell
  what the reviewer read (due 2026-12-31).
