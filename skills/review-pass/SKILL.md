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
- its checks are green while the router's label is still a stale `agk:ci-running`;
- it is a draft with a `Question:` comment created or **edited** after the last verdict (reason `question on a draft`):
  the builder waits on the answer, which needs no checks.

And never:

- **at most one verdict per head**: a verdict by a listed author that names the head, with none of those comments after it, means
  the pull request is skipped, whatever its label says;
- any other draft, or a pull request whose checks are still running (a required run queued or in progress, or a required status
  pending), is skipped whatever its label; the loop wakes again when that changes. Required checks that have not reported at
  all skip it under `agk:ci-running`; under any other label it is reviewed with the reason `checks not reported` (a project
  whose workflows are off), and the verdict clears nothing while CI is missing.

`python3 scripts/agk/session.py review-queue` applies exactly these rules, read-only, and prints one line per pull request that
qualifies, `#<n> <head7> review: <why>`, or `empty`; with `--all` it also prints `#<n> <head7> skip: <why>` for the others.

## The pass

1. **The queue.** Use the output of `python3 scripts/agk/session.py review-queue --all`. The loop runs it before it starts the
   pass and gives it to you after the command; use exactly that. In a session started by hand, the person runs it and pastes the
   output, because the conductor's guard runs no script outside the bounded run `(verify: Q-306-1 asks whether the guard should
   allow this one read-only command)`. Without the output, read the same facts with `gh api` GET (the open pull requests, the
   comments of each, the check runs of each head) and apply the rules above yourself. When the queue is `empty` and has no skip
   lines, post nothing, run the re-plan of step 7 and end with the line `queue empty` followed by its `Start` and `waits for`
   lines: a merge that empties the queue is when briefs unblock.
2. **Order.** Review the `review` lines in `Depends-on` order: a pull request after the ones it names.
3. **Review each one** by the conductor's protocol and its pre-verdict steps (`.claude/agents/conductor.md`): CI first,
   mergeable, the reviewed sha is the head, real paths only, a cause only from a run. Answer every `Question:`, `Report:`,
   `Correction:` and `Maintainer answer:` that the reason names in the verdict itself. For a `question on a draft`, answer
   the question in a verdict on the draft's head whose numbered items are the answers, and do not review the draft's code:
   it is not finished, and its checks may still be running.
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
7. **Re-plan.** After the verdicts, and also after a pass that posted nothing, run
   `python3 scripts/agk/session.py plan --json` (brief 331, ADR-0190). It reads GitHub and posts nothing; the pass posts
   nothing new either. From its output write, for the last lines, one line `Start <n>: <session> takes #<brief>, ...` (with
   `build (<x>)` after a brief built in parts), or `Start 0: <why>`, and one line `#<brief> waits for <what> (<why>)` for each
   of its waits, in the plan's own words. Then read the `[flow]` table of `agk.toml` for the two settings `auto_start` and
   `launch_adapter`:
   - **`auto_start` off** (the default, or `launch_adapter` unset) and the plan starts sessions: write the plan exactly as
     printed with `Write` into `plan.json` in your scratch directory and run
     `python3 scripts/agk/launch.py prompts --plan <the scratch file>`. Print its ready-to-paste prompts after the last lines, as
     `/agk:launch` does, for the person to start; nothing starts.
   - **`auto_start = true` and `launch_adapter` set**, in your checkout and on the default branch alike (run `git fetch origin`
     first: the guard reads both, and turning the setting off on the default branch stops the starts), and the plan starts
     sessions: write the plan the same way and run exactly
     `python3 scripts/agk/launch.py prompts --plan <the scratch file> --adapter <launch_adapter>`, with the adapter as written in
     `agk.toml`, quoted as one word. The guard allows that one command and no other adapter. Add each `started <session>
     #<brief>` line it prints to the last lines.
   The plan decides who starts: never more than the plan's capacity (`launch.py` refuses a plan whose start list is longer than
   its slots, and with an adapter a plan without its `capacity`, and starts no more than `[flow] max_builders`, printing
   `not started:` for the rest), never for a brief that is taken (the plan leaves those out), and never a session the plan does not name. Each
   started session takes its brief with its own `session.py claim`; that `taken:` claim, made by the started session itself,
   never by the conductor, is the record of the start, so post no `taken:` and run no `claim`. A refused adapter is reported,
   not retried: quote its `FAIL launch:` and `not started:` lines and add `NEEDS-YOU: the adapter refused <session>`; do not run
   the command again in this pass. When the plan starts nothing, run no `launch.py` at all.
8. **The last lines.** End the pass with one line per pull request of the queue, review and skip lines alike:
   `#<n> <head7> <action>`, where the action is `verdict cleared (comment <id>)`, `verdict fix list (comment <id>)`,
   `verdict rejected (comment <id>)`, `skip: <why>` or `nothing posted: <why>`; then the `Start` and `waits for` lines of the
   re-plan and any `started` lines; then the `NEEDS-YOU:` lines, if any. Nothing else follows, except the ready-to-paste
   prompts of a re-plan with `auto_start` off.

A pass keeps no state of its own: GitHub holds it (the heads, the labels, the comments), so the next pass reads it again.
