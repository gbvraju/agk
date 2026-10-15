# SPEC-0006: agk doctor

- Status: Draft
- Owner: maintainers
- Requirements: REQ-002 (AC1), REQ-014 (to be added by ADR, see SPEC-0005)

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.
Open points are raised as `Q-K3-n` (this spec uses 12 to 29) in `docs/runs/spec-0006-notes.md`; a rule that depends on
one says so. Claude Code and GitHub facts not reconfirmed are marked `(verify)`. This spec is K3 criterion b of
ADR-0015. The GitHub response shapes used here were read (GET only) from `gbvraju/agk` on 2026-10-15.

## Rules

### What it is

1. **Command.** `python3 scripts/agk/doctor.py [--repo OWNER/REPO] [--kit-root PATH] [--api-dir DIR] [--json]
   [ROOT]`. Standard library only. ROOT is the work tree to inspect (default `.`). The script is vendored into every
   target (listed in `kit/manifest.json` `verbatim`) and runs without the plugin (SPEC-0005 rule 2). `/agk:doctor`
   runs this same script and passes `--kit-root` the plugin root (rule 20); it has no logic of its own.
2. **Read-only.** The script writes no file, makes no commit, runs no `git` command that changes anything, and calls
   `gh` only as `gh api` with `GET` on the four paths of rule 6. It never reads, prints or stores a token: it holds no
   credential, `gh` does (SPEC-0005 rule 11; Q-K3-14 asks whether this reading of that rule is right). It is not run by
   `make governance` or by any workflow: it needs the network and, for rulesets, rights a CI token lacks.
3. **Honest result.** Each check ends in exactly one status: `ok`, `fail`, or `cannot-check`. A check that could not
   read what it needs is `cannot-check` with the reason class (`gh-missing`, `gh-unauthenticated`, `no-admin`,
   `not-github`, `no-kit-root`, `version-mismatch`, `offline`, `bad-response`), never `ok`. A `cannot-check` is never turned into `ok` by
   any option.
4. **Messages name the setting or path class, never a value** (rule 6 of CLAUDE.md). A message says, for example,
   "ruleset: `required_approving_review_count` differs from ADR-0001 decision 3", not the found number. The printed
   fix may state the expected value, which is the kit's own text.

### The checks

Each check has a stable id, a severity (`error` or `warn`) and a printed fix. Order is the order below; the report
and the JSON keep it.

