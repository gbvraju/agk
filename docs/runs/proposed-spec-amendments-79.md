# Proposed spec amendments 79 (SPEC-0032; REQ-039)

Date: 2026-10-26 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0143. The path: `docs/specs/0032-github-events-label-each-pr-people-approve-specs-a-red-branch-stops-work.md`.

1. **SPEC-0032 rule 2, the label from the checks.** The router judges the checks of a head by the latest run of each check name (the highest `id`, the later `started_at` on a tie) and the latest status of each context; an older run of a name is ignored. A latest run that is `cancelled` or failed is red; one that is still running is pending.
2. **SPEC-0032 rule 7, the default branch.** `branch_state` and the name and link of the failing check in the red-branch brief are read the same way.
3. **SPEC-0032 rules 2 and 7, skipped runs.** A run whose conclusion is `skipped` (the jobs that the `push` workflows start under the same names) is ignored while the name has a run that was not skipped; a name with only skipped runs keeps its newest, neither red nor pending.
