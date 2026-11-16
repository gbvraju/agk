# ADR-0571: The conductor runs each pass on the tier it needs

- Status: Accepted
- Date: 2026-11-15
- Deciders: maintainers
- Related: ADR-0554, ADR-0525, ADR-0528, ADR-0568, ADR-0289, SPEC-0045 (amendment 183), brief #1359, brief #1283, plan #661
- Requirements: REQ-050

## Context

Every conductor job starts on the strongest tier at high effort: `conductor.py` sets `AGK_TIER="strongest"` for the
interactive watchdog, the scripted pass of ADR-0554 and the reviewer starts, and `.claude/agents/conductor.md` says the
role runs on `strongest`. Many passes are routine (a re-review of an applied fix list with no findings, a queue holding
only a `Report: ... nothing to change`, a sweep, a re-plan), and the co-owner's review named the always-strongest
conductor as the largest cost lever. `config.MODEL_DEFAULTS` already routes builder kinds below `strongest`, and
`watchdog --pass` already decides as a script whether a job starts. Brief #1283 (merged as #1352) gives the spend by
role and model that measures the change. SPEC-0045 rule 6 (Approved) kept the conductor on `strongest`; the maintainers
chose to amend it in the same pull request (`Maintainer answer: Q-1359-3 (a)`: "first reviews and risky changes stay on
the strongest model"), and `docs/runs/proposed-spec-amendments-183.md` holds the amended lines.

## Decision

1. **The starter picks the tier from the queue.** `watchdog --pass` reads each pull request that
   `session.py review-queue --all` lists for review (the pull request, its files and its comments, GET only) and starts
   the job on `strongest` at `high` when any of them changes a protected path class (`config/protected-paths.txt`),
   adds or changes a spec or ADR (`docs/specs/`, `docs/adr/`), is a first review (no verdict by a counted verdict
   author yet: every first review, by the maintainers' answer to Q-1359-3, so the brief's `[review] large_lines` bound
   is not added), carries a `Question:` or a `Correction:` after its last verdict or two verdicts of different kinds
   on one head (a disagreement), or is an intake (a title starting `Intake:`); also when the queue holds a question
   on a brief, or cannot be read. Every other pass starts on `mid` at `medium`. The tier and effort reach the adapter
   as `AGK_TIER` and `AGK_EFFORT`, the prompt names them, and the pass prints `watchdog: tier <tier>[: <why>]` and
   `watchdog: job started <name> on <tier> at <effort>: <why>`.
2. **A step up, never down inside a pass.** A mid job's prompt tells it to post no verdict on a pull request that meets
   any row of decision 1 or whose verdict it is unsure of, and to end with one line `escalate: #<n> <reason>` for
   each. The watchdog reads those lines from the adapter's output, and for a background job from
   `<worktree>/.agk-session.log` once the job has ended (read once per job), and starts one strongest job for all of
   them at once, printing `watchdog: escalated #<n> to strongest: <reason>`. Every verdict names its tier in its
   `Read:` line as `tier: <tier>`, so the shadow and the daily list can count them.
3. **Floors stay.** `REVIEW_FLOOR` and the reviewer starts (ADR-0528) stay on `strongest` at `high`; the interactive
   `watchdog` without `--pass`, which starts a looping conductor, stays on `strongest`; the architect and shadow
   roles are unchanged. `[models] conductor = "strongest"`, the one value accepted, pins every pass to `strongest`;
   another value is refused naming the setting (`setting: models.conductor`). SPEC-0045 rules 2 (the `conductor`
   key) and 6 (the scripted pass's exception) are amended by amendment 183.
4. **Measured.** The pull request body gives the before figure; the share of passes on each tier, the tokens per
   merged pull request over the first week and the share of mid verdicts that the shadow or a later strongest pass
   changed are read from #1283's spend by role and model and the `tier:` marks of decision 2.
5. **By mode.** Local mode takes all of it. CI mode: the cloud conductor task reads the same rule from the role file
   when it starts a pass; no workflow, ruleset or required check changes. Personal mode has no conductor and is
   unchanged. Stacks: not applicable.

## Consequences

Routine passes start on the mid tier and every escalation costs one strongest pass. Protected path classes changed:
`scripts/agk/` (`conductor.py`, `config.py`), `.claude/` (`.claude/agents/conductor.md`), `tests/kit/`
(`test_conductor_tier.py`), `kit/` (`kit/templates/agk.toml`) and
`agk.toml` (the pin as a comment and the new test file in the `[[testing.map]]` entries of `conductor.py`,
`config.py` and `.claude/agents/*.md`).

Not protected: `docs/specs/0045-each-kind-of-work-runs-on-the-model-it-needs.md` (rules 2 and 6, amendment 183) and
`docs/runs/proposed-spec-amendments-183.md`.

## Residual

- 2026-11-15: the Windows adapter opens the job in a Windows Terminal tab and keeps no log (confirmed, Q-1359-2), so
  a background mid job's `escalate:` lines there are not read until the next strongest pass.
- 2026-11-15: a mid pass that misjudges a row and posts a verdict anyway is caught only by the shadow or a later
  strongest pass; decision 4's measure counts those.
