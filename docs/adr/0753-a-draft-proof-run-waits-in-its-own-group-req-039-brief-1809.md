# ADR-0753: A draft's proof run waits in its own group, so it never cancels the ready run (REQ-039)

- Status: Accepted
- Date: 2026-11-23
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1809, found bug of #1808, brief #216, brief #283, brief #369, ADR-0207, brief #972, found bug #1253, brief #1371, ADR-0576, plan #661
- Requirements: REQ-039

Protected classes: `.github/`, `tests/kit/`

## Context

On #1808's head a396ea72 the push and `ready_for_review` arrived within milliseconds. The ready event's proof run was
cancelled three seconds later by the push's run, whose payload still said draft, so its job was skipped by the
job-level `if:`. The head ended with proof `skipped, cancelled` and no proof run that ran. `proof.yml` put every
`pull_request` event of a pull request in one group, `proof-<number>`, with `cancel-in-progress`; GitHub admits a run
to its group and cancels the older one before it reads the job's `if:`, so a run that only skips still cancels one
that would run. ADR-0576 fixed the same race for governance's `edited` run with a group of its own. `proof` is a
required check, so in hosted CI such a head waits for a person to re-run it (1 of the last 10 merged heads). The
owner's word (2026-11-23, the steward chat, quoted as data): "Yes, file the proof race brief".

## Decision

1. Separate groups. `proof.yml`'s group is `proof-<number>-draft` for a `pull_request` event whose payload is a
   draft and `proof-<number>` otherwise; a `merge_group` run keeps its own sha group, `proof-<sha>`, and is never
   cancelled. A draft run cancels only an older draft run; a ready run cancels an older ready run, as before.
2. No new minutes. The job-level `if:` that skips a draft (brief #369, ADR-0207) is unchanged.
3. The class stays closed. `tests/kit/test_ci_saving.py` reads every workflow under `.github/workflows/` with a
   job-level draft skip and fails, naming the file, when a draft payload and a ready payload of one pull request fall
   in one group whose `cancel-in-progress` is true.
4. No setting is added. `execution`, `[flow] auto_merge`, `merge_queue`, `required_checks`, `review_mode` and
   `pr_mode` are read as before; personal mode runs no workflow.

## Consequences

A push followed at once by ready for review always leaves one proof run that ran on the head. When a ready pull
request is turned back into a draft and pushed, the draft run no longer cancels the running ready run of the older
head; that run ends on its own head, which the router's latest-head reading supersedes: one extra run's minutes at
most. The installed `proof.yml` changes its group line; its hash in `kit/hashes.json` changes by the maintainers'
shared-mechanical step (session rule 14), never by this build.

## Residual

- 2026-11-23: the guard reads the job-level `if:` and the top-level `concurrency:` only; a workflow that skips a draft
  in a step, or sets `concurrency:` on a job, is not read by it (none does today).
