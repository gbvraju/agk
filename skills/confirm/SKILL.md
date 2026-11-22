---
name: confirm
description: Solo mode only. The natural path first - the steward asks one plain question and, on the person's yes in the chat, posts the approval with steward_owner.py approve. Otherwise print the one confirmation comment for the pull request's head (the verdict, its Final lines and the spec approval together) for the person to post themselves.
disable-model-invocation: true
argument-hint: "<pull request number>"
---
<!--
SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
SPDX-License-Identifier: LicenseRef-AGK-Proprietary
AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
-->

# /agk:confirm

`/agk:confirm <n>` is for a project in solo mode (`review_mode = "solo"` in `agk.toml`, with one person listed in
`config/reviewers.yaml`), where one comment by that person counts as the verdict, its `Final:` lines and the spec approval of
the head it names (brief 277, ADR-0179).

## The natural path

Only with `review_mode = "solo"` and one person listed, and only for the steward (session rule 29, ADR-0704, brief #1692):

1. **One question.** The steward writes the exact line the kit reads (the verdict comment below, or an `Approve:` line)
   to a file and runs `python3 scripts/agk/steward_owner.py ask --target pr:<n> --qid <Q> --file <question> --line <line>`:
   it pins the full head and prints the question for the chat, with three lines or fewer and the link.
2. **The yes.** On the person's own plain yes, typed in the chat, the steward saves those words verbatim as one line and
   runs `python3 scripts/agk/steward_owner.py approve --ask <Q> --said <file> --at <UTC>`. It refuses a moved head, a
   closed pull request, a stale ask, a question or a condition; on a yes it posts the line with the person's words, the
   question and its link, and `Who: ProductOwner`.
3. **The read-back.** A post that GitHub marks with an app of `agent_apps` does not count: `approve` says so and prints the
   one body to paste, and so does a cloud session. In personal mode nothing is posted: it prints the `personal.py
   confirm` command, print only. In team mode it posts no approval.

The print path below stays as the fallback: for an app-marked session, and for a person who prefers to post it.

## The print path

Here the session prepares that comment; **the person posts it, never the session** (session rule 29): GitHub cannot tell
a comment the person typed from one a session posted under the same account, so a session that posted it would give the
one yes itself. The conductor's guard refuses such a comment by name.

1. **Read the head.** Read the pull request with `gh api repos/<owner>/<repo>/pulls/<n>` (a GET) and take `head.sha`, the full
   40-character ID. Read its checks; do not prepare a confirmation for a head whose checks are red or still running.
2. **Review it** by the conductor's protocol (`.claude/agents/conductor.md`) and write the verdict: `Verdict: cleared <head>`,
   `Verdict: fix list <head>` with numbered items, or the covered form with `Final: <path> <old> -> <new>` lines and no numbered
   item. For each spec the pull request sets `Approved`, add one line `Approve: SPEC-<n>`.
3. **Show the person three lines**: what changes, what it risks, and what stays as it is. Ask for a yes. Without a yes, stop.
4. **Print the comment** exactly, in this order, and nothing else:

   ```
   Confirmed: <the full head ID>
   Verdict: <kind> <the same full head ID>

   <findings, Final: lines and Approve: SPEC-<n> lines>

   Shown:
   <line 1 of the three lines>
   <line 2>
   <line 3>
   confirmed by <the person's login> in a session at <date -u +%Y-%m-%dT%H:%M:%SZ>
   ```

   Tell the person to post it as a comment on the pull request from the browser or the GitHub app, as it is. A comment posted
   through an agent's app, by another account, for another head, or of another shape counts for nothing.
5. **After the person posted it**, and only then, the session may make the `Final:` commit (status lines only, pushed alone), as
   for any covered fix list. Until the maintainers decide amendment 97 item 6, the person re-runs the red governance check, or the
   session pushes, so that governance reads the confirmation.

Merging stays the person's. The print path writes no file and posts nothing.
