---
name: confirm
description: Solo mode only. After the person says yes in a session, print the one confirmation comment for the pull request's head (the verdict, its Final lines and the spec approval together) for the person to post themselves. Never posts it.
disable-model-invocation: true
argument-hint: "<pull request number>"
---

# /agk:confirm

`/agk:confirm <n>` is for a project in solo mode (`review_mode = "solo"` in `agk.toml`, with one person listed in
`config/reviewers.yaml`), where one comment by that person counts as the verdict, its `Final:` lines and the spec approval of
the head it names (brief 277, ADR-0179). The session prepares that comment; **the person posts it, never the session**
(session rule 29): GitHub cannot tell a comment the person typed from one a session posted under the same account, so a
session that posted it would give the one yes itself. The conductor's guard refuses such a comment by name.

## Steps

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

Merging stays the person's. This command writes no file and posts nothing.
