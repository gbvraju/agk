# ADR-0035: init and adopt install an empty residuals register when none exists, kit 0.17.1

- Status: Proposed
- Date: 2026-10-18
- Deciders: maintainers
- Related: ADR-0023, ADR-0031
- Requirements: REQ-009, REQ-010

Protected classes: `scripts/agk/`, `tests/kit_dev/`, `kit/`, `.claude-plugin/`

## Context

The facts document reads `residuals` from `docs/runs/residuals.md` and returns the string `unknown` when that file is absent
(SPEC-0009). A new repository made by `init` or `adopt` has no register, so its facts, its drift audit's register check and the product
report's At-risk and Needs-you sections all read `unknown` for residuals until someone creates the file. The pilot hit this.

## Decision

1. **A new template `kit/templates/residuals.md`** (an empty register: the title, one paragraph on the line format, an empty `## Open`
   heading and an empty `## Closed (not findings)` table) is installed at `docs/runs/residuals.md` by `init` and by `adopt`. The facts
   then read `[]` for the register, not `unknown`.
2. **Created only when absent.** Unlike the other templates, an existing `docs/runs/residuals.md` of any content is left as it is: it is
   not compared, so it is never a conflict, the run exits 0 and a second run changes nothing. A symlink at the path is refused, as for
   every file. The rule is one constant, `CREATE_ONLY`, in `scripts/agk/init.py`, used by both installers.
3. **SPEC-0001 rule 8 and SPEC-0002 rule 4 are amended** (`docs/runs/proposed-spec-amendments-22.md`, applied here).
4. **Tests** (`tests/kit_dev/test_init.py`, `test_adopt.py`): the register exists after init and after adopt with an `## Open` heading and
   no line; facts on a fresh install reads a list, with no entry from the register; an existing register is byte-for-byte unchanged by
   init and by adopt, and a second run changes nothing; a symlinked register is refused by init.
5. **Kit 0.17.1**: manifest (both template maps), hashes, plugin version.

## Consequences

- A new repository's report and facts show `nothing this week` for residuals instead of `unknown`.
- `agk upgrade` does not create template files: a target installed before 0.17.1 does not get the register from the upgrade (it prints
  `template-changed docs/runs/residuals.md (kit/templates/residuals.md)`, a note and no write). The pilot creates it by hand, from the
  template, in its own change; recorded as a residual.

## Questions

| Q | Question | Reading taken (conservative) |
| --- | --- | --- |
| Q-K4-166 | "Never overwrite": refuse (a conflict) or leave alone when the file exists and differs? | leave alone, exit 0: a project that keeps its own register must not be blocked from installing the kit; the file is never read for the comparison |
| Q-K4-167 | The kit version. | 0.17.1: one added template file, no behaviour of any check changes |
| Q-K4-168 | What the template says. | the format paragraph and the empty `## Open` and `## Closed (not findings)` sections only, with no date and no kit-specific line, so installed text stays neutral |

## Residual

- 2026-10-18: `agk upgrade` does not create the register in a target that lacks it; creating a missing template file at upgrade
  would need a rule for every template (due 2026-12-31).
