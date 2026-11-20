# ADR-0617: Clean layout build (g): the rehearsal's four figures are recorded, checked and gate any customer move

- Status: Proposed
- Date: 2026-11-19
- Deciders: maintainers
- Related: brief #1459, SPEC-0071 rules 11, 12 (g) and 13, ADR-0614, ADR-0616, Q-1459-1, Q-1459-2
- Requirements: REQ-078

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `agk.toml`

## Context

SPEC-0071 rule 11 says no customer project moves to the clean layout before the same five briefs have run on a sample
project, once installed and once clean, and the clean run's four figures are within 10% of the installed run's, written
to the spec's proof and accepted by the maintainers. Build (d) (ADR-0614) shipped `upgrade.py --clean-repo` refusing
without `--rehearsal` through a constant, `CLEAN_PROOF_HELD = False`, that build (g) was to replace. Nothing recorded the
figures and nothing checked them.

## Decision

1. The record is one `### Rehearsal record` table in SPEC-0071's Proof section: an `installed` and a `clean` row,
   each with its run dates (`YYYY-MM-DD` or `YYYY-MM-DD..YYYY-MM-DD`), its briefs (`#n` each) and the four figures of rule 11, in this
   order: lead time per brief in hours, tokens per merged pull request (`metrics.py --cost`), first-review pass rate in
   percent and failed checks. After it comes one line `Accepted: <YYYY-MM-DD> by the maintainers`. SPEC-0071 is
   Approved, so this build does not edit it (principle 6; `check_specs.py` refuses an Approved spec's change without a
   proposed-spec-amendments file, and the brief reserves none). The table is written there, with the run's figures,
   by the spec amendment that follows the runs, and the date by the maintainers (Q-1459-1).
2. `scripts/agk/rehearsal.py check [--root KIT_ROOT]` (kit-only, run from the plugin) reads that table. It fails (exit 1)
   when a run, its dates, its briefs or a figure is missing, when the two runs do not list the same five briefs, or when
   a clean figure is worse than the installed one by more than 10%. Higher is worse for every figure except the pass rate.
   The bound is 10% of the installed figure, so an installed figure of 0 failed checks allows 0 (Q-1459-2). It also
   fails when the acceptance line carries no date. Each line names the figure or the run, never a value. It reads one
   file and writes nothing.
3. `upgrade.py --clean-repo` replaces `CLEAN_PROOF_HELD` with `rehearsal.proof_held(kit_root)`. Without `--rehearsal` it
   refuses, naming the proof of SPEC-0071 rule 11, until the check passes on the plugin's own copy of the spec and the
   acceptance line is dated. The other refusals of ADR-0614 are unchanged and keep their order.

## Consequences

The clean layout stays closed to customer projects, as it is today, until a person runs the rehearsal and writes the
figures, and the maintainers date the line. This build runs no rehearsal: a cloud builder session cannot run a
conductor and two builders over five briefs on a sample project (Q-1459-1). The record is in the plugin's spec, so a
project's own copy cannot open its own gate. Installed projects, CI mode, personal mode and the kit's own repository are
unchanged, and no workflow, ruleset or required check changes. The brief names `docs/specs/` a protected class;
`config/protected-paths.txt` does not list it, and this build leaves the spec unchanged.

## Residual

- 2026-11-19: the four figures are not written; the rehearsal on a sample project with the conductor and two builders,
  and the maintainers' acceptance, are a person's work after this build (due 2027-01-31).
