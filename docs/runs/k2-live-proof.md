# K2 live proof (SPEC-0002 rules 19-20)

Source of the fork facts: overnight brief 1 from the maintainers, who ran the proof on the fork and verified it
(including the upstream `lint_python` state). The agent that wrote this record has no access to the fork and did not
re-check any of it; kit facts were checked in this repository.

## Record

- Kit: agk at **d64c42c** (`main`, PR #13 merged; PRs #1-#13).
- Target: `gbvraju/colorama`, a fork of `tartley/colorama` (BSD-3-Clause, default branch `master`).
- **Fork PR #1, adopt:** `agk adopt` installed 47 files. The only existing file that changed was `.gitignore`, by
  the marked block. The checks were green, and colorama's own `Test` matrix was green. `lint_python` was red, and had
  been red upstream since 2026-05-13 (verified by the reviewer), so it is not caused by adoption.
- **Fork PR #2, first governed change:** ADR-0002, requirement REQ-101 and the test
  `colorama/tests/trace_test.py` carrying its marker.
- **Reviewer's negative test:** removing ADR-0002 from PR #2 made `check_protected_changes` fail, naming
  `docs/requirements.md`.
- Safety rule 20 held as reported: every PR targeted `gbvraju/colorama` `master`; nothing was opened on
  `tartley/colorama`.

## Findings

- **(a) Missing `refs/remotes/origin/HEAD`.** A session clone may lack `refs/remotes/origin/HEAD`, and then adopt
  refuses because it cannot tell the default branch (SPEC-0002 rule 7). The refusal should name the fix
  (`git remote set-head origin --auto`). Follow-up: overnight item E.
- **(b) `reviewers.py --codeowners` prints to stdout.** Writing `.github/CODEOWNERS` (or the marked block in adopt
  mode) needs a redirect that agents may not be allowed to run. Follow-up: overnight item E (`--write`).
- **(c) Project-wide linters scanning `.` flag kit files.** bandit over the adopted fork reported 255 findings: 224
  `B101` asserts, and subprocess findings `B603`, `B607`, `B404`, in `tests/kit`, `scripts/agk` and the stop hook;
  the same bandit run on colorama `master` before adoption reported 0. Adoption is zero-touch for product files, but
  a project that scans `.` sees kit files. Follow-up: design note, overnight item B (no code change tonight).

## Result

SPEC-0002 rules 19 and 20 are met on a real codebase: no product file was modified, the project's existing CI was
unchanged by adoption, `governance` was green, and a small traced change passed through the kit's checks.
