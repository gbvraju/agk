# Proposed spec amendments 182 (SPEC-0036; REQ-039)

Date: 2026-11-14 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0538 (brief #1272), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0036-whenever-a-pull-request-changes-state-the-project-publishes.md`. The conductor's fix list on #1274
reserved amendment 182. This file proposes the lines and does not edit the spec.

The sentence (brief #1272): "A router run by hand in local mode writes its pipeline document to a git-ignored file, so no
project working tree is left with an untracked `pipeline.json` that a builder could commit."

## Items

1. **Rule 2 gains one sentence after its first:** "With `AGK_PIPELINE_FILE` unset, a run writes the document as
   `.agk-pipeline.json` in the repository root, which the installed `.gitignore` block ignores; the workflow sets
   `AGK_PIPELINE_FILE` to its `pipeline.json` in the runner's temp folder, so the path of rule 5 is unchanged."
2. **Rule 5** (the artifact `agk-pipeline`, its `pipeline.json` and its retention) is unchanged.
3. **Tests.** `tests/kit/test_pipeline.py` (a) to (c) of brief #1272; the earlier tests of the file unchanged.
