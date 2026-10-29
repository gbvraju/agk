# Proposed spec amendments 93 (SPEC-0006, SPEC-0008; REQ-039)

Date: 2026-10-29 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). It is applied by
ADR-0165, and it changes `docs/specs/0006-doctor.md` and `docs/specs/0008-upgrade.md`. The conductor gave the number 93 for this
build on #293 (brief #285; verdict on 9f9f326, Q-285-3).

1. **SPEC-0006 rule 5.** A new row: `router-wake` | warn | a workflow of ROOT that holds a check of `required_checks` is not in
   the `workflows:` list of `workflow_run` in `.github/workflows/agk-route.yml`, or that list cannot be read (`ok` when the file
   is absent) | run `/agk:upgrade`, or add the workflow's name to the list (an ADR); until then a verdict comment or an edit of
   the title or description wakes the router.
2. **SPEC-0006 rule 8.** "compares, byte for byte" gains: "the router `.github/workflows/agk-route.yml` with its `workflow_run`
   list read as the kit's (the names are the project's, ADR-0165)".
3. **SPEC-0008 rule 7.** A new paragraph: "The router `.github/workflows/agk-route.yml` is a whole file whose `workflow_run`
   list is the project's. T is compared with that list read as N's. The file written is N with the list of ADR-0165 decision 1,
   and its line ends `(router workflows added: n)` when n is not zero."
4. **Tests (SPEC-0006 rule 14, SPEC-0008 rule 18).** `tests/kit/test_route_triggers.py` and the doctor case `router-unwoken`
   (the list, the doctor's check and the comparison), and `tests/kit_dev/test_upgrade_route_triggers.py` (upgrade and init).
   Their marker is `REQ-039`.
