# Notes on SPEC-0006 (agk doctor)

Date: 2026-10-15 (from `date -u`). Overnight brief 2, item B. The spec is Draft; nothing is implemented. The maintainers
set it Approved. No protected path is changed by this pull request.

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
  `ruleset-missing`; Q-K3-17 asks whether that is intended.

## Live proof (maintainers' step; not done)

Rule 18. It needs admin rights on `gbvraju/agk-sandbox` and changes its settings one at a time. Nothing was run
against the sandbox, `colorama` or any repository other than `gbvraju/agk`.

## Open

- **Q-K3-12.** Should a ruleset element stricter than ADR-0001 decision 3 (one required approval, say) be `fail` or
  `warn`? Draft: `fail` for `ruleset-pull-request` (decision 3 says "exactly"). Conservative reading kept.
- **Q-K3-13.** Three checks go beyond the brief's list: `repo-auto-merge` and `repo-delete-branch` (decision 3 lists
  them as repository settings) and `default-branch-config`. Keep, or drop? Draft: kept as `warn`.
- **Q-K3-14.** The script runs `gh api` itself with the user's own `gh`. SPEC-0005 rule 11 says the network is used "by
  the command with the user's own `gh`, never by a script that holds a credential", and CLAUDE.md says "no network
  calls in checks". The draft reads both as met (the script holds no credential; the doctor is not a check and not in
  CI). If not, the alternative is that the command fetches and the script reads `--api-dir` only, which makes
  `python3 scripts/agk/doctor.py` without the plugin useless for the GitHub checks.
- **Q-K3-15.** ADR-0003's residual (colon-refspec deletion of branches) and REQ-002 AC2 (settings deny force-push and
  reset): should the doctor check that `.claude/settings.json` contains named deny entries? That needs the maintainers
  to fix the list of required entries. Draft: no such check.
- **Q-K3-16.** A deliberately edited vendored file is reported on every run (`vendored-differs`). Allow a declared
  exception? Any list of exceptions is a second source of truth next to `agk.toml` (SPEC-0005 rule 3, no lock file).
  Draft: no exception.
- **Q-K3-17.** A repository protected by classic branch protection instead of a ruleset: `ruleset-missing` (draft), or
  a separate check that reads `branches/{b}/protection`? ADR-0001 decision 3 names a ruleset only.

## Decisions-log rows (for the maintainers' log; not edited in this pull request)

| Date | Decision | Reason | Recorded in | By |
| --- | --- | --- | --- | --- |
| 2026-10-15 | SPEC-0006 drafted: one stdlib script, read-only, `cannot-check` never `ok`, `--json` kept | the plugin command and fixture tests read the structure; criterion b of ADR-0015 | `docs/specs/0006-doctor.md` | agent |
| 2026-10-15 | Q-K3-12 to Q-K3-17 opened | the draft chose the conservative reading of each | `docs/runs/spec-0006-notes.md` | agent |
