# ADR-0224: the self-hosted runner guide adds one shared, opt-in pool for an organisation (REQ-039, brief 410)

- Status: Accepted
- Date: 2026-10-31
- Deciders: maintainers
- Related: ADR-0217
- Requirements: REQ-039

Protected classes: `tests/kit_dev/`

## Context

Brief #410, from #288 part 2. ADR-0217 (brief #372) documented one project's own ephemeral runner. An organisation with several
AGK projects asks for one pool that serves all of them, with shared caches, and that a pull request from a fork can never reach.
The brief is documentation and one guide test; the test lives under `tests/kit_dev/`, a protected class, so this ADR covers it
(the conductor reserved ADR-0224 for it). The brief names no `Measured:` line. The tests were written first
(`tests/kit_dev/test_self_hosted_pool.py`: 10 failed without the section, at the first checkpoint of the pull request).

## Decision

1. **The section (answer 1).** `docs/guides/self-hosted-runner.md` gains a section "One pool for an organisation": an
   organisation runner group limited to selected private repositories, never a public one; ephemeral runners only, starting
   with one machine and autoscaling later; shared caches (container layers, package managers, browsers) on a volume that holds
   no credential; no deploy or production secret on any runner, and a job token with read permissions only; governance and
   proof on GitHub-hosted runners as the trust anchor. Rule 2 of the guide, which registered a runner on the one repository,
   now points to this section for an organisation's pool.
2. **The snippet (answer 2).** A copyable job reads its runner from the repository variable `AGK_HEAVY_RUNNER`, with
   `ubuntu-latest` as the fallback, and its `if:` keeps a pull request from a fork off the pool with the brief's guard, written
   as `github.event_name != 'pull_request' || <guard>` as in the guide's existing job, so that a push still runs the job.
3. **Measuring (answer 3).** The section says to run `minutes.py` one week before and one week after the switch. Because
   `minutes.py` treats a job as self-hosted by the label `self-hosted` among the labels the job asked for, the guide sets the
   variable to `self-hosted`; a custom label alone would be counted as hosted minutes (question Q-410-1, answered in the verdict
   on 4c868ed: this reading stands). Since every self-hosted runner carries that label, it picks the pool only while the pool's
   group holds the repository's only self-hosted runners, and a person step checks that the repository reaches no other one (no
   runner registered on the repository, and a Default group that holds none or does not include it).
4. **The person's steps (answer 4).** The kit sets up no runner, no runner group and no variable; the section lists each as a
   step the person takes in the organisation or repository settings, each marked `(verify)`.
5. **Tests (answer 5).** `tests/kit_dev/test_self_hosted_pool.py`: the section exists once; each rule of answer 1; the snippet
   with the variable, the hosted fallback, the fork guard and read permissions only; the measurement; the person's steps,
   including the check that no other self-hosted runner reaches the repository; rule 2 points to the section.
6. **Flow mode.** One fragment `changelog.d/self-hosted-pool.md`; no version bump; `kit/hashes.json` not edited (session rule
   14).

## Consequences

- An organisation with several AGK projects has one documented way to share one pool of ephemeral runners, opt-in per
  repository through one variable, without weakening the checks that stay on GitHub-hosted runners.
- Runner groups, their repository access and the settings they need depend on GitHub's current plans and settings; the steps
  are marked `(verify)` and are the person's to confirm.

## Residual

- 2026-10-31: none open (Q-410-1 answered in the verdict on 4c868ed).
