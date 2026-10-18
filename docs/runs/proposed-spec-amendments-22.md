# Proposed spec amendments 22 (SPEC-0001 and SPEC-0002; found by the pilot, Day 14 E1c)

Date: 2026-10-18 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). The paths:
`docs/specs/0001-agk-init.md`, `docs/specs/0002-agk-adopt.md`.

**Applied by ADR-0035** (2026-10-18) on the maintainers' brief: in a new repository the facts read the residuals register as `unknown`,
because no register exists.

1. **SPEC-0001 rule 8, the template set.** Adds `docs/runs/residuals.md`, an empty register with its `## Open` heading and no line.
   Unlike the other templates it is *created only when absent*: an existing file of any content is left as it is and is never a
   conflict (the run still exits 0, and a second run changes nothing).
2. **SPEC-0002 rule 4, the created set.** The same file, with the same exception.