5. **Table of checks.**

   | Id | Severity | Fails when | Printed fix |
   | --- | --- | --- | --- |
   | `ruleset-missing` | error | no ruleset whose conditions include `~DEFAULT_BRANCH` (or the default branch's ref) | create the ruleset of ADR-0001 decision 3 (the report prints its elements) |
   | `ruleset-enforcement` | error | `enforcement` is not `active` | set the ruleset to Active |
   | `ruleset-bypass` | error | `bypass_actors` is not empty | remove every bypass actor |
   | `ruleset-target` | error | the ruleset does not target the default branch | target the default branch |
   | `ruleset-deletion` | error | no `deletion` rule | restrict deletions |
   | `ruleset-linear-history` | error | no `required_linear_history` rule | require linear history |
   | `ruleset-force-push` | error | no `non_fast_forward` rule | block force pushes |
   | `ruleset-pull-request` | error | no `pull_request` rule, or approvals differ from 0, or stale approvals are not dismissed on push, or the allowed merge methods are not exactly squash | require a pull request: 0 approvals, dismiss stale approvals, squash merge only |
   | `required-check-governance` | error | no `required_status_checks` rule with the context `governance` | require the status check `governance` |
   | `repo-auto-merge` | warn | repository setting `allow_auto_merge` is false (Q-K3-13) | allow auto-merge |
   | `repo-delete-branch` | warn | repository setting `delete_branch_on_merge` is false (Q-K3-13) | auto-delete head branches |
   | `placeholder-team-reviewers` | error | `config/reviewers.yaml` contains `@REPLACE-ME` | replace the placeholder with a real team or user, then `python3 scripts/agk/reviewers.py --codeowners --write` |
   | `placeholder-team-codeowners` | error | `.github/CODEOWNERS` contains `@REPLACE-ME` | same fix |
   | `origin-head` | warn | `refs/remotes/origin/HEAD` does not exist | `git remote set-head origin <default_branch>` (no network; `-a` asks the remote) |
   | `drift-workflow-file` | error | `.github/workflows/drift-audit.yml` is absent, or has no `schedule` with a `cron` | restore the file from the kit |
   | `drift-workflow-state` | error | the workflow's `state` is not `active` on GitHub | enable the workflow (GitHub disables scheduled workflows after inactivity `(verify)`) |
   | `kit-version` | warn | the installed kit's `kit_version` differs from `version` in `agk.toml` | run `/agk:upgrade` (SPEC-0008) |
   | `vendored-missing` | error | a file the installer for `mode` writes verbatim is absent | restore it from the kit |
   | `vendored-differs` | error | a vendored file differs byte for byte from the kit's copy, and the versions match | review `git log -p -- <path>`; restore the kit's copy, or record the deliberate edit in an ADR that names the path class (Q-K3-16) |
   | `default-branch-config` | warn | `default_branch` in `agk.toml` differs from the repository's `default_branch` (Q-K3-13) | set `default_branch` in `agk.toml` |

6. **The four reads.** `gh api repos/{o}/{r}` (default branch, `allow_auto_merge`, `delete_branch_on_merge`,
   `permissions`), `gh api repos/{o}/{r}/rulesets` (the list carries no rules), `gh api repos/{o}/{r}/rulesets/{id}` for
   each ruleset that targets the default branch (rules, `enforcement`, `bypass_actors`, `conditions`), and
   `gh api repos/{o}/{r}/actions/workflows/drift-audit.yml` (`state`). `{o}/{r}` comes from `--repo`, else from the URL of
   the remote `origin` (read from `.git/config` or `git remote get-url origin`); a host other than github.com is
   `not-github`. Whether a non-admin can read a ruleset's rules is `(verify)`; a 403 or 404 on a ruleset read is
   `cannot-check` (`no-admin`), and never `ruleset-missing`.
7. **Strictness.** ADR-0001 decision 3 says the ruleset "is exactly" its list. Any element absent is `fail` with the
   id above. An element that is present and stricter than decision 3 (for example one required approval) is also
   `fail` for `ruleset-pull-request` with the message "differs from ADR-0001 decision 3", because the check is of
   equality (Q-K3-12 asks whether stricter should be a `warn`). An extra rule not named in decision 3 is not a
   failure.
8. **The kit comparison.** With `--kit-root`, the script reads `kit/manifest.json` in it and compares, byte for byte,
   each `verbatim` path that the installer for the target's `mode` writes (the `verbatim` list minus the files
   SPEC-0001 rule 3 keeps kit-only for `init`; minus the `adopt.skip` set, and for `adopt` the marked blocks compared
   inside their markers only) with the file of the same relative path in the kit root. `templates` and `rendered` files
   are not compared: the target owns them, and CODEOWNERS is checked by `reviewers.py --check-codeowners`. The
   comparison runs only when the kit's `kit_version` equals `version` in `agk.toml` (SPEC-0005 rule 3); otherwise
   `kit-version` is the finding and `vendored-differs` and `vendored-missing` are `cannot-check` (`version-mismatch`). Without `--kit-root` the three kit checks
   are `cannot-check` (`no-kit-root`).
9. **Local-only mode.** `--api-dir DIR` replaces every `gh` call with the recorded JSON files of rule 15 and is the
   mode tests use. Nothing else changes the source of the reads.

### Output

10. **Text report.** Lines on stdout, no color, no timestamp, no path outside ROOT:
    `agk doctor <kit_version or "unknown">`, then per check `<STATUS> <id> <severity> <message>` (STATUS is `ok`,
    `FAIL` or `??`) and, for `FAIL` and `??`, an indented `fix: <fix>` line (for `??` the line starts `to check:`
    and names what is needed, such as `gh auth login` or admin rights). The last line is
    `summary: <n> ok, <n> fail, <n> cannot-check`. The same inputs give a byte-identical report.
11. **`--json`.** One JSON object on stdout with `doctor` (the version), `checks` (an array, in order, of `id`,
    `severity`, `status`, `reason` for `cannot-check`, `message`, `fix`) and `summary`; keys sorted, no timestamp. The
    reason for the option: `/agk:doctor` hands the result to a model to explain, and the fixture tests assert on ids
    and statuses, so both read the structure instead of parsing text; the text report is rendered from the same
    structure. The two outputs carry the same findings (a test compares them).
12. **Exit codes.** 0 only when every check is `ok`. 1 when at least one `error`-severity check is `fail`. 4 when no
    `error` check failed but a `warn` check failed or any check is `cannot-check`. 2 usage. 3 I/O error. A report
    with `cannot-check` never exits 0.
