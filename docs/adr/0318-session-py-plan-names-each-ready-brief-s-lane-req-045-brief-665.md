# ADR-0318: `session.py plan` names each ready brief's lane (REQ-045, brief 665)

- Status: Accepted
- Date: 2026-11-07
- Deciders: maintainers
- Related: ADR-0251, ADR-0312, SPEC-0038, SPEC-0034
- Requirements: REQ-045

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

SPEC-0038 rule 12 build (g) builds rule 8: with a declared work type, `session.py plan` names, for
each ready brief, the lane whose `kinds` hold the brief's `Kind:` line, or `lane: none` for a brief
without one (`Q-S0038-8`); the lane only labels and orders the ready briefs (within the same
priority, the earlier phase first) and parallel builders are offered briefs from different lanes
first (the sentence of brief #665); the plan prints the playbook's `heavy_steps` once, as the steps
a builder runs under `lock.py run --name heavy`, and changes no lock setting; waves, capacity, the
merge queue and the safe merge set stay as SPEC-0034 rule 15 decides them, so a lane never lets two
briefs whose files overlap run together; without a declaration the plan prints exactly what it
prints today (REQ-045 AC3 and AC4). Brief #665 gives the build; ADR-0251 sets the direction and
lists the classes the builds of SPEC-0038 change; ADR-0312 built the declaration (build (b)) and
ruled that a playbook is read through `scripts/agk/playbook_format.py`. This ADR number was
reserved for brief #665 by the conductor.

## Decision

1. The plan reads the declaration with `playbook_format.selected(root)` (ADR-0312 decision 1), not
   with a reader of its own, and reads the selected playbook with `tomllib`, taking only its
   `work_type`, `[[lanes]]`, `[split]` and `heavy_steps`. With no declaration, or with one that
   `doctor.py` and `check_playbooks.py` refuse (rule 5), the plan reads no playbook and its words
   and its `--json` are byte for byte what the default branch prints; no value of a refused
   declaration is printed. A brief's kind is its one line `Kind: <kind>`, read as `Touches:` and
   `Priority:` are read.
2. **The label.** The plan's words gain, with a declaration, one line after the `Start` line (and
   the `Capacity` line, where there is one): `Lanes (<work type>): #<n> lane: <lane>; ...`, one
   entry per ready brief in the plan's order, where the lane is the first `[[lanes]]` entry whose
   `kinds` hold the brief's kind, and `none` for a brief without a `Kind:` line, with a kind that
   no lane holds (`contract` in `web-app.toml`), or with a kind the playbook does not know; none of
   these is an error; with no ready brief the line reads `no ready brief`. `--json` gains one key
   `playbook` with `work_type`, `lanes` (one
   `{brief, kind, lane}` per ready brief, in the same order) and `heavy_steps`; every other key is
   as before.
3. **The order.** With a declaration the ready briefs are ordered by priority, then by phase, then
   across lanes, then by number: a kind's phase rank is its depth in `[split] depends_on` (a kind
   that depends on no kind is first, and each later kind is one deeper than the deepest kind it
   depends on), which is the phase `order` of `web-app.toml` for every kind of its `brief_order`
   (`Q-665-1`); a brief without a kind, or with a kind the playbook does not know, belongs to no
   phase and follows the kinded briefs of its priority, by number among themselves (`Q-665-2`);
   within one priority and phase rank the briefs are taken one per lane in turn, in the order of
   `[[lanes]]`, then `none`, each lane by number, so that two parallel builders are offered briefs
   from different lanes first. The waves then decide as before: a brief whose files overlap an
   earlier brief of the order, or running work, waits and the wait names the file.
4. **The heavy steps.** One line, printed once after the lanes:
   `Heavy steps (<work type>): <step>; ...; a builder runs each under lock.py run --name heavy.`,
   or `Heavy steps (<work type>): none.` The plan reads and writes no lock setting (`lock_slots`
   or any other) and writes no file.
5. `session.py next`, `claim`, `demand` and the conductor's queue do not change: `next` orders the
   free briefs as before (brief #665 names `session_plan.py` and its test only), and a lane never
   changes which briefs may run together, which pull requests may merge together, the capacity or
   the merge queue (SPEC-0034 rule 15).
6. No installed script is added, so `kit/manifest.json` and `agk.toml`'s test map do not change
   (`session_plan.py` is in `always_full`); `kit/hashes.json` is not edited; one fragment under
   `changelog.d/` records the change of the installed `session_plan.py`.

## Consequences

A project that declares no work type sees the same plan as today. A project with a declaration
reads each ready brief's lane and the heavy steps on two lines, and its first parallel builders
are offered briefs from different lanes; nothing else about who runs, waits or merges changes.

## Residual

- 2026-11-07: `Q-665-1`: rule 8 orders "the earlier phase first" but the format ties a kind to no
  phase by name (`mock` is a kind, `mocks` a phase). The build reads the phase rank from the
  split's `depends_on` depth; the next amendment of SPEC-0038 may name the rank or add a phase
  key to `brief_order` (due 2026-12-31).
- 2026-11-07: `Q-665-2`: where a brief without a kind sorts among kinded briefs of the same
  priority is not written; it follows them (due 2026-12-31).
