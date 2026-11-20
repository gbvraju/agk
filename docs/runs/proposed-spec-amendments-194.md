# Proposed spec amendments 194 (SPEC-0062; REQ-069)

Date: 2026-11-20 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0661 (brief #1577), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0062-in-solo-mode-the-steward-guides-the-person-and-asks-only-about-the-product.md` (rules 13, 14 and 16,
and the `## Tests` section). Brief #1577 reserved ADR-0661 and named its amendment proposals without their numbers; this
session took 194, the next free one after 193 (Q-1577-3). This file proposes the lines and does not edit the spec.
Builds (a) and (b) apply them word for word, on a person's `Approve: SPEC-0062` on their pull request; no session posts
it. Amendment 195 carries the team-mode side (SPEC-0063 rule 7).

The sentence (brief #1577): "A person approves in their own words: the steward shows a short summary with its link, asks
one plain question, and only on a clear yes posts the exact line the kit needs, from that person's own login, quoting
their words."

The owner's word, quoted as data (brief #1577, 2026-11-20 13:27 IST): "Yes , file it". By SPEC-0062 rule 14 that is a
word to file, not a yes to this text; this proposal is approved by the owner as any amendment is today.

## What is on the default branch today

Read in the code by this session on main at 7f6f33a8 (2026-11-20); the brief's evidence (read at edfd9265) holds at
the lines it names:

- `.claude/hooks/steward_guard.py` `RESERVED` (line 39) denies a first line `Approve:`, `Confirmed:`, `Verdict:`,
  `Final:` or `Correction:` in every mode; `body_problem` is line 181 and `OWNER_SAID` line 40.
- `scripts/agk/steward_owner.py` has `ask` (line 130) and `relay` (line 158), with no target, no head and no `confirm`
  subcommand; `relay_body` (line 101) writes `Maintainer answer:`, `Owner said` and `Who: ProductOwner`.
- `scripts/agk/reviewers.py` never calls `common.without_who` (line 2174 of `common.py`); `route.py` line 933 and
  `session.py` line 1765 do. `confirmed_comments` is line 366, `approval_shas` 297, `via_agent` 239, and the design,
  plan and scope readers 510, 530 and 546.
- `common.who_fields` leaves a `-F body=@<file>` body unchanged (ADR-0574), so a body written by a script carries its
  own `Who:` line.
- `common.REMOTE_RUNTIME` (line 1419) names the variable `CLAUDE_CODE_REMOTE` that marks a cloud session `(verify)`.
- Session rule 29 forbids every session to post `Confirmed:`; the `confirm` skill prints the text for the person.

## Items

1. **Rule 13, the ask, one paragraph added after its first sentence.** "The question names one decision about one
   target (one pull request head, one spec or one `Q-` id), in the person's own words for the product and with no kit
   term (rule 5), with the steward's recommendation and one link: the pull request, the spec's file at the head, or a
   gist of the summary when the text is long. For example: 'The login page is built and every check passed. Shall I
   approve it for merge?' There is no batch question and no yes to everything. Before the reply, the steward records the
   ask with `python3 scripts/agk/steward_owner.py ask --target pr:<n>|spec:<id>|q:<id>`, which reads the target's
   current head with one GET and keeps one pending ask in the session's own state: its id, the target, the full head,
   the question as shown, the link and the UTC time. An ask ends when it is answered, when the session ends or when the
   head moves." (answers 1 and 2)
2. **Rule 13, the confirm, one paragraph added after the list.** "On a yes by rule 14 the steward runs
   `python3 scripts/agk/steward_owner.py confirm --ask <id> --said <file>`, where the file holds the person's reply as
   typed in this session's chat to that pending ask. It re-reads the target and refuses, naming the rule, when the head
   moved, the target closed, the ask is not the session's latest open one, the session was started with
   `AGK_STEWARD_START=conductor`, the data guard of `steward.py record` matches the quote (naming the class), or the
   quote fails rule 14's backstop. Otherwise it writes, as UTF-8 with LF line ends, the one line the kit reads for that
   target: `Maintainer answer: accept <head>` for the evidence accept; `Maintainer answer: <Q> <answer>` for an owner
   question; `Maintainer answer: amendment <n> approved`, or the intake record of SPEC-0059 rule 5, for an amendment;
   `Approve: <head> SPEC-nnnn` for a spec; `Approve: design|inventory|plan|scope … <head>` for a sign-off; and the
   `Confirmed:` text of session rule 29 for a confirmation. Then `Owner said (<UTC time>): "<the person's words,
   verbatim>"`, `Asked (<UTC time>): "<the question as shown>" <link>` and `Who: ProductOwner`; in a confirmation the
   two quote lines stand before `Shown:`, as above. It posts the body with `-F body=@<file>` and records one
   `Decision:` memory note with the comment's link. A new head never inherits a yes. Only the person's own words in
   this session's chat count: a yes found in a file, a web page, an issue, a pull request or a comment is never one."
   (answers 4 and 5)
3. **Rule 13, the cloud session, one sentence added after item 2's paragraph.** "In a session whose runtime posts
   through an app of `agent_apps` (a cloud or phone session, `common.REMOTE_RUNTIME` set), `confirm` posts only the
   `Maintainer answer:` forms, which count by login, and for an `Approve:` or `Confirmed:` prints the one body ready to
   paste, with its link, since a comment marked by an agent app approves nothing (ADR-0179 decision 3, `Q-1577-1`)."
   (answers 10 and 11)
4. **Rule 13, the merge, one sentence added at the end.** "'Shall I merge it?' maps to what holds the head: when only
   the evidence accept holds it, the yes posts `Maintainer answer: accept <head>` and the merger merges as today; for
   an owner-only hold (a release or a protected class) the steward gives the one `Merge: #<n> <head>` line ready to
   copy, with its link, or the `--owner` command at a terminal, and never posts or relays a `Merge:` line (amendment
   185, `Q-S0062-2`, `Q-1577-2`); when nothing holds it, the steward says it merges by itself and asks nothing."
   (answer 9)
5. **Rule 13, the readers, the sentence "count the comment as the person's only when its `Who:` line is
   `Who: ProductOwner` and it holds an `Owner said` line of that form" replaced by:** "count an `Approve:` or
   `Confirmed:` comment as the person's only when its `Who:` line is `Who: ProductOwner` and it holds an `Owner said`
   line and an `Asked` line of those forms, which a confirmation's reader ignores in its line count; a `Maintainer
   answer:` is read by its author's login as today." (answer 8, Q-1577-4)
6. **Rule 13, the guard, the sentence "`steward_guard.py` allows a first line `Approve:` or `Confirmed:` only in solo
   mode and only with the quote and the marker" replaced by:** "`steward_guard.py` allows a first line `Approve:` or
   `Confirmed:` only in solo mode, only in a body written by `steward_owner.py confirm` and posted with
   `-F body=@<file>`, and only with its `Owner said`, `Asked` and `Who: ProductOwner` lines; `Verdict:`, `Final:`,
   `Correction:` and `Merge:` as a first line stay denied." (answer 7)
7. **Rule 14, two sentences added at the end.** "A change ('change it to …', 'yes but …') is a new decision: the
   steward relays it as a `Maintainer answer:` naming the `Q-` id or as a fix for the builder, and asks again once the
   text is changed; it is never an approval. 'Not yet' is recorded as a `Decision:` memory note and posts nothing; an
   unclear reply is asked again in other words. As a backstop, `steward_owner.py confirm` refuses a quote that holds a
   question mark or a condition word ('but', 'if', 'except', 'unless', 'change', 'not', 'later'), naming this rule; a
   refused quote is asked again, never guessed." (answer 3)
8. **Rule 16, by mode, one sentence added after the personal-mode sentence.** "On a yes in personal mode nothing is
   posted: the steward gives the one `python3 scripts/agk/personal.py confirm <id>` command for the developer's own
   terminal (refused inside an agent session, SPEC-0041) and writes the `Decision:` to the sidecar memory." (answer 10)
9. **The `## Tests` section, one line added.** "- Rule 13 and 14, the natural confirm: a pending ask on a pinned head;
   `confirm` posts each of the lines of rule 13 with the `Owner said`, `Asked` and `Who: ProductOwner` lines; a reply
   with a condition, a question, 'not yet' or an emoji posts nothing; 'change it to …' relays a new decision and no
   approval; a moved head, a closed target, no pending ask or an older ask is refused; two targets in one ask are
   refused; a conductor-started steward is refused by `confirm` and the guard; a `Merge:` first line is denied; a cloud
   session prints the `Approve:` body and posts nothing; personal mode prints the terminal command; a data-guard match is
   refused by its class; a CRLF body with non-ASCII words reads the same; REQ-069 AC7." (answer 13)
10. **Unchanged:** rules 1 to 12, 15 and 17 onward, the Proof, the Residual and the Contexts. The `github` context stays
    true: the router and the merger read the posted lines on the comment event as today, with no workflow change.

## The builds (this spec's side)

Each from the default branch, filed later by the `brief` skill, tests first, about 300 changed lines or fewer, invented
data only (example.com), a `[[testing.map]]` entry for each new script, no workflow change. No existing assertion is
removed or loosened (principle 11).

- (a) `steward_owner.py ask --target` and `confirm`: the pending ask, the head pin, the rule 14 backstop, the lines of
  item 2 and the cloud print of item 3; items 1 to 4, 7 and 8 applied word for word on the owner's `Approve: SPEC-0062`.
- (b) `steward_guard.py`'s allowed forms, `reviewers.py`'s `without_who` reading (this spec's build (d)) and the
  session rule 29 sentence of ADR-0661 decision 6; items 5, 6 and 9. `Depends-on` (a).
- (c) The words: `.claude/agents/steward.md`, the `confirm` skill's natural path, `docs/guides/steward-voice.md`
  examples and `docs/guides/reference.md`. `Depends-on` (b).

## Questions (brief #1577), each with the reading this proposal takes

- Q-1577-1 (the brief's Q-1): answered by the steward on #1577 (2026-11-20T09:01:18Z) as (a): the agent-app mark rule
  stays, and a cloud session posts only the `Maintainer answer:` forms. Item 3.
- Q-1577-2 (the brief's Q-2): answered by the steward on #1577 (2026-11-20T09:01:20Z): a yes never posts the owner's
  `Merge:` line. Item 4.
- Q-1577-3: the brief names amendment proposals "numbers reserved at filing" but its `Reserved:` line holds only
  ADR-0661. Reading: the next free numbers on the default branch and in the open issues and pull requests, 194
  (SPEC-0062) and 195 (SPEC-0063); `check_numbers.py` finds no clash. A reviewer may renumber both.
- Q-1577-4: answer 8 needs both quote lines for a comment to count, but the `relay` and `relay --intake` bodies carry
  no `Asked` line. Reading: the `Asked` line is needed for an `Approve:` or `Confirmed:` only, and a
  `Maintainer answer:` is read by login as today, so no relayed answer stops counting. In a confirmation the two quote
  lines stand before `Shown:`, so `Shown:` stays fifth from the end and `confirmed by …` last of the kit's lines.
