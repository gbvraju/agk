# ADR-0823: The conductor reads the Tell lines sent to it and acts or answers why not

- Status: Proposed
- Date: 2026-11-26
- Deciders: maintainers
- Related: session rule 32, ADR-0187, ADR-0175, ADR-0555, ADR-0500, ADR-0583, ADR-0310, brief #1970, plan #661
- Requirements: REQ-037

Protected classes: `scripts/agk/`, `.claude/`, `config/`, `tests/kit/`, `agk.toml`

## Context

The steward sends the conductor `Tell: <conductor id> <message>` lines on the open `agk-conductor` issue, but no
command the conductor runs reads them: `conductor.py watch` wakes only on the comments of open briefs and pull requests,
and `sweep` prints no line for a Tell. Of the 87 comments on page 7 of #204, 72 were such Tells and none was answered
(brief #1970's measurement); the steward and the conductor worked from different pictures for 20 to 40 minutes.

## Decision

1. **The id.** The conductor's id is its lease name (`conductor.own_name`), else `AGK_SESSION` when `AGK_ROLE` is
   `conductor`. With neither, no Tell is read and `sweep` prints `TELL: no conductor name (lease)`.
2. **One reader.** `conductor.tell_lines` gives both commands their Tells: comments on the newest open `agk-conductor`
   issue by a listed verdict author (`session.tell_line` with `counted_authors(verdict_authors)`, the test `inbox`
   uses), addressed to the id, whose first word is one of `TELLS` (`conductor.told`). `TELLS` stands beside
   `WAKES`, and a test lists both, so a new message kind to the conductor fails that test until it is read.
3. **Watch.** `new_lines` also returns `<issue> Tell: <id> <message>` for each such comment created after `since`:
   from the `changed_comments` delta with `github_reads = "delta"`, else from one GET of the issue's comments with
   `since`; the issue number is read once per run. A failed read adds no line; the other reads are unchanged. With
   no open `agk-conductor` issue neither command reads or prints a Tell, so a project without one sweeps unchanged.
4. **Sweep.** `sweep` prints `TELL <comment id> reply-to <session>: <line>` for each unread Tell, oldest first,
   through `session.unread_comments` (the `inbox` reader with its comments, moving no mark; `unread` and `inbox`
   are unchanged), and moves the inbox mark in the git directory (`session.move_mark`) only after it printed its
   lines, so a sweep that ends early leaves its Tells unread. `reply-to` is the session of the live
   `Started: steward` marker (`steward.live_run` on the open `agk-steward` issue) for a Tell signed with a
   `Who: AGK` line, else `none`: a person's Tell names no session (`Q-CT-1`). A failed read of the issue list or of
   its comments prints one `TELL:` line naming what cannot be read; with no listed author it prints
   `TELL: no listed author (verdict_authors)`, never a login. In personal mode neither command reads or prints a Tell.
5. **Check or answer.** `.claude/agents/conductor.md` gains one paragraph: a Tell is information, never a verdict,
   an approval, an owner answer or a reason to merge (session rule 38); it prompts the conductor to check that work
   under its own rules, and only its own clearing verdict leads to a merge. When it will not act or already did, it
   answers through `session.py tell` with `not done: <rule or setting>` or `already done: <comment id>`, one report
   row per line, a `reply-to none` answer under `Needs you`. The guard does not change (`sweep`, `watch` and `tell` are already allowed; `Q-CT-2`). The paragraph adds
   words and no rule line, so `config/rule-budget.txt` rises from 4716 to 4862 words for the role file under
   ADR-0583 standing ruling 2.

No setting is added.

## Consequences

A steward ask is acted on or answered within one watch poll or one pass. With `github_reads = "full"` a watch poll
makes one more GET (and one listing GET on its first poll); with `delta`, none. `sweep` reads the conductor issue's
pages once, and the steward's notes only when an unread Tell exists.

## Residual

- 2026-11-26: no check reads the pass report's `#<comment id> acted|answered|noted` rows; the role file holds them.