13. **Refusals.** `ROOT` not a directory, a missing `agk.toml` (the target is not an agk target: exit 1, "agk.toml
    missing", no checks), and an `--api-dir` file that is not JSON (exit 3, names the file class) are refusals; each
    writes nothing.

### Tests and proof

14. **Tests, no network.** `tests/kit/test_doctor.py` (installed with the kit, as the script is): `gh` is never
    called; a test that puts a `gh` executable on `PATH` fails if it is run (it records any call).
15. **Fixture set.** `tests/kit/fixtures/doctor/<case>/`: `api/repo.json`, `api/rulesets.json`, `api/ruleset-<id>.json`,
    `api/workflow-drift-audit.json` recorded with `gh api` from a real repository (owner and ids changed; the
    responses carry no secret), and a `tree/` of the few local files a case needs. One case per misconfiguration:
    `ok` (reports none), `no-ruleset`, `weak-enforcement`, `bypass-actor`, `no-deletion`, `no-linear-history`,
    `no-force-push-block`, `approvals-required`, `merge-methods`, `no-governance-check`, `placeholder-reviewers`,
    `placeholder-codeowners`, `no-origin-head`, `drift-disabled`, `drift-no-schedule`, `version-mismatch`,
    `vendored-edited`, `vendored-missing`, `auto-merge-off`, `no-gh` (every remote check `cannot-check`),
    `no-admin` (403 on the ruleset read: `cannot-check`, not `no-ruleset`). Each case asserts the ids that fail and
    only those.
16. **A correctly configured repository reports none.** The `ok` case exits 0 with no `fail` and no `??`; the
    sandbox in the live proof does the same (rule 18).
17. **Determinism.** A test runs each case twice and compares the text and the JSON byte for byte.
18. **Live proof (criterion b of ADR-0015; a maintainers' step, not done by an agent).** On `gbvraju/agk-sandbox`
    (admin rights, `gh auth login`): run `python3 scripts/agk/doctor.py --kit-root <kit>`; expect exit 0. Then, one at a
    time, make each misconfiguration of the fixture set in the repository settings (ruleset removed, bypass actor
    added, `governance` removed from the required checks, `@REPLACE-ME` put back, `origin/HEAD` deleted with
    `git remote set-head origin --delete`, the drift-audit workflow disabled), run the doctor, expect exactly the
    matching id to fail, and restore the setting. The settings changes, the commands and the outputs are recorded in
    `docs/runs/`. Until then criterion b is open.
19. **Protected classes.** The implementation adds `scripts/agk/doctor.py`, `tests/kit/test_doctor.py` and fixtures
    (all under classes already protected: `scripts/agk/`, `tests/kit/`) and lists `doctor.py` in
    `kit/manifest.json`; the PR carries an ADR that names each class. The skill `skills/doctor/SKILL.md` is under the
    classes SPEC-0005 rule 20 adds.
20. **Plugin command.** `skills/doctor/SKILL.md` runs `python3 scripts/agk/doctor.py --kit-root "${CLAUDE_PLUGIN_ROOT}"`
    (the variable is `(verify)`, SPEC-0005 residual), shows the report, and explains each `FAIL` and `??` in plain
    words. It does not run the printed fix. A test reads the skill and fails if it names a write verb other than the
    script call.

## Tests

- Rules 1-4, 12, 13: `tests/kit/test_doctor.py`, marker `REQ-002 AC1`.
- Rules 5-9, 15, 16: the same file over the fixture cases, marker `REQ-002 AC1`.
- Rules 10, 11, 17: the same file, marker `REQ-002 AC1`.
- Rule 14: the `PATH` stub test, marker `REQ-002 AC1`.
- Rule 20: `tests/kit_dev/test_distribution.py`, marker `REQ-014 AC2`.
- Rule 18: a record in `docs/runs/`, checked by the maintainers, not by a test.

## Residual

- 2026-10-15: whether a non-admin can read a ruleset's rules, and the exact `state` values of a
  disabled workflow (`disabled_manually`, `disabled_inactivity`), are `(verify)`; the code treats any `state` other
  than `active` as `fail` and any 403 or 404 on a ruleset as `cannot-check` (due 2026-11-30).
- 2026-10-15: ADR-0003's open point (colon-refspec branch deletion has no deny rule) is not a doctor check in this
  draft; the ruleset's `deletion` rule already covers the default branch (Q-K3-15) (due 2026-12-15).
- 2026-10-15: the doctor sees GitHub settings as they are when it runs; it cannot say who changed one. The audit log
  is not read (due 2026-12-31).
- 2026-10-15: a legitimate local edit of a vendored file is reported on every run until it is reverted or the kit
  copy changes; there is no allow-list (Q-K3-16) (due 2026-11-30).
