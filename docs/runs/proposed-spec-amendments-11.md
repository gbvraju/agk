# Proposed spec amendments 11 (SPEC-0006)

Date: 2026-10-15 (from `date -u`). Found while building SPEC-0006 (day 9, item C; ADR-0017). Approved specs change only
through a proposal like this one (principle 6). Nothing here is applied; until the maintainers apply it, the code is ahead
of the Approved text of the rules below.

**Applied 2026-10-16 (from `date -u`) on the maintainers' instruction (day 10, item B):** items 1 to 11 are in `docs/specs/0006-doctor.md` (item 1 is the count in `docs/runs/spec-0006-notes.md`, now twenty; item 11 is the wording of rule 13).

## SPEC-0006 (`docs/specs/0006-doctor.md`)

1. **Rule 5, the number of checks.** The table has twenty rows (the notes said nineteen). Proposed: none to the table; fix the
   notes' count.
2. **Rule 3, a reason class `no-ruleset`.** When no ruleset targets the default branch, the other ruleset checks cannot be read
   from a ruleset that does not exist. Built: they are `cannot-check` with the reason `no-ruleset`, so a case "asserts the
   ids that fail and only those" (rule 15): `ruleset-missing` alone, or `ruleset-target` alone. Proposed: add `no-ruleset`
   to the reason classes of rule 3.
3. **Rule 5, `ruleset-target` versus `ruleset-missing`.** Built: `ruleset-missing` fails when no branch ruleset exists;
   `ruleset-target` fails when branch rulesets exist and none includes the default branch (`~DEFAULT_BRANCH` or
   `refs/heads/<default>`). Proposed: say so in the table.
4. **Rule 7, several rulesets and active rulesets only.** Built: rulesets that target the default branch are read
   together, and only rulesets whose `enforcement` is `active` provide protection. `ruleset-enforcement` fails when no
   candidate is active. `ruleset-bypass` and every element check (`ruleset-deletion`, `ruleset-linear-history`,
   `ruleset-force-push`, `ruleset-pull-request`, `required-check-governance`) read the active candidates only; an element
   present only on a disabled or evaluate-mode ruleset does not count, and a bypass actor on a disabled ruleset is not a
   bypass. With no active candidate, `ruleset-bypass` and every element check fail. Proposed: say so in rule 7.
4b. **Rule 5 (`ruleset-target`), what targets the default branch.** Built: a ruleset targets the default branch when
   `conditions.ref_name.include` has `~DEFAULT_BRANCH`, `~ALL` or `refs/heads/<default>`, and `conditions.ref_name.exclude`
   has none of `~DEFAULT_BRANCH`, `~ALL` and `refs/heads/<default>`. Proposed: replace "includes `~DEFAULT_BRANCH` (or the
   default branch's ref)" with this.
5. **Rule 6, empty list and permissions.** Built: an empty ruleset list is `ruleset-missing` only when `permissions.admin` in the
   repository read is not false; with `permissions.admin` false it is `cannot-check` (`no-admin`). A missing
   `allow_auto_merge` or `delete_branch_on_merge` key (shown only to users with push access) is `cannot-check` (`no-admin`).
   An omitted `allowed_merge_methods` counts as all methods allowed `(verify)`. Proposed: add these three sentences.
6. **Rule 3, `bad-response` for unreadable local input.** An unreadable `config/reviewers.yaml`, `.github/CODEOWNERS`, a
   directory that is not a git work tree for `origin-head`, a kit without a manifest, or a missing `mode` or `version` in
   `agk.toml` is `cannot-check` (`bad-response`). Proposed: say so.
7. **Rule 6, the read of `origin`.** Built: `git config --get remote.origin.url` (read-only) when `--repo` is absent; a URL whose
   host is not github.com, or no `origin`, gives `not-github`. Proposed: replace "`.git/config` or `git remote get-url`".
8. **Rule 9 and 15, the fixture layout and error bodies.** Built: `tests/kit/fixtures/doctor/ok/` holds `api/` (the four
   responses, sanitized from the real ones of `gbvraju/agk`: names and ids changed, only the keys the script reads kept),
   `tree/` (local files), `kit/` (a mini kit with a manifest and two files) and `case.json`; every other case holds only the files
   that differ plus a `case.json` (`fail`, `cannot`, `delete`, `origin_head`). A recorded error body `{"message", "status"}` in an
   API file stands for that HTTP error. Vendored stand-ins are `.txt` files. Proposed: replace the layout sentence of rule 15.
9. **Rule 15, cases.** Added: `wrong-target`, `no-dismiss-stale`, `delete-branch-off`, `default-branch-mismatch`,
   `no-admin-empty-list` (one per check or branch of a check not in the list); `approvals-required` and `merge-methods` of the
   Draft list became `stricter-ok` and `merge-commits-allowed` by the rulings. `no-gh` is tested in live mode with no `gh`
   on `PATH` (and `gh` stubs for unauthenticated, 403, offline and bad output), not as a fixture directory. Proposed: list them.
10. **Rule 14, the real kit.** The tests of `tests/kit/` build a mini kit because the kit's `init.py` is not installed in targets. The
    comparison against this repository's own checkout is `tests/kit_dev/test_doctor_wiring.py`. Proposed: say so.
11. **Rule 13, refusal wording.** Built: `refused: agk.toml missing (path class agk.toml); this is not an agk target` (exit 1) and
    `refused: ... api-dir` (exit 3), printed on stdout. Proposed: none beyond the wording.

## Question (answered)

None.
