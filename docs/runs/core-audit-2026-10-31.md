# Core audit 2026-10-31

This page is evidence for #278, not a decision: it lists what the kit's checks and rules refused in the history read below. It changes no rule and no check; a person files any follow-up.

Written by `python3 scripts/agk/core_audit.py --write` on 2026-10-31 (the date from `date -u`).

```text
agk core audit, the whole history, read on 2026-10-31
pull requests: 286 (check runs unreadable: 3, comments unreadable: 0)
Unread pages:
  #1 job
  #2 combined step
  #32 combined step

Governance checks (pull requests whose governance run failed on the check):
  Paused: cannot-check
  Status-only final commit: cannot-check
  Latest full run: at least 8
  PR states and open pull requests: cannot-check
  check_protected_changes: at least 42
  check_requirements: cannot-check
  check_adrs: at least 1
  check_numbers: cannot-check
  check_specs: at least 6
  check_neutrality: cannot-check
  check_build_state: cannot-check
  check_kit_tests: cannot-check
  check_design: cannot-check
  reviewers --check: cannot-check
  reviewers --check-codeowners: cannot-check
  check_pr_mode: at least 10
  check_final_clearance: at least 1
  Release check: at least 1
  PR body shape: at least 9
  Lint: at least 6
  Tests of the checks: at least 30
  Project tests: cannot-check
  Secret scan: at least 20

Session rules (verdicts that cite the rule):
  session rule 1: 1
  session rule 2: 0
  session rule 3: 0
  session rule 4: 0
  session rule 5: 0
  session rule 6: 0
  session rule 7: 1
  session rule 8: 0
  session rule 9: 0
  session rule 10: 0
  session rule 11: 0
  session rule 12: 0
  session rule 13: 2
  session rule 14: 1
  session rule 15: 0
  session rule 16: 0
  session rule 17: 1
  session rule 18: 0
  session rule 19: 0
  session rule 20: 0
  session rule 21: 1
  session rule 22: 1
  session rule 23: 0
  session rule 24: 1
  session rule 25: 0
  session rule 26: 0
  session rule 27: 1
  session rule 28: 1
  session rule 29: 1
  session rule 30: 3
  session rule 31: 0
  session rule 32: 0
  session rule 33: 0

Spec rules (verdicts that cite the rule):
  SPEC-0006 rule 5: 2
  SPEC-0006 rule 8: 3
  SPEC-0007 rule 8: 1
  SPEC-0008 rule 7: 2
  SPEC-0008 rule 13: 2
  SPEC-0009 rule 8: 1
  SPEC-0009 rule 14: 1
  SPEC-0011 rule 15: 1
  SPEC-0015 rule 4: 1
  SPEC-0020 rule 6: 1
  SPEC-0020 rule 8: 2
  SPEC-0021 rule 1: 1
  SPEC-0021 rule 4: 1
  SPEC-0021 rule 5: 1
  SPEC-0021 rule 6: 1
  SPEC-0021 rule 8: 1
  SPEC-0022 rule 1: 1
  SPEC-0022 rule 2: 1
  SPEC-0022 rule 4: 1
  SPEC-0024 rule 4: 1
  SPEC-0025 rule 3: 1
  SPEC-0025 rule 5: 2
  SPEC-0025 rule 10: 1
  SPEC-0026 rule 1: 1
  SPEC-0028 rule 2: 2
  SPEC-0029 rule 4: 1
  SPEC-0029 rule 5: 1
  SPEC-0029 rule 6: 2
  SPEC-0029 rule 7: 3
  SPEC-0029 rule 9: 1
  SPEC-0030 rule 4: 1
  SPEC-0032 rule 1: 1
  SPEC-0032 rule 3: 2
  SPEC-0032 rule 4: 1
  SPEC-0032 rule 5: 2
  SPEC-0032 rule 6: 1
  SPEC-0032 rule 7: 3
  SPEC-0032 rule 13: 1
  SPEC-0033 rule 1: 1
  SPEC-0034 rule 4: 1
  SPEC-0034 rule 5: 2
  SPEC-0034 rule 6: 2
  SPEC-0034 rule 11: 1
  SPEC-0034 rule 7b: 1
  SPEC-0034 rule 7c: 1
  SPEC-0035 rule 1: 2
  SPEC-0035 rule 3: 1
  SPEC-0035 rule 4: 1
  SPEC-0035 rule 8: 1
  SPEC-0036 rule 1: 2

Never fired in the period:
  checks: none
  session rules: 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 15, 16, 18, 19, 20, 23, 25, 26, 31, 32, 33
  spec rules:
    SPEC-0001: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24
    SPEC-0002: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20
    SPEC-0003: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23
    SPEC-0004: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23
    SPEC-0005: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21
    SPEC-0006: 1, 2, 3, 4, 6, 7, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20
    SPEC-0007: 1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24
    SPEC-0008: 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25
    SPEC-0009: 1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25
    SPEC-0010: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25
    SPEC-0011: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 18, 19, 20, 21, 22, 23
    SPEC-0012: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19
    SPEC-0013: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30
    SPEC-0014: 1, 2, 3, 4, 5
    SPEC-0015: 1, 2, 3, 5, 6, 7, 8
    SPEC-0016: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
    SPEC-0017: 1, 2, 3, 4, 5, 6, 7, 8, 9
    SPEC-0018: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
    SPEC-0019: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
    SPEC-0020: 1, 2, 3, 4, 5, 7, 9, 10
    SPEC-0021: 2, 3, 7, 9, 10, 11, 12
    SPEC-0022: 3, 5, 6, 7, 8, 9, 10, 11, 12
    SPEC-0023: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12
    SPEC-0024: 1, 2, 3, 5, 6, 7, 8
    SPEC-0025: 1, 2, 4, 6, 7, 8, 9, 11
    SPEC-0026: 2, 3, 4, 5, 6, 7, 8, 9, 10
    SPEC-0027: 1, 2, 3, 4, 5, 6, 7, 8
    SPEC-0028: 1, 3, 4, 5, 6, 7, 8, 9, 10
    SPEC-0029: 1, 2, 3, 8, 10
    SPEC-0030: 1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12
    SPEC-0031: 1, 2, 3, 4, 5, 6, 7, 8
    SPEC-0032: 2, 8, 9, 10, 11, 12, 14
    SPEC-0033: 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12
    SPEC-0034: 1, 2, 3, 7, 8, 9, 10, 12, 13, 14
    SPEC-0035: 2, 5, 6, 7, 9, 10
    SPEC-0036: 2, 3, 4, 5, 6, 7, 8, 9, 10
    SPEC-0037: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14

Totals: ADRs 217, specs 37, requirements 44, scripts 56
```
