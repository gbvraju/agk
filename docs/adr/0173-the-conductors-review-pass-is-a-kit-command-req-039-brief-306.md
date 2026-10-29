# ADR-0173: the conductor's review pass is a kit command that is safe to run again and again (REQ-039, brief 306)

- Status: Proposed
- Date: 2026-10-29
- Deciders: maintainers
- Related: ADR-0105, ADR-0170
- Requirements: REQ-039

Protected classes: `scripts/agk/`, `skills/`, `.claude/`, `tests/kit/`, `tests/kit_dev/`

## Context

Brief #306 (priority 1), from the pilot of #284 and its comments: the person hand-wrote a review-pass prompt and a PowerShell
loop around a headless conductor, and learned its rules the hard way: review only on `agk:review`, on a newer `Question:`,
`Report:`, `Correction:` or `Maintainer answer:` comment, on a head that differs from the last verdict's, or on green checks under
a stale `agk:ci-running` label; at most one verdict per head; forward-slash scratch paths on Windows; a `NEEDS-YOU:` line when a
decision belongs to a person; wake on edited comments. The tests of `review-queue` were written first
(`tests/kit/test_session_review.py`, 18 failed at the first checkpoint of the pull request, db59650).

## Decision

1. **`session.py review-queue`** (answer 2) prints, read-only (GET only), one line `#<n> <head7> review: <reason>; ...` for each
   open pull request that needs a verdict, or `empty`. The reasons are the four rules above. A comment counts from its edit time
   (`updated_at`) when it was edited. The last verdict is the latest one by a counted author (`verdict_authors`, without the pull
   request's own author when two or more are listed, as the router counts them). A verdict that names the head, with no trigger
   comment after it, skips the pull request whatever its label, so a stale `agk:review` never gets a second verdict. A draft is
   skipped without reading its comments; a pull request labelled `agk:ci-running` whose required checks still run, or have not
   reported, is skipped. Check states are the router's reading (`route.judged` over `required_checks`). `--all` adds a line
   `#<n> <head7> skip: <why>` for every other open pull request. An unreadable list, comment page or check list fails (exit 2);
   it never reads as `empty`. No listed verdict author fails naming the setting.
2. **`--fingerprint`** prints `fingerprint <sha256>` of each open pull request's number, head, `agk:` labels, draft flag, comment
   ids with their times (edits included) and the states of its required checks, so that a loop wakes only when the queue changes
   (answer 3).
3. **`/agk:review-pass`** (answer 1), `skills/review-pass/SKILL.md`, holds the rules and is the conductor's prompt for one pass:
   use the queue's output, review in `Depends-on` order by the conductor's protocol, read the pull request again just before
   posting and post nothing when the head moved or a verdict on it already came after the trigger, post with exactly one
   `-F body=@<file>` and no `--jq`, write Windows scratch paths with forward slashes, write `NEEDS-YOU: #<n> <what>` for a
   person's decision, and end with one line per pull request, `#<n> <head7> <action>`. It is a command a person or a loop runs
   (`disable-model-invocation: true`). `.claude/agents/conductor.md` names it.
4. **The guide** (answer 3) documents a loop for bash (Linux, macOS) and PowerShell (Windows) that runs from a clean detached
   worktree of the default branch, outside the work tree and outside the temp directory (so that it is never a conductor scratch
   directory), wakes on a changed fingerprint, starts `claude -p --agent conductor` only when `review-queue --all` is not
   `empty`, and reads the fingerprint again after the pass. Before it, the guard check: the guard script must deny a push, and a
   headless conductor must report the same push refused; otherwise the loop is not started.
5. **Reading Q-306-1 (taken, the conservative one).** The conductor's guard allows no script outside the bounded run, so a
   conductor session cannot run `review-queue` itself. The guard is not widened here (its file is not in the brief's `Touches:`):
   the loop runs `review-queue` outside the session and hands its output to the pass; by hand, the person runs it, or the
   conductor reads the same facts with `gh api` GET. Whether the guard should allow this one read-only command is a later decision.
6. **Reading Q-306-2 (taken).** A trigger comment after a verdict on the same head qualifies once: the conductor answers a
   `Question:` only by a verdict that names the head, and that verdict is then the newest, so the comment no longer counts. "At most
   one verdict per head" is read as one verdict per head and per trigger.
7. **Reading Q-306-3 (taken, the conservative one).** Checks still running skip a pull request even with a newer trigger comment;
   the comment still counts when the checks end and the label changes, which wakes the loop.
8. **Tests.** `tests/kit/test_session_review.py` (fixtures for each rule, a verdict already on the head, an edited comment, a
   draft, unread pages, the fingerprint). The skill, guide, reference and role-file tests are in
   `tests/kit_dev/test_review_pass_skill.py`, outside the brief's `Touches:`, because `skills/` is not vendored into a project.
9. **Flow mode.** Fragment `changelog.d/review-pass.md`; no version bump; `kit/hashes.json` is not edited (session rule 14).

## Consequences

- A conductor reviews exactly the pull requests that need a verdict, and two passes on an unchanged queue post one set of verdicts.
- A project no longer hand-writes the pass or the loop; a loop that sees no change starts no model.

## Residual

- 2026-10-29: the headless loop uses the person's own GitHub identity, which can merge and push; the guard and the role file are
  the only boundary until a maintainer sets up a comment-only identity for the conductor (due 2026-12-15).
- 2026-10-29: two conductors that check the head at the same moment can still both post; the re-read before posting narrows the
  window, it does not close it (a residual of SPEC-0030) (due 2026-12-15).
- 2026-10-29: whether a `-p` session runs the frontmatter hooks is not confirmed by the builder `(verify)`; the guard check of the
  guide is how a person finds out on their machine (due 2026-12-15).
