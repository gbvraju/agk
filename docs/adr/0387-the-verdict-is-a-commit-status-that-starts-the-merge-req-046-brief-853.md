# ADR-0387: The verdict is a commit status that starts the merge, and pull requests are up to date before merge

- Status: Proposed
- Date: 2026-11-09
- Deciders: maintainers
- Related: ADR-0354, ADR-0373, ADR-0383, amendment 151, brief #853
- Requirements: REQ-046

## Context

Measured on 2026-11-09: cleared heads waited 80 minutes (#783) and 7 hours 26 minutes (#831), and the merger's schedule ran 2 of about 32 times overnight. The ruleset's required checks had `strict_required_status_checks_policy: false`, so #831, green on its own head, turned main red at e05411d. GitHub's merge queue is offered only on organization-owned public repositories and on Enterprise Cloud, so a personal repository cannot use it, and the ruleset's code-owner review keeps GitHub's own auto-merge from firing.

This build changes the protected path classes `.github/` (the workflow `merger.yml`), `.claude/` (`.claude/agents/conductor.md`), `scripts/agk/` and `tests/kit/`. A workflow change needs its own ADR (session rule 36), and the owner's yes for it is quoted in brief #853.

## Decision

1. `merge_cleared.py --status --pr N --sha <head>` computes the commit status `agk/verdict` with the reading of the merge and sets it: `success` when the latest verdict clears that head, no hold of rule 5 stands and the head is not in the re-prove state; otherwise `pending`, the description being `fix list`, `rejected`, `no verdict`, `no verdict for this head`, `approve SPEC-nnnn`, `re-prove <file>`, `owner merge` (a release or a path class of rule 5), or the hold's own words. A `--sha` that is not the head sets nothing, so a new push has no status. The same status is not set twice. In local mode, as rule 4 reads it, the command prints the state and sets nothing.
2. `merger.yml` also starts on the `status` event for `agk/verdict` with `success`, as a condition of its existing job, with no new job. `--event` names the one open pull request into the default branch whose head is that sha; anything else does nothing. The status only starts the job: the guarded command reads the verdict again and is the only thing that merges. The sweep and the schedule stay as a fallback, and a status event never sweeps.
3. The job, on a `Verdict:`, `Approve:` or edited `Final:` comment, sets the status before it looks for a target, and the sweep refreshes the status of each cleared head when main moves. The job's token gains `statuses: write`. A status set with the job's token starts no workflow (verify), and the status step acts only on a comment, so nothing can loop.
4. `doctor.py` warns (`ruleset-up-to-date`) when `strict_required_status_checks_policy` is off in a repository with `[flow] auto_merge = true`, unless `[flow] merge_queue` is on.
5. `[flow] merge_queue = true` (default `false`; anything but a boolean is refused naming the setting) is for a project that can use GitHub's merge queue: `agk/verdict` is a required status of the queue, the guarded command holds naming the setting, the job finds no target, and the status does not read the re-prove state, because the queue tests the pull request together with the default branch.

## Consequences

A cleared head merges when its verdict is posted or its status is set, without waiting for a schedule. After this merges, the owner turns on "Require branches to be up to date before merging" in the ruleset and adds `agk/verdict` to the required status checks; until then doctor warns and behaviour is as before. Every status event of any check starts a run of the workflow whose jobs are skipped by their conditions, which costs no job.

## Residual

- 2026-11-09: anyone who can write statuses can start the job with a `success`, and a stale `success` can stand until the next refresh. Neither merges anything: the guarded command reads the verdict and the holds again. With `agk/verdict` required, a stale `success` no longer holds the owner's own merge button.
- 2026-11-09: `.claude/hooks/conductor_guard.py` allows the conductor exactly `--pr <n> --sha <sha>`, and is not among the brief's `Touches:`, so the conductor cannot yet run `--status` (`Q-853-1`). Until it can, the status of a head follows the merger job and the sweep; a fix list posted while the job cannot run leaves the old status until the sweep.
- 2026-11-09: the router does not refresh the status: `route.py` and `agk-route.yml` are not among the brief's `Touches:` and the owner's yes names `merger.yml` alone (`Q-853-2`).
- 2026-11-09: the `status` event runs from the default branch and reports the default branch as its ref (verify); it is read from GitHub's documentation, not from a run of this workflow.
