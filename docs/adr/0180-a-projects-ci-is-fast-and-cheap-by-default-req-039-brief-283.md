# ADR-0180: a project's CI is fast and cheap by default (REQ-039, brief 283)

- Status: Proposed
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0165, ADR-0172, ADR-0176
- Requirements: REQ-039

Protected classes: `.github/`, `scripts/agk/`, `kit/`, `tests/kit/`

## Context

Brief #283 (priority 1): in a project pilot (2026-10-27, a private repository with a monthly allowance of Actions minutes) a
required project job ran about ten minutes on every push, draft checkpoints included, and a container build uploaded a build
record each run until the Actions storage quota was hit; on day 2 the allowance ran out and every job was refused. The guidance a
project's builders follow did not say how to avoid this. Measured here: the brief's `Measured:` line names no command and was
taken in a project repository this session cannot read; the cause it names was reproduced in the kit itself on 2026-10-30 with
`grep -c "pull_request.draft" .github/workflows/proof.yml .github/workflows/governance.yml`, which printed 0 and 2: proof never
read the draft flag, and governance read it only for the body and final-clearance checks, so both ran their suites on every
draft push. The tests were written first (`tests/kit/test_doctor_ci.py`, 24 failed at the first checkpoint of the pull request).

## Decision

1. **The guide (answer 1).** `docs/guides/project-ci.md` gives the five defaults, each with a copyable snippet: heavy jobs only on
   pull requests that are not drafts (and pushes to the default branch), with `ready_for_review` as a trigger; one concurrency
   group per pull request with cancel-in-progress for pull requests only; caches of dependency installs and of container layers
   (`type=gha`), measured before they are kept; a documentation-only change that skips the heavy steps and still reports
   success, never `paths-ignore` on a required check; no build-record upload and a short artifact retention. It points to the
   `[proof]` table (ADR-0172) rather than repeating it. `docs/guides/reference.md` points to it from the doctor section.
2. **The stack ADR template (answer 1).** Its Practices gain `fast CI: check (step: agk doctor reports ci-drafts and
   ci-concurrency ok for each workflow of required_checks; ...)`, kept by a stack that names CI.
3. **The kit's own workflows (answer 2).** `governance` skips its heavy steps on a draft through the same `skip` output as a
   status-only final commit (the lint, the tests of the checks, the project tests, the kit tests check and the tooling
   install), writes one line in the job summary, and still reports; `ready_for_review` was already a trigger. `proof` gains
   `ready_for_review` and reports `outcome: skipped` on a draft through its `skip` output, then runs in full when the draft is
   marked ready. Every kit workflow carries one comment, `Fast CI (brief #283)`, that says how it meets each default or why a
   default does not apply (a schedule or a tag has no draft and no superseded run; governance reads documentation; the product
   report keeps its data 90 days on purpose). The router keeps its group of brief #309 and runs on drafts, since it labels
   them and runs no test; `drift-audit` keeps its two jobs. Two existing tests that pinned proof's trigger list now include
   `ready_for_review`.
4. **The doctor (answer 3).** Two warnings after `router-wake`: `ci-drafts` when a workflow under `.github/workflows/` (the
   router's own excluded) holds a job whose check name is in `required_checks`, runs on `pull_request`, and names
   `github.event.pull_request.draft` nowhere outside a comment, and also, as its own case, when it names the flag but has no
   `ready_for_review` outside a comment (the unsafe one: its check reports green on the draft, and when the draft is marked
   ready with no new commit nothing runs again, so the pull request could merge unchecked); the message counts the two cases
   apart (`n runs on drafts`, `n skips drafts but has no ready_for_review`) and the fix says why `ready_for_review` matters.
   `ci-concurrency` warns when such a workflow has no `concurrency:` key,
   at the top or on a job. Each is a warning (exit 4 at most), its message names the setting and the path class and a count,
   never a workflow or a check, and its fix points to the guide. A workflow that cannot be read makes both `cannot-check`. The
   job names are read by the router's own reading (`common.jobs_of`). The doctor fixture `router-unwoken` gained a draft rule and
   a group, so that it still reports only its own finding, and the counts of the report tests moved by two.
5. **Generic (answer 4).** No project or product is named in the kit and the tests use invented workflows; the one exception is
   default 5 describes the build action's options that upload a build record and write a build summary without naming them,
   since their names carry a maker's prefix; it keeps the `(verify)` mark (Q-283-3, answered by the conductor's verdict on
   8579af0, 2026-10-30).
6. **Reading Q-283-1 (taken, the conservative one; confirmed by the conductor's verdict on 8579af0, 2026-10-30: each is its own
   brief, filed by the conductor where it holds up; the line-ending rule is part of #263).** The field notes on the brief ask for more than its answers: a setting that
   says whether governance runs the project tests, minutes left and a budget per push, a degraded mode without Actions, image
   size warnings, scanning images from the daemon, a `.gitattributes` line ending rule, and a two-tier local gate. None is built
   here; each waits for its own brief.
7. **Reading Q-283-2 (taken, the conservative one; accepted by the conductor's verdict on 8579af0, 2026-10-30: a text rule
   is enough for a warning, recorded as a known limit in the Residual).** The doctor's draft rule is textual: naming the draft flag outside a comment
   counts as handling drafts. A workflow that reads the flag without skipping anything passes; a stricter reading of conditions
   would need a YAML expression reader the kit does not have.
8. **Flow mode.** Fragment `changelog.d/fast-ci-defaults.md`; no version bump. `kit/hashes.json` is not edited, although the
   brief's `Touches:` lists it: it is a release file (session rule 14).

## Consequences

- A builder's draft checkpoints cost the light governance checks and the secret scan only; the suites run once, when the pull
  request is marked ready, and on every push after that.
- A project sees two warnings until the workflows of its required checks skip drafts and cancel superseded runs.
- The status-only decision of a final commit reads the latest full run of its parent; a draft's run of the same head is older than
  the run that `ready_for_review` starts, so it is not the one read.

## Residual

- 2026-10-30: a parent head that was pushed while the pull request was a draft and never marked ready has only a draft run, which
  passed without its suites; the final commit comes after a verdict on a ready pull request, so this is not reached today, but no
  check enforces it (due 2026-12-15).
- 2026-10-30: known limit (Q-283-2): the doctor's draft, `ready_for_review` and group rules read the text, not the YAML; a
  workflow that names the flag without skipping anything, or an unusual layout, can pass or warn wrongly. All are warnings
  only (due 2026-12-15).
