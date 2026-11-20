# ADR-0661: A person approves in their own words, and the steward posts the exact line on a clear yes (REQ-069, REQ-070)

- Status: Proposed
- Date: 2026-11-20
- Deciders: maintainers
- Related: SPEC-0062, SPEC-0063, SPEC-0059, SPEC-0041, amendment 194, amendment 195, amendment 185, amendment 193, brief #1577, brief #1573, brief #1381, ADR-0179, ADR-0546, ADR-0574, ADR-0660, plan #661
- Requirements: REQ-069, REQ-070

Protected classes the builds of this decision change: `scripts/agk/`, `.claude/`, `skills/`, `tests/kit/` and
`config/` (session rule 29, by build (b)). This pull request changes none of them.

## Context

The lines a person types today are strict forms read by first line and login: `Maintainer answer: accept <head>`
(`merge_cleared.answered`, line 798), `Maintainer answer: amendment <n> approved`, `Approve: [<sha>] SPEC-nnnn`
(`reviewers.approval_shas`, line 297), `Approve: design|inventory|plan|scope … <head>` (lines 510, 530, 546), the solo
`Confirmed:` comment of at least seven exact lines (`reviewers.confirmed_comments`, line 366) and the owner's
`Merge: #<n> <head>` (amendment 185). A business user finds them hard to type; the owner asked for one natural question
with a link and, on a clear yes, the exact line posted from that person's own login (brief #1577, quoted there as data).

SPEC-0062 rule 13 and SPEC-0063 rule 7 (both Approved) already allow the steward to post an approval on a plain yes,
but neither is built: `steward_guard.py` `RESERVED` (line 39) denies `Approve:` and `Confirmed:` in every mode,
`reviewers.py` never drops the `Who:` line (`common.without_who`), and session rule 29 forbids every session to post
`Confirmed:`. A comment GitHub marks as posted through an app of `agent_apps` is never an approval (`reviewers.via_agent`,
line 239; ADR-0179 decision 3), while `route.asks_owner` (line 502) and `merge_cleared.answered` read a
`Maintainer answer:` by login only. `common.who_fields` leaves a `-F body=@<file>` body unchanged (ADR-0574).

## Decision

1. SPEC-0062 changes only through amendment 194 and SPEC-0063 only through amendment 195, which this intake writes
   and does not apply; each build applies its items word for word on the owner's `Approve:` of that spec.
2. **One natural question.** The steward shows what is decided in three lines or fewer with one link, asks one
   question in the person's words with its recommendation, and covers one decision about one target per question;
   there is no batch form. The ask is recorded before the reply by `steward_owner.py ask --target`, which pins the
   target's full head (amendment 194 item 1).
3. **The reply.** An explicit yes by SPEC-0062 rule 14 alone posts. A change is a new decision, relayed and asked
   again, never an approval; anything else posts nothing. `confirm` refuses a quote with a question mark or a
   condition word as a backstop (amendment 194 item 7).
4. **The exact line.** `steward_owner.py confirm --ask <id> --said <file>` re-reads the target, refuses a moved head, a
   closed target, a stale ask, a conductor-started steward and a data-guard match, and writes the one line the kit reads
   with `Owner said`, `Asked` and `Who:` lines, posted with `-F body=@<file>`, and records a `Decision:` (amendment 194
   item 2). Only the person's own chat words to the pending ask count.
5. **Who, by mode.** Solo: `Who: ProductOwner`. Team: `Who: <the kept login>`, only for that login and only a line that
   login may give (`spec_approvers`); `Confirmed:` stays denied in team mode (`Q-S0063-6`); each role runs its own
   steward on its own login (amendment 195).
6. **Session rule 29**, by build (b), gains one sentence after its first: "The one exception: in solo mode the steward
   posts that text when `steward_owner.py confirm` wrote it on the person's recorded plain yes (SPEC-0062 rules 13 and
   14), with the `Owner said`, `Asked` and `Who: ProductOwner` lines; every other session, and every session in team
   mode, still never posts it." The core-rules summary of rule 29 gains "(the solo steward's recorded yes aside)".
   `CLAUDE.md` item 2 speaks to the builder and stays.
7. **The guard and the readers** (amendment 194 items 5 and 6, amendment 195 items 2 and 3). The guard allows
   `Approve:` and, in solo mode, `Confirmed:` only in a body written by `confirm` with its three closing lines;
   `Verdict:`, `Final:`, `Correction:` and `Merge:` stay denied. The readers drop the `Who:` line and the footer and
   count an `Approve:` or `Confirmed:` with a `Who:` line only when it names the author's role and holds both quote
   lines; a comment with no `Who:` line counts as today, and any `Who: AGK…` approves nothing.
8. **The agent mark stays** (`Q-1577-1`, answered as (a)): an app-marked `Approve:` or `Confirmed:` approves nothing.
   In a cloud or phone session `confirm` posts only the `Maintainer answer:` forms and prints an approval body ready to
   paste (amendment 194 item 3).
9. **No merge on a yes** (`Q-1577-2`, `Q-S0062-2`, amendment 185): the steward never posts or relays `Merge:`. A yes
   posts the evidence accept when that is the only hold; an owner-only hold gets the line to copy; with no hold the
   steward says it merges by itself.
10. **Personal mode** (`forge = "files"`): nothing is posted; the steward prints the one `personal.py confirm <id>`
    command and writes the `Decision:` to the sidecar memory (amendment 194 item 8).
11. No workflow, ruleset, required check, `agent_apps`, `spec_approvers` or `teams` change. Builds (a) to (c) follow by
    the `brief` skill, each from the default branch, tests first.

## Consequences

- A person approves by answering one plain question; the kit's strict lines are written by the script, with the
  person's words, the question and its link as the trail.
- One login still cannot prove who typed the yes (SPEC-0062 rule 13 accepts that); the quote and its time are the
  record, and the agent mark keeps a cloud session's approval from counting.
- Every reader of approvals changes once, by build (b), with SPEC-0062's build (d) and SPEC-0063's build (c).

## Residual

- (due 2026-12-20) After build (b) merges, count the approvals posted by `confirm` and the refusals by kind; propose a
  change to the backstop words only from that count.
