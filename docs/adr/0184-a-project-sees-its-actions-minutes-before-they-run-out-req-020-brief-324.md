# ADR-0184: a project sees its Actions minutes before they run out (REQ-020, brief 324)

- Status: Accepted
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0180
- Requirements: REQ-020

Protected classes: `scripts/agk/`, `kit/`, `tests/kit/`

## Context

Brief #324 (priority 1, part of #287 answer 7): in a pilot a private organisation repository on a free plan used up its included
Actions minutes on day 2 without warning, and the team estimated its use by hand from the run history. The brief has no
`Measured:` line. Run here on this repository on 2026-10-30, the new command read 2,500 runs created since the day before the
month began (the run list answers the newest 1,000 of them), and could not read billing with the session's token (refused).

## Decision

1. **One command (answer 1).** `scripts/agk/minutes.py`, standard library only, reads with `gh api --method GET` (the credential
   stays in `gh`) or from recorded responses (`--api-dir`), and prints: the minutes used this month (the account's billing
   figure where it answers, otherwise the estimate); the plan's included minutes, or `unknown (the token cannot read billing:
   <class>)` with the class `refused` (401, 403), `missing` (404, 410, or no recorded response) or `unreadable` (any other answer,
   or a body without the two figures); the estimate from the run history; and the minutes per merged pull request.
   `--json` prints the same figures. It is installed in a project (`kit/manifest.json`, verbatim).
2. **The estimate.** The month is the calendar month of the day in UTC. The runs created from the day before it began are read,
   then each job that started within the month on a GitHub-hosted runner is counted, rounded up to a whole minute; a skipped job
   counts none. In a private repository each job's minutes are then multiplied by its runner's rate, read from its labels, as the
   included minutes are used: a label that starts `windows` counts 2x, one that starts `macos` 10x, any other runner once
   `(verify)`; the output says the rates are applied. A known limit, said in the output and the guide: a re-run keeps its run's
   creation time, so re-runs of runs created before this month are not counted. A job whose labels name `self-hosted` and a job
   still running are listed and not counted. A run list longer than
   it answers, or a run whose jobs cannot be read, makes the estimate (and the figure per pull request) `at least`. The billing
   endpoint follows the owner's type (`/orgs/...` or `/users/.../settings/billing/actions`) `(verify)`. Job lists are read eight
   at a time, so a month of a thousand runs reads in about a minute and a half.
3. **The figure per merged pull request** is the estimate divided by the pull requests merged in the month; with none merged it
   is `-`, never a division by zero.
4. **The warning (answer 2).** `minutes_warn` in `agk.toml` (optional, 80 when unset, a whole number from 1 to 100; any other
   value is refused naming the setting) sets the threshold. When the included minutes are known and the higher of the billing
   figure and the estimate reaches that percent of them, one `warning:` line is printed, pointing to local mode in the guide, and
   the command exits 3; otherwise it exits 0. It writes nothing. A repository that cannot be read fails (exit 1) naming the
   path class, never the repository.
5. **The guide (answer 3).** `docs/guides/project-ci.md` gains `How many minutes are left`, which says how to read each line and
   points to local mode (brief #322) for when the minutes run out. `kit/templates/agk.toml` names the setting in a comment.
6. **Not built.** `doctor.py` and the Autopilot preflight do not read the minutes here (#287 answer 7 names them; this build
   must not edit `doctor.py`). `docs/guides/reference.md` is not edited, although the brief's `Touches:` lists it (decision 8).
   `kit/manifest.json` is changed although the brief's `Touches:` does not list it, so that a project has the command.
7. **Flow mode.** Fragment `changelog.d/actions-minutes.md`; no version bump. `kit/hashes.json` is a release file and is not
   edited (session rule 14).

8. **Reading Q-324-1 (answered by the conductor's verdict on 8e06ed5, 2026-10-30).** The guide section is enough; a pointer in
   `docs/guides/reference.md` can follow after the open pull request that changes it merges.
9. **Reading Q-324-2 (answered by the conductor's verdict on 8e06ed5, 2026-10-30).** The runner rates are applied for a private
   repository, as decision 2 says.
10. **Reading Q-324-3 (answered by the conductor's verdict on 8e06ed5, 2026-10-30).** The endpoint stays, with `missing` as the
   fallback; the newer billing platform's usage endpoint is a residual and a later brief.

## Consequences

- A person sees in one command whether the month's minutes will last and what each merged pull request costs, and the guide's
  defaults can be judged against that figure.
- With a token that cannot read billing, the included minutes stay unknown and no warning is printed; the estimate is still
  shown.

## Residual

- 2026-10-30: the billing endpoint read is the one of the older billing reports; an account on the newer billing platform may
  answer `missing`, and reading that platform's usage endpoint waits for a later brief (Q-324-3, due 2026-12-15).
- 2026-10-30: re-runs of runs created before this month are not counted (decision 2); reading them would need every older run's
  jobs (due 2026-12-15).
