# Notes on SPEC-0006 (agk doctor)

Date: 2026-10-15 (from `date -u`). Overnight brief 2, item B. The spec was written Draft and set Approved on the maintainers'
rulings of 2026-10-15 (final commit of the pull request); nothing is implemented. No protected path is changed by this pull request.

## Decisions taken in the draft (each is a numbered rule)

- One script, `scripts/agk/doctor.py`, vendored into targets and run without the plugin; the plugin command only
  passes `--kit-root` (rules 1, 20).
- Read-only by construction: GET on four paths, no write, no token handled by the script, not run in CI (rules 2, 6).
- Three statuses, and `cannot-check` is never `ok` and never exits 0 (rules 3, 12).
- Nineteen checks, each with id, severity and printed fix (rule 5). The brief's six groups map to: ruleset and
  `governance` (nine ids), placeholder team (two), `origin-head`, drift audit (two), vendored files and version
  (three). The residual lines naming doctor: ADR-0001 (the ruleset and review settings, covered by the ruleset ids),
  SPEC-0001 (`@REPLACE-ME`, covered), ADR-0003 (colon-refspec deletion, see Q-K3-15).
- `--json` is included, for the reason in rule 11: the plugin command hands the result to a model and the tests assert
  on ids; the text is rendered from the same structure.
- The kit comparison needs the kit's copy: `--kit-root` is the only way to give it, and a plugin root is a kit root
  (SPEC-0005 rule 6). A repository checked without the plugin gets `cannot-check` (`no-kit-root`) for those checks,
  not `ok`.
- Fixtures are recorded `gh api` responses (rule 15); the `no-admin` case proves a 403 is not read as a missing
  ruleset.

## Response shapes the checks read (probed with GET on `gbvraju/agk`, 2026-10-15)

- Ruleset list: `id`, `name`, `target`, `enforcement`; no rules.
- Ruleset: `enforcement` `active`; `bypass_actors` `[]`; `conditions.ref_name.include` `["~DEFAULT_BRANCH"]`; rules
  `deletion`, `non_fast_forward`, `required_linear_history`, `pull_request` (`required_approving_review_count` 0,
  `dismiss_stale_reviews_on_push` true, `allowed_merge_methods` `["squash"]`), `required_status_checks` (context
  `governance`).
- Repository: `default_branch`, `allow_auto_merge`, `delete_branch_on_merge`, `permissions`.
- Workflow: `state` `active`. Other states are `(verify)`.
- `branches/main/protection` answers 404 "Branch not protected": the repository uses a ruleset, so the doctor does not
  read classic branch protection. A repository that uses classic protection instead of a ruleset gets
  `ruleset-missing` (ruled intended, Q-K3-17).

## Live proof (maintainers' step; not done)

Rule 18. It needs admin rights on `gbvraju/agk-sandbox` and changes its settings one at a time. Nothing was run
against the sandbox, `colorama` or any repository other than `gbvraju/agk`.

## Rulings (maintainers, 2026-10-15)

| Q | Ruling | Where in the spec |
| --- | --- | --- |
| Q-K3-12 | The ruleset elements are a minimum: stricter is `ok` (1+ approvals, a team approver, an extra check); merge methods `fail` only if `merge` is allowed; an extra rule is not a failure | rule 7, table row `ruleset-pull-request`, fixture `stricter-ok` |
| Q-K3-13 | Keep `repo-auto-merge`, `repo-delete-branch` and `default-branch-config`, all `warn` | rule 5 |
| Q-K3-14 | Confirmed: the doctor is not a check and does not run in CI; it runs `gh api` GET with the user's own `gh` and holds no credential | rule 2 |
| Q-K3-15 | No separate settings check: `.claude/settings.json` is verbatim, so a weakened deny list shows as `vendored-differs` on a version match (covers REQ-002 AC2) | rule 8, residual |
| Q-K3-16 | No exception list; the residual stays | residual |
| Q-K3-17 | Keep `ruleset-missing`; its fix adds "classic branch protection is not read; use a ruleset (ADR-0001 decision 3)" | rule 5 |

No question is open.

## Decisions-log rows (for the maintainers' log; not edited in this pull request)

| Date | Decision | Reason | Recorded in | By |
| --- | --- | --- | --- | --- |
| 2026-10-15 | SPEC-0006 drafted: one stdlib script, read-only, `cannot-check` never `ok`, `--json` kept | the plugin command and fixture tests read the structure; criterion b of ADR-0015 | `docs/specs/0006-doctor.md` | agent |
| 2026-10-15 | Q-K3-12 to Q-K3-17 ruled (ruleset elements are a minimum; settings covered by vendored-differs; no exception list); SPEC-0006 Approved | maintainers' rulings | `docs/runs/spec-0006-notes.md`, SPEC-0006 | reviewer |
