# ADR-0468: Iterations and the four ceremonies are printed from facts

- Status: Proposed
- Date: 2026-11-13
- Deciders: maintainers
- Related: SPEC-0043, SPEC-0037, ADR-0269, ADR-0454, ADR-0465, ADR-0466, ADR-0467, ADR-0469, amendment 164 item 4, brief #1096, plan #661
- Requirements: REQ-050

## Context

SPEC-0043 (Approved, REQ-050, ADR-0269) rules 23 and 24 run the plan in time boxes of `[plan] iteration_days`
working days with four short outputs for the person: planning, daily status, review and retrospective. Amendment 164
item 4 (ADR-0469) adds to the review each `Demo:` screen and state with its `Design match:` line as evidence. On the
default branch at 17b2173 the estimator (`plan_estimate.py`, ADR-0465), the status (`plan_status.py`, ADR-0466), the
baseline (ADR-0467) and the `Demo:` lines of `render` (brief #1092) exist, `common.plan_settings` already reads and
refuses `iteration_days`, and no ceremony script exists. This is build (h) of rule 27.

## Decision

1. `scripts/agk/plan_ceremony.py` (new, installed, `verbatim`) runs `planning|daily|review|retro --facts FILE
   [--plan DIR] [--today D] [--weeks N] [--stalls FILE] [--matches FILE]`. It reads files only, writes nothing, posts
   nothing, files nothing and runs no other program. An input it cannot read exits 2 naming the option or the
   setting, never the value; an `iteration_days` other than a whole number from 1 to 30 is refused by
   `common.plan_settings` naming `[plan] iteration_days`.
2. The iteration: working days are Monday to Friday; day 1 is the baseline's `date` (or the first working day after
   it). Iteration `n` holds working days `(n - 1) * N + 1` to `n * N`. The current iteration is the one holding today,
   or, on a weekend, the next working day. Before the baseline date there is no iteration; without
   `baseline.json` the planning and daily outputs say `iteration unknown (no baseline)` and the review and
   retrospective, which need an iteration, exit 2 naming `--plan`.
3. Planning: the capacity is the nearest-rank P50 of the briefs closed as completed in each full past iteration (the
   same working-day windows, counted back from the current iteration's first day, or from today without a baseline)
   that lies inside rule 12's throughput (from the Monday of the first close in the window); `capacity unknown` with
   its reason while the throughput has fewer than 4 weeks or no full past iteration, and then nothing is cut. The open
   briefs are listed in milestone order, then `Depends-on` order, then priority: published briefs (the facts) by issue
   number, since `publish` prints them in `Depends-on` order and the facts carry no `Depends-on` or priority; brief
   files by their `Depends-on:` keys, then a `Priority: <n>` line (lower first, none last), then key (`Q-1096-2`).
   The first `capacity` of them are proposed under `Proposed for the person to accept or change`, the rest counted;
   then `plan_estimate.py`'s forecast lines and the limits line of rule 26.
4. Daily status: at most ten lines: what finished since the start of the previous working day (pull requests merged,
   briefs closed as completed), the open pull requests, and the blocked ones, each with the cause of a saved
   `stalls.py --json` output (`--stalls FILE`) and, for an open pull request the facts mark `stalled` without a saved
   cause, `stalled (facts)`; past seven blocked lines the last says how many more.
5. Review: per milestone touched in the iteration (a brief of it closed, or a pull request of its briefs merged, in the
   iteration): its `Exit:` criterion with its evidence (each merged pull request of its briefs with its link from the
   facts' `repo` and its proof, and each requirement its briefs advance that the facts mark done), or `no evidence
   yet`; the newest `design` row of `docs/design/signoffs.md` with its version and link; and each `Demo:` screen and
   state with the `Design match:` line of a merged pull request that names it, or `no evidence yet`, and the persona
   whose story it completes (the brief file whose `Screens:` line names it, its `Advances:` keys and their `Persona:`
   lines in `requirements-proposed.md`), or `persona unknown`. The facts carry no pull request body, so the lines come
   from `--matches FILE`, a JSON object from pull request number to its `Design match:` lines that the person saves
   (`Q-1096-1`); without it every screen reads `no evidence yet`.
6. Retrospective: measured facts of the pull requests merged in the iteration only: the estimates within range by size
   (actual hours within the declared range, SPEC-0018 rule 6), the median waits of rule 15, the `fix` verdicts as
   rework per merged pull request, and the stalls by kind (from `--stalls`, else the facts' `stalled` as `builder`);
   then at most three candidate briefs, each a `Sentence:` and a `Measured: before:` line from one measured fact,
   printed for the person and never filed or applied.
7. `docs/guides/planning.md` gains `Sprints and ceremonies`, naming the four commands and rule 26's limits.

Protected path classes changed: `scripts/agk/` (`plan_ceremony.py`, new), `kit/` (`kit/manifest.json`, and
`kit/hashes.json` only as `kit_hashes.py` prints it), `agk.toml` (one `[[testing.map]]` entry) and `tests/kit/`
(`test_plan_ceremony.py`, new).

## Consequences

A project with a plan gets four texts to paste into its own ceremonies, each from measured facts, and AGK still runs
no meeting and posts nothing. The person saves the texts under `docs/plan/iterations/<n>/` if wanted (rule 25).

## Residual

- 2026-11-13: the review's screen evidence depends on the person saving the `Design match:` lines with `--matches`;
  a missed save prints `no evidence yet` for a screen that has a match (due 2026-12-31).
- 2026-11-13: the facts list only the briefs closed in their own `--weeks` window, so the capacity reads only the
  iterations inside it (due 2026-12-31).
