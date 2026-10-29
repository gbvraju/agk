# ADR-0178: a brief is closed when the pull request that finishes it merges (REQ-039, brief 302)

- Status: Proposed
- Date: 2026-10-29
- Deciders: maintainers
- Related: ADR-0165, ADR-0174
- Requirements: REQ-039

Protected classes: `.github/`, `config/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`

## Context

Brief #302 (priority 2). On 2026-10-29 the conductor found nine briefs whose pull requests had merged but which were still open
(#269, #270, #272, #273, #274, #282, #285, #291, #295). Their bodies said `Brief: #n` and never `Closes #n`, because one brief can
take several builds. An open finished brief misleads `session.py next`, the `Depends-on` check and anyone reading the board. The
conductor's field note on the brief reserves this ADR, makes the work depend on #309 (pull request #310), because both change
`scripts/agk/route.py` and the router workflow, and puts the workflow's `closed` type and `init.py`/`upgrade.py` in scope. The
tests were written first (checkpoint c24a654) and were red on the unchanged tree.

## Decision

1. **The line (answers 1 and 2).** A pull request body may carry one line `Finishes: #n`. It says that the pull request is the
   last one of brief #n. `common.py` reads it (`finishes_problem`, `finished_brief`). It counts only once, and only beside the
   first `Brief:` line naming the same number as `Brief: #n`. `check_pr_body.py` fails a body whose `Finishes:` line breaks that
   rule (malformed, repeated, without `Brief: #n`, or naming another brief). The message names the rule and the line, never a
   number. A draft is not checked, as before.
2. **The router closes the brief (answer 1).** `agk-route.yml` adds `closed` to its `pull_request` types. Its job runs for a
   closed pull request only when `github.event.pull_request.merged` is true. On that event `route.py` reads the pull request
   again with GET. It acts only when GitHub reports it merged and its body finishes brief #n. It then reads issue #n and acts
   only when #n is an open issue (not a pull request) labelled `agk-brief`. It posts one comment
   `Finished by #<pr> (merge commit <sha>).` unless a comment starting `Finished by #<pr> (merge commit ` is already there, and
   then closes #n with `state_reason=completed`. It closes no other issue, runs no code of the pull request, and keeps the
   five permissions (`issues: write` already covers it). A 403 is skipped as before (a fork's read-only token). An unreadable
   read fails, naming the rule. `--dry-run` writes nothing. A body with `Brief: #n` and no `Finishes:` leaves the brief open.
3. **Install (field note).** `init.py` and `upgrade.py` already write the kit's router whole, with only its `workflow_run` list
   taken from the project (ADR-0165). So they write the new type and condition with no code change.
   `tests/kit_dev/test_route_finishes_install.py` shows it for init, and for an upgrade from the released router that keeps the
   project's names.
4. **The prompt and the rules (answer 2).** The builder prompt of `launch.py` tells the pull request that finishes a brief (its
   only one, or the one of its last build) to carry `Finishes: #<brief>`. Session rule 28 now asks the last pull request of a
   brief for `Finishes: #<brief>` beside `Brief: #<brief>` as well as `Closes #<brief>`. The `Closes` line is kept, because rule 28
   already asked for it and this session's prompt names it (Q-302-1).
5. **The doctor (answer 3).** A new check, `brief-finished` (warn, after `brief-label`), reads the open `agk-brief` issues and the
   latest 100 pull requests with GET. It lists each open brief that has pull requests naming it with `Brief: #n`, none of them
   open, at least one merged, and its latest merge more than a day old. A pull request closed without a merge is not counted. A
   read that fails is `cannot-check`.
6. **Tests (answer 4).** `tests/kit/test_route_finishes.py`, `tests/kit/test_check_pr_body.py`,
   `tests/kit/test_doctor_finished_briefs.py` with the case `brief-finished-open`, and
   `tests/kit_dev/test_route_finishes_install.py`. `test_route.py` expects the new type. `test_doctor.py` counts one more check
   and two more reads. Flow mode: fragment `changelog.d/brief-finishes.md`, no version bump. `kit/hashes.json` is not edited
   (session rule 14).

## Spec amendments

Amendment 96 (`docs/runs/proposed-spec-amendments-96.md`) changes SPEC-0032 rules 1 and 8 (the `closed` type and the brief the
router closes) and SPEC-0006 rules 5 and 6 (the `brief-finished` check and its two reads). The number was
confirmed in the verdict on 08b173a (Q-302-2).

## Consequences

- A brief closes when its finishing pull request merges, so `session.py next`, `Depends-on` and the board read the truth.
- The router runs once more per merged pull request. A pull request closed without a merge starts no job.
- A brief whose last pull request forgot the line stays open, and the doctor lists it after a day.

## Residual

- 2026-10-29: Q-302-1 to Q-302-4 were answered in the verdict on 08b173a. Q-302-1: keep both lines; `Closes #n` is GitHub's own
  close and works when the router does not run, and `Finishes: #n` gives the router's completed close with the merge-commit
  comment and lets the doctor reason about briefs. Q-302-2: amendment 96 is confirmed (95 is held for the SPEC-0010 amendment of
  #305). Q-302-3: the stacking on #310 is accepted, as the brief's field note asked; this pull request merges after #310.
  Q-302-4: `.claude/agents/conductor.md` stays as it is (outside `Touches:`, and `Closes #<brief>` stays required).
- The doctor reads only the latest 100 pull requests, so an older finished brief is not listed.
