# ADR-0357: A brief is checked when it is filed, and every brief belongs to a wave

- Status: Proposed
- Date: 2026-11-08
- Deciders: maintainers
- Related: amendment 140, brief #770, SPEC-0030
- Requirements: REQ-037

## Context

On 2026-11-08 five open briefs had failed `check_brief.py` for up to two days, and `session.py plan` skipped them with one
clause in its `Skipped:` line that nobody acted on. The check ran only inside the conductor's guard, so a brief filed by anyone
else was never checked; a refused brief became no action for anyone; and nothing on GitHub checked a brief when it was opened
or edited. Ten open briefs also belonged to no wave of the plan (owner direction 2026-11-08, quoted in brief #770).

This build changes the protected path classes `scripts/agk/`, `tests/kit/`, `tests/kit_dev/` (the catch log's row count), `kit/` (the manifest's `verbatim` list and the installed `.gitattributes` template), `.github/` (the new workflow), `.claude/` (the conductor's report line) and `config/` (the rule budget's lowered line).

## Decision

1. With `[flow] plan_issue` set, a brief needs one line `Wave: n`. `session.py` reads the plan's waves from the milestones
   titled `Wave <n>`; `check_brief.py` takes them with `--waves` and, without that list, checks the shape only, since a check
   makes no network call. A brief without the line, or naming a wave the plan does not have, is refused naming the rule. With no
   plan issue the line is optional.
2. `session.py plan` prints each brief refused for a brief-check rule on its own line `MALFORMED: #<n> <rule> (fix: <filer>)`,
   and no longer in `Skipped:`. The conductor's report carries those lines under `Needs a fix` until the brief passes.
3. `check_brief.py --event PAYLOAD` decides what a job does for one saved `issues` event: `ignore`, `fail` with the label
   `agk-brief-invalid` and a comment naming each failing rule, or `pass` with the wave for the milestone. It posts nothing.

4. `.github/workflows/agk-brief.yml` (the owner's yes is quoted in brief #770) runs that decision on `issues` `opened`, `edited`
   and `labeled` events of an issue labelled `agk-brief`, from a checkout of the default branch, on the saved event file, so the
   issue's text never reaches a command. It has `contents: read` and `issues: write`. It sets or clears the label and its one
   comment, and on a pass sets the issue's milestone to its wave. It also reads the milestones, for the waves. The workflow is
   installed in projects, in `verbatim` of `kit/manifest.json` (the owner's ruling Q-770-4); this names the classes `kit/` and
   `.github/`. With no milestone `Wave <n>` in a project, the `Wave:` line is checked for its shape only.
5. `doctor.py` gains the warning `brief-invalid-label`: where that workflow is in the tree and the label is missing, the owner
   creates it. A project that has deleted the workflow is asked nothing.

## Consequences

A brief refused for its shape, or for having no wave, is named on its own line each time the plan runs, with the person who can
fix it. Every open brief needs a `Wave:` line once this merges, so the repair of brief #770 answers 1 and 5 goes first.
Every project gets, on install or upgrade, one more job with `issues: write`, and its owner creates the label `agk-brief-invalid`
when `doctor.py` reports it missing.

## Residual

- 2026-11-08: the workflow runs only from the default branch, so it first acts on the first event after this merges; a brief that
  has no later event is reported by `session.py plan` alone.
- 2026-11-08: the conductor's guard (`.claude/hooks/conductor_guard.py`, outside the brief's `Touches:`) does not yet check the
  `Wave:` line when it files a brief; the plan refuses such a brief on its next run.
