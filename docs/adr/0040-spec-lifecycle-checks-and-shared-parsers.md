# ADR-0040: spec lifecycle checks (SPEC-0013 rules 23 to 26) and the shared parsers, kit 0.20.0

- Status: Proposed
- Date: 2026-10-18
- Deciders: maintainers
- Related: ADR-0021, ADR-0037, ADR-0039
- Requirements: REQ-020

Protected classes: `.github/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `kit/`, `.claude-plugin/`

## Context

SPEC-0013 (Approved) is built in four pull requests, as measured: G1 (this one) the lifecycle checks of `check_specs.py` and the shared parsers
(rules 23 to 26); G2 `/agk:ruleset` (rules 19 to 22, after the sandbox proof of Q-K4-101); G3 the architect role, its guard and the templates
(rules 6 to 17); G4 `/agk:start` and the existing-codebase path (rules 1 to 5). Rules 18 and 28 are the product report's At-risk line (an amendment
of SPEC-0011) and the maintainers' proof of criterion g; neither is in G1.

## Decision

1. **Rule a (SPEC-0013 rule 23).** `check_specs.py --body FILE|-` reads the pull request body. For an implementation pull request (its diff touches a
   path outside `docs/` and `.github/ISSUE_TEMPLATE/`) each `REQ-nnn` on the `Advances:` line must be named by the `Requirements:` line of a spec
   whose Status is `Approved` in the work tree; otherwise `FAIL specs: REQ-nnn: no Approved spec names it`. A requirement that no spec names and an
   ADR names (any status) is exempt (Q-K4-103 and Q-K4-104 ruled). Without a body, or with an empty one, the rule prints a notice and is skipped.
2. **Rule b (rule 24).** A spec whose Status is `Approved` at the head and whose status line is added or changed in the diff has no open `Q-` id: an id
   that starts a table row or a list item (`| Q-...`, `- Q-...`) in the spec or its notes file and has neither a row starting with the id in the notes'
   `## Rulings` section (a heading that continues, such as `## Rulings (maintainers, 2026-10-16)`, counts) nor a decisions-log row with `<id> ruled`.
   `FAIL specs: SPEC-nnnn: Q-... has no ruling`. Specs already Approved and unchanged in status are not re-checked (Q-K4-105 and Q-K4-106 ruled).
   Measured on this repository's eleven Approved specs at this commit: none has an open id.
3. **The shared parsers (rule 25).** `common.find_questions(root)` (ids, files, `ruled`, `named_in_log`; `None` when the decisions log is absent) is extracted
   from `facts.py`, which calls it and adds `open_in`; `common.next_free_ids(root, ref)` is extracted from `intake.py`, which calls it. Behaviour-preserving:
   the `questions` section of every facts golden is byte-identical (the existing goldens pass unchanged). SPEC-0009 rules 16 and 17 are amended
   (`docs/runs/proposed-spec-amendments-15.md`, item 2, applied here).
4. **The workflow** (`.github/workflows/governance.yml`): a step `PR body file` writes the pull request body (empty on a push) to `$RUNNER_TEMP/pr-body.md`
   before the checks, and `check_specs` runs with `--body "$RUNNER_TEMP/pr-body.md"`. The step names of the nine checks are unchanged. `agk.mk` runs
   `check_specs.py` without a body, so `make governance` prints the notice and skips rule a locally, as the other diff checks do outside CI.
5. **Tests** (`tests/kit/test_check_specs_lifecycle.py`, installed; `test_workflow.py`): rule a for a docs-only pull request, the issue-form-only change
   and a workflow change, an Approved spec, a Draft spec only, a Draft spec with an ADR, no spec and an ADR, no spec and no ADR, two requirements with
   one failing, no body, an empty body, a body file; rule b for an open id, a `## Rulings` row, a log row, a mention in prose, a notes-file table row,
   `Q-AB-10` against `Q-AB-1`, an unchanged Approved spec, a new spec added Approved, an intake `Q-S` id; both shared functions. No test uses the network.
   `tests/kit_dev/test_init.py` runs the CI steps with `RUNNER_TEMP` set to a directory holding an empty body file.
6. **Kit 0.20.0**: manifest (the new installed test), hashes, plugin version.

## Consequences

- From this change, a pull request of this repository that changes anything outside `docs/` must advance a requirement of an Approved spec (or one that
  predates specs), and no spec is set Approved while a question in it or its notes is unruled. The pilot receives both at its next `agk upgrade`.

## Residual

- 2026-10-18: rule a reads the work tree, so a pull request that approves its spec and builds from it in one change passes; the review is where that is judged (due 2026-12-31).
