# Proposed spec amendments 82 (SPEC-0007, SPEC-0010; REQ-039)

Date: 2026-10-26 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0146. The paths: `docs/specs/0007-metrics.md`, `docs/specs/0010-proof-checks.md`.

1. **SPEC-0007 rule 13, governance on a status-only final commit.** The first step of the job after the setup decides with `scripts/agk/status_only.py --parent-governance` (the decision of SPEC-0010 rule 17) whether the head is a status-only final commit whose parent passed the full governance run and whose base has not moved; then the install of the tooling, the lint, the tests of the checks, the project tests and the kit-tests check are skipped, every other check runs, the job and its name are unchanged, and the job summary names the parent run.
2. **SPEC-0010 rule 17, one decision.** The status-only decision is one script for proof and for governance: `--parent-proof` or `--parent-governance` gives the conclusion of the check on the parent; the other conditions are the same.
