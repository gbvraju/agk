# SPEC-0033: A stopped session loses nothing and the next one resumes with one command

- Status: Draft
- Owner: reviewer group (a team from config/reviewers.yaml)
- Requirements: REQ-040

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.
Written by the intake of one sentence (SPEC-0012): "When a session stops in the middle of its work for any reason, nothing it did is lost or half-applied, and the next session resumes from the branch and the pull request with one command instead of starting again." It is generic and project-agnostic: it holds for every project the kit is installed in and names no project and no reader. Evidence: sessions stop without warning (the account runs out of credits or tokens, the usage limit of a session is reached, an idle machine is reclaimed, a person closes the session); a builder's uncommitted work lives only on its machine, its progress only in its context, and a brief it took stays taken.
The maintainers gave 9 answers before it was written, in the brief of issue #182 and not as interview questions: (1) a builder commits and pushes at every step that leaves its tests green or expected-red, with a subject starting `checkpoint:`, the first checkpoint opens the pull request as a draft, and the draft is ignored by the body and clearance checks until it is marked ready; (2) one `Progress:` comment per pull request, edited in place; (3) `session.py resume --pr N` prints where the work stands from GitHub and git only; (4) a pull request that has not changed for `stall_hours` is stalled and `session.py next` offers it before a new brief and takes it over with one comment; (5) a conductor posts a verdict whole or not at all; (6) a whole account without credits needs no person to reconstruct the state, and the guide says so; (7) a usage figure is reported when the runtime shows one and summed, never guessed; (8) it is built in three parts after intake; (9) the tests use saved responses and git in a temporary directory. The principles are: every side effect is atomic (a push, one comment, one label); state lives in git and GitHub, never only in a session; resuming costs less than redoing; and nothing depends on a runtime's way of reporting its limits, because a session usually cannot see its limit before it is hit.

## Rules

1. **Checkpoints.** A builder commits and pushes its branch at every step that leaves the tests it has written so far green or expected-red (tests first, then each part). The subject of such a commit starts with `checkpoint:`. The first checkpoint opens the pull request as a draft, so the work is visible and owned at once. A checkpoint never carries a `Final:` status line (SPEC-0021). The pull request is marked ready for review only when the builder's own checks pass. `config/session-rules.md` says so in one numbered rule.
2. **Drafts are ignored.** `check_pr_body.py` and `check_final_clearance.py` ignore a draft pull request until it is marked ready. The workflow gives them the draft flag of the pull request as a file or an input; neither script calls GitHub.
3. **The progress line.** After each checkpoint the builder posts or edits one comment on its pull request whose first line is `Progress: <head> done <n>/<m>; next: <step>`, where the steps are the numbered answers or rules of its brief. It is edited in place and never repeated, so the pull request holds exactly one such comment. `<head>` is a prefix of the head at the time of the checkpoint.
4. **Resume.** `python3 scripts/agk/session.py resume --pr N` prints, from GitHub and git only: the brief and its answers, the progress line, the last verdict and whether it names the head, the state label of the pull request, and the local commands that check out the branch at its head. A new session started on a stalled pull request runs it first and continues from `next:`; it never redoes a step that the progress line marks done unless a verdict says so. It writes nothing.
5. **Takeover.** A pull request whose head, progress line and comments have not changed for `stall_hours` (the key of the flow table of `agk.toml`, 4 by default) is stalled. `session.py next` offers a stalled pull request before a new brief, takes it over with one comment `taken over: <id> <YYYY-MM-DD>`, and the new session works on the same branch and the same pull request: one pull request per brief, never a second. The take comment is the only write of the script, as in SPEC-0030 rule 3. The weekly report and the router show a stalled pull request as At risk.
6. **The conductor.** A verdict is one comment written whole and posted once, so a conductor that stops during a review posts nothing. The pull request keeps its `agk:review` label and the next conductor reviews it from scratch. A conductor never posts a partial verdict or a verdict in parts.
7. **A whole account without credits.** Every session stops. The GitHub side (the router, CI, the labels) keeps running and needs no model. When credits return, `session.py queue` and `session.py resume` show where each piece of work stands, and nothing needs a person to reconstruct it. The getting-started guide states this, and states that Actions minutes on private repositories are a second budget that the router uses, one short job per event.
8. **Cost visibility.** A builder's `Report:` line may carry a usage figure when the runtime shows one: a trailing `Usage: <n> tokens` with a whole number. The weekly report sums the figures reported for each pull request and prints `not reported` for a pull request with none, never zero and never an estimate.
9. **No network in a check.** `session.py` stays the only script that calls GitHub, only through `gh api`; `check_pr_body.py`, `check_final_clearance.py` and the report read files and git only.
10. **Not built.** Reading the limit of a runtime, resuming a session by itself, a server or a daemon, auto-merge, and any model call in a check.
11. **How it is built.** Intake first (the requirement, this spec and its ADR; amendments to SPEC-0030 by proposal). Then three builds from the default branch, each its own pull request in flow mode with its fragment, an ADR that names the protected classes and tests first: (a) checkpoints, draft pull requests and the progress line, in the session rules and in `check_pr_body.py` and `check_final_clearance.py`; (b) `session.py resume` and the stalled takeover in `next`; (c) the report lines. The builds follow the state labels of the router (the brief of issue #179) and share the flow table with the work-management brief (issue #176).
12. **The tests.** Fixtures of saved GitHub responses and git repositories in `tmp_path`, with a `gh` stub on `PATH`, no network and no model: a draft pull request ignored by the body and clearance checks; one progress line edited and not repeated; `resume` printing each part; a stalled pull request offered before a brief and taken over with one comment; a fresh pull request not stalled; a usage figure summed and a missing one reported as `not reported`.

## Tests

- Rule 1: the rules file states the checkpoint rule; REQ-040 AC1.
- Rule 2: a draft is ignored by both checks; REQ-040 AC2.
- Rule 3: one progress line, edited in place; REQ-040 AC3.
- Rule 4: `resume` prints each part and writes nothing; REQ-040 AC4.
- Rule 5: a stalled pull request is offered first and taken over with one comment, a fresh one is not; REQ-040 AC5.
- Rule 6: a conductor's verdict is one whole comment, and a stopped review leaves the label; REQ-040 AC6.
- Rule 7: the guide's statements, and `queue` with `resume` after a stop; REQ-040 AC7.
- Rule 8: the usage figure is summed and a missing one is `not reported`; REQ-040 AC8.

## Proof

REQ-040 AC1 and AC2: *work is on the branch before the session ends.* Rules 1 and 2. REQ-040 AC3 and AC4: *the next session knows where to continue.* Rules 3 and 4. REQ-040 AC5: *a stalled item does not stay taken.* Rule 5. REQ-040 AC6: *a stopped conductor leaves nothing half-said.* Rule 6. REQ-040 AC7: *a stopped account is not a lost afternoon.* Rule 7. REQ-040 AC8: *what the work cost is measured where it is shown.* Rule 8. The first stall, resumed this way, with the number of messages the maintainers still had to write, is recorded by the maintainers.

## Residual

- 2026-10-25: a session that stops between its push and its `Progress:` edit leaves a progress line one checkpoint behind the head; `resume` prints both and the new session reads the log of the branch (due 2026-12-31).
- 2026-10-25: `stall_hours` is a single number for all work; a long review may be offered for takeover while its builder waits (due 2026-12-31).

## Open questions

none
