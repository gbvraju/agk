# Proposed spec amendments 8 (SPEC-0004)

Date: 2026-10-15 (from `date -u`). Found while implementing SPEC-0004 (ADR-0012). Approved specs change only through a
proposal like this one (principle 6). Nothing here is applied; maintainers decide.

## SPEC-0004 (`docs/specs/0004-drift-audit.md`)

1. **Tests section, where the tests live.** Now: `tests/kit_dev/test_drift_audit.py` for rules 5-15, 18-20 and
   `tests/kit/test_workflow.py` style tests for the workflow. Proposed: the same ruling as amendments 7 for SPEC-0003:
   `tests/kit/test_drift_audit.py`, `tests/kit/drift_fixtures.py` and `tests/kit/test_drift_workflow.py`, so that
   installed checks ship with their tests (principle 4). The implementation already does this; the kit-only wiring
   tests are in `tests/kit_dev/test_drift_wiring.py`.
2. **Rule 21, the `gh` verbs.** Now: "the only `gh` verbs are `issue create` and `issue edit` (and `label create`)".
   Proposed: add the read-only `issue list`. The workflow must find the open audit issue to update it instead of
   opening a second one (rule 13), and the label filter of `issue list` is the way to do it. It writes nothing.
3. **Rules 13 and 23, the last line of the body.** Rule 13 says the body ends with the marker, rule 23 says it ends
   with the inactivity line. Proposed: the inactivity line is the last text line and the marker is the final line.
4. **Rule 15, the script's interface.** Add the options the workflow needs, so that the decision stays in the tested
   script: `--open-issues 'N N'` (the numbers of the open audit issues, used for D6 and for the action),
   `--print-action` (`create`, `update N` or `none`), `--print-title` (`agk drift audit YYYY-MM-DD`) and `--branch NAME`
   (the default branch; default from `agk.toml`).
5. **Rule 6, D1 granularity.** Proposed wording: a commit that fails yields one finding per touched protected class
   that no single ADR in the commit covers together (as the per-PR check prints one failure per class); the protected
   list used is the one at the commit's parent; the finding's subject is the first 12 characters of the commit id.
6. **Rule 9, D4 subjects.** Proposed wording: the subject of an overdue ADR or spec bullet is the file path; of an
   overdue register line, its source field; of a malformed register line, `docs/runs/residuals.md:LINE`. Only bullet
   lines (`- `) of the `## Open` section are register entries.
7. **Rule 7, the work tree.** D2, D4 and D5 read the work tree, and D1 and D3 read the history of the default branch;
   the audit is meant to run on a checkout of the default branch (as the workflow does). Proposed: say so in rule 7.

## Status

Applied 2026-10-15 on maintainers' instruction (final commit of PR #23). SPEC-0004 rules 6, 7, 9, 13, 15, 21
and 23 and its Tests section carry the proposed text (Q-K2-23: yes); nothing else in the spec changed.
