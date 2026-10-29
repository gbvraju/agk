---
name: review-pass
description: The conductor's one review pass. Reviews exactly the pull requests that session.py review-queue lists, posts at most one verdict per head, and ends with one line per pull request. Safe to run again and again, by hand or from a timed loop.
disable-model-invocation: true
---

# /agk:review-pass

`/agk:review-pass` is the conductor's own prompt for one pass over the queue. Run it in a conductor session
(`claude --agent conductor`, whose guard bounds what it can do), by hand or from the loop of `docs/guides/getting-started.md`.
A pass is safe to run again and again: it reviews only the pull requests that need a verdict, never twice on one head, and a
pass with nothing to do posts nothing. It never merges, never pushes and edits no file of the repository.

## The rules of a pass

A pull request needs a verdict when one of these holds, and the pass reviews no other:

- it is labelled `agk:review`;
- a `Question:`, `Report:`, `Correction:` or `Maintainer answer:` comment was created or **edited** after the last verdict;
- its head differs from the head the last verdict names, or it has no verdict yet;
- its checks are green while the router's label is still a stale `agk:ci-running`.

And never:

- **at most one verdict per head**: a verdict by a listed author that names the head, with none of those comments after it, means
  the pull request is skipped, whatever its label says;
- a draft, or a pull request whose checks are still running, is skipped; the loop wakes again when that changes.

`python3 scripts/agk/session.py review-queue` applies exactly these rules, read-only, and prints one line per pull request that
qualifies, `#<n> <head7> review: <why>`, or `empty`; with `--all` it also prints `#<n> <head7> skip: <why>` for the others.

## The pass

1. **The queue.** Use the output of `python3 scripts/agk/session.py review-queue --all`. The loop runs it before it starts the
   pass and gives it to you after the command; use exactly that. In a session started by hand, the person runs it and pastes the
   output, because the conductor's guard runs no script outside the bounded run `(verify: Q-306-1 asks whether the guard should
   allow this one read-only command)`. Without the output, read the same facts with `gh api` GET (the open pull requests, the
   comments of each, the check runs of each head) and apply the rules above yourself. When the queue is `empty` and has no skip
   lines, post nothing and end with the one line `queue empty`.
2. **Order.** Review the `review` lines in `Depends-on` order: a pull request after the ones it names.
3. **Review each one** by the conductor's protocol and its pre-verdict steps (`.claude/agents/conductor.md`): CI first,
   mergeable, the reviewed sha is the head, real paths only, a cause only from a run. Answer every `Question:`, `Report:`,
   `Correction:` and `Maintainer answer:` that the reason names in the verdict itself.
4. **Check again just before posting.** Read the pull request (`gh api repos/<owner>/<repo>/pulls/<n>`, a GET) and its newest
   comments. When the head is no longer the head you reviewed, or a verdict by a listed author that names this head was posted
   after the comment that made it qualify (another pass, or another conductor), post nothing and say so in the last lines. This
   keeps two passes, or two conductors, from posting two verdicts on one head.
5. **Post the verdict.** Write it with `Write` into a file in a scratch directory named `agk-conductor-<name>` directly in the
   system temp directory, and post it with exactly
   `gh api --method POST repos/<owner>/<repo>/issues/<n>/comments -F body=@<that file>`: no `--jq`, no other flag. On Windows
   write the path with forward slashes and a drive letter, for example
   `C:/Users/<user>/AppData/Local/Temp/agk-conductor-<n>/verdict.md`: in Git Bash an unquoted backslash path loses its
   backslashes before the guard reads it, and `/tmp` there is not the temp directory that Python reports, so the guard refuses
   both. When the guard refuses a correct verdict, quote its message in the last lines; never retry with another spelling of the
   command.
6. **A decision that belongs to a person.** When a pull request waits for something only a person gives (an `Approve:` of a
   spec, an ADR's decision, a question the rules do not answer, a merge), say it in one line
   `NEEDS-YOU: #<n> <what the person decides>`. Never write `Approve:` yourself and never merge.
7. **The last lines.** End the pass with one line per pull request of the queue, review and skip lines alike:
   `#<n> <head7> <action>`, where the action is `verdict cleared (comment <id>)`, `verdict fix list (comment <id>)`,
   `verdict rejected (comment <id>)`, `skip: <why>` or `nothing posted: <why>`; then the `NEEDS-YOU:` lines, if any. Nothing
   else follows.

A pass keeps no state of its own: GitHub holds it (the heads, the labels, the comments), so the next pass reads it again.
