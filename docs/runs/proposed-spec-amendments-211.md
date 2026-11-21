# Proposed spec amendments 211 (SPEC-0071; REQ-078)

Date: 2026-11-20 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0683 (brief #1603, reserved number 211), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0071-the-kit-runs-from-the-plugin-and-a-product-repository-keeps-only-its-project.md` (rule 2 and rule 12).
This file proposes the lines and does not edit the spec; they are applied word for word on a person's
`Approve: SPEC-0071` on the pull request that carries this file; no session posts it.

## What is on the default branch today

Read in the code by this session on main at deae41f5 (2026-11-20):

- SPEC-0071 rule 2: "In a clean project (`[kit] layout = "plugin"` in `agk.toml`, written only by the migration of
  rule 8):".
- `scripts/agk/init.py` and `scripts/agk/adopt.py` have no layout option, so a new or adopted project holds the kit's
  files in its first commit; `rehearsal.py check` reports the proof of rule 11 as not held.

## Items

1. **Rule 2, its opening clause replaced.** "In a clean project (`[kit] layout = "plugin"` in `agk.toml`, written by
   the migration of rule 8, or by `init` and `adopt` with `--layout plugin`, which write only the files that migration
   keeps, `execution = "local"` and the `[kit]` table, with the migration's refusals of rule 8 and rule 11):".
2. **Rule 12, one build added after (g).** "(h) `init` and `adopt` with `--layout plugin` (rule 2 as amendment 211
   reads), held by the proof of rule 11 as the migration is (brief #1603, ADR-0683). `Depends-on` (d)."
3. **Unchanged:** rules 1 and 3 to 11 and 13, the Tests, the Proof, the Residual, the Contexts and the Open questions.
