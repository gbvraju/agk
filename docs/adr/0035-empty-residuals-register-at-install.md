# ADR-0035: init, adopt and upgrade install an empty residuals register when none exists, kit 0.17.1

- Status: Accepted
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
3. **`agk upgrade` creates it too** (the maintainers' verdict on the first head): every `CREATE_ONLY` path that the target lacks is created
   from the present kit's template (`create docs/runs/residuals.md (absent)`; the dry run lists it the same way), by the same rule: only
   when absent, never read or rewritten when it exists, a symlink or a non-file refused (exit 1, nothing written). The `template-changed`
   note for that path is no longer printed. A second run says `nothing to do`.
4. **SPEC-0001 rule 8, SPEC-0002 rule 4 and SPEC-0008 rule 7 are amended** (`docs/runs/proposed-spec-amendments-22.md`, applied here).
5. **Tests** (`tests/kit_dev/test_init.py`, `test_adopt.py`, `test_upgrade.py`): the register exists after init and after adopt with an `## Open` heading and
   no line; facts on a fresh install reads a list, with no entry from the register; an existing register is byte-for-byte unchanged by
   init and by adopt, and a second run changes nothing; a symlinked register is refused by init; upgrade creates an absent register in an init and in an adopt target, lists it in a dry run, leaves any
   existing one untouched (bytes and modification time), refuses a symlink, and says `nothing to do` the next time.
6. **Kit 0.17.1**: manifest (both template maps), hashes, plugin version.

## Consequences

- A new repository's report and facts show `nothing this week` for residuals instead of `unknown`.
- A target installed before 0.17.1 gets the register at its next `agk upgrade`; the pilot needs no hand step.

## Questions

| Q | Question | Reading taken (conservative) |
| --- | --- | --- |
| Q-K4-166 ruled | "Never overwrite": refuse (a conflict) or leave alone when the file exists and differs? | leave alone, exit 0: a project that keeps its own register must not be blocked from installing the kit; the file is never read for the comparison |
| Q-K4-167 ruled | The kit version. | 0.17.1: one added template file, no behaviour of any check changes |
| Q-K4-168 ruled | What the template says. | the format paragraph and the empty `## Open` and `## Closed (not findings)` sections only, with no date and no kit-specific line, so installed text stays neutral |

## Residual

None. The gap recorded in the first head (upgrade does not create a missing template file) is closed by decision 3.
