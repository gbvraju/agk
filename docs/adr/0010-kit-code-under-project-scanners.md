# ADR-0010: Kit code under project scanners

- Status: Accepted
- Date: 2026-10-15
- Deciders: maintainers
- Related: ADR-0008, ADR-0009
- Requirements: REQ-010

## Context

Finding (c) of the K2 live proof (`docs/runs/k2-live-proof.md`): a project that runs bandit, flake8, pylint or mypy over
`.` also scans the kit's code, and bandit alone reported 255 findings in the fork. The design note
`docs/runs/design-kit-lint-clean.md` measured five tools on a fresh init target and compared six options; the
maintainers ruled on 2026-10-15 (PR #15): the combination of documented exclude snippets and justified suppressions
(Q-ON-2), the snippets printed by init and adopt (Q-ON-3), flake8, pylint and mypy findings on kit code advisory
(Q-ON-4), and the code change as its own PR (Q-ON-5). This is that PR.

Protected classes: `scripts/agk/`, `tests/kit/`, `.claude/`, `kit/`, `tests/kit_dev/`. This PR changes all five.

## Decision

1. **Justified suppressions.** Every `import subprocess` and every `subprocess.run` call in `scripts/agk/`,
   `.claude/hooks/` and `tests/kit/` carries `# nosec B404 - <reason>` (import) or `# nosec B603 [B607] - fixed argument
   list, no shell` (call), with exactly the codes bandit reports for that line. A blanket `# nosec` is not allowed. A
   kit test (`tests/kit/test_scanner_hygiene.py`) checks this from the source text, so the rule holds without bandit.
2. **The four mypy findings are fixed in the code**, not silenced: a `Path` variable no longer reused as a `str` in
   `check_protected_changes.py`, and an annotation in `check_adrs.py`. No `type: ignore` is allowed in kit source; the
   same test checks it. Where mypy or bandit is installed, the test also runs it on kit source.
3. **Exclude snippets.** One source file, `kit/templates/scanner-excludes.txt` (kit-only, never installed), gives the
   bandit, flake8, pylint and mypy settings that exclude `scripts/agk`, `tests/kit` and `.claude/hooks`. Init and
   adopt print it after every run, after the ruleset (print only; neither writes it). The README quotes it in an
   "Existing scanners" section. Tests keep the printed text, the template and the README equal. pylint needs two keys
   (`ignore-paths` for the two directories, `ignore` for the hidden `.claude`), because `ignore-paths` does not reach a
   hidden directory in recursive mode (measured with pylint 4.1.3).
4. **Kit version** `0.4.2`: installed content changed (comments, annotations, a new test file).
5. **Not done.** The bare `assert` of the kit tests (bandit B101) stays: option 2 of the note was rejected. flake8,
   pylint and mypy style findings on kit code stay advisory (Q-ON-4).

## Consequences

- On a fresh init target bandit's non-assert findings go from 31 to 0; only B101 remains, all in `tests/kit`. With the
  printed bandit exclusion applied, bandit reports nothing.
- Kit source changes only by comments and variable names; no behaviour changes.
- A new subprocess call in kit source fails the kit test until it carries its codes and a reason.
- A project must still add the printed exclusions itself for its first scanner run to be green.

## Residual

- 2026-10-15: B101 (252 bare asserts in `tests/kit`) is still reported by an unexcluded bandit (due 2027-01-31); the plugin
  form at K3 removes the kit's files from the project tree.
- 2026-10-15: the pylint snippet depends on pylint's handling of hidden directories (verified with pylint 4.1.3 only)
  (due 2026-12-15).
- 2026-10-15: class naming in an ADR is still a substring match (ADR-0003 residual).
