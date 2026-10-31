# ADR-0217: a documented, opt-in way to run a project's heavy jobs on its own ephemeral runner (REQ-039, brief 372)

- Status: Accepted
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0180, ADR-0182, ADR-0184
- Requirements: REQ-039

Protected classes: `tests/kit_dev/`

## Context

Brief #372, from #287 answer 9 and #288 part 2. A private repository on the Free plan has a fixed monthly allowance of Actions
minutes for the whole account, and heavy jobs (full suites, image builds, scans) use most of it. GitHub supports self-hosted
runners, but a careless one is a security risk: persistent, reused between jobs, or holding secrets. The kit says nothing about
it, and `minutes.py` already lists self-hosted jobs as not counted. The brief is documentation and one guide test; the test
lives under `tests/kit_dev/`, a protected class, so this ADR covers it (the conductor reserved ADR-0217 for that case). The
brief names no `Measured:` line. The tests were written first (`tests/kit_dev/test_self_hosted_guide.py`: 9 failed without the
guide, at the first checkpoint of the pull request).

## Decision

1. **The guide (answer 1).** `docs/guides/self-hosted-runner.md` has, in order: when it fits (a private repository, heavy jobs
   only, minutes short; never a public repository); the rules (an ephemeral runner that takes one job and is then removed,
   never on a public repository or for pull requests from forks, no secret beyond the job's own, never deploy or production
   credentials); how to set up an ephemeral runner, each step that depends on the person's machine or plan marked `(verify)`;
   how a heavy job opts in (`runs-on` with the runner's labels) while governance and proof stay on GitHub-hosted runners as the
   trust anchor; and what to do when the runner is down (the job waits; fall back to `ubuntu-latest` for that job, or to local
   mode). It changes no workflow of the kit and no file a project installs: a project opts in by editing its own heavy job.
2. **The pointers (answer 2).** `docs/guides/reference.md` lists the guide, and `docs/guides/project-ci.md` links it from its
   minutes section (`project-ci.md` is outside the brief's `Touches:`, but answer 2 names it).
3. **Tests (answer 3).** `tests/kit_dev/test_self_hosted_guide.py`: each section in order; the phrases of each rule; every
   setup step marked `(verify)`; no fenced block that names `self-hosted` names a kit workflow file or a kit job, and no block
   that names governance or proof names `self-hosted`; the fallback; no vendor beyond GitHub; the reference and the minutes
   section link the guide.
4. **Flow mode.** One fragment `changelog.d/self-hosted-runner.md`; no version bump; `kit/hashes.json` not edited (session rule
   14).

## Consequences

- A project short of minutes has one documented, opt-in way to move its heavy jobs off hosted runners without weakening the
  checks the kit relies on, which stay on GitHub-hosted runners.
- The runner's setup depends on GitHub's current runner application and the person's machine; the steps are marked `(verify)`
  and are the person's to confirm.

## Residual

- 2026-10-30: none open.
