# Build state

Appended by docs commits only; feature PRs carry their row in the PR body (`Build-state row:`).

## Done log

| Date | Change | REQs |
| ---- | ------ | ---- |
| 2026-10-14 | K0 self-governed skeleton: layout, constitution, ADR-0001/0002, checks with tests, governance job, settings, stop hook | REQ-001, REQ-002, REQ-003 |
| 2026-10-14 | Decisions log seeded; PR #1 build-state row appended | REQ-006, REQ-008 |
| 2026-10-14 | ADR-0003 (Accepted): CLAUDE.md, push rule, CODEOWNERS, ADR-cover and marker checks, edited trigger | REQ-001, REQ-003, REQ-005 |
| 2026-10-14 | SPEC-0001 agk init (Approved) and day-2 report | REQ-009 |
| 2026-10-14 | agk init implemented per SPEC-0001; kit manifest and templates; ADR-0004 (Accepted): protected list expanded, kit/ and tests/kit_dev/ protected, neutral CLAUDE.md | REQ-009, REQ-001, REQ-003, REQ-005 |
| 2026-10-14 | Installed repositories' make test runs the project's own tests; ADR-0005 (Proposed, amends ADR-0004); SPEC-0001 rule 18 amended | REQ-009 |
| 2026-10-14 | K1 live proof record; build-state rows for PRs #5-#7 | REQ-009 |
| 2026-10-14 | K1 exit: actions pinned to SHAs, CODEOWNERS dedupe, Approved-spec check, installed ADR-0001 records the creation commit, README Installing, kit 0.2.0; ADR-0006 (Accepted, amends ADR-0001) | REQ-005, REQ-009 |
| 2026-10-14 | K2 target survey (tartley/colorama, read-only) and SPEC-0002 agk adopt (Approved) | REQ-010 |
| 2026-10-14 | Shared kit layout (SPEC-0002 rules 5-8, 10, 12 for init and this repository): agk.mk, agk.toml, thin Makefile, project_tests and agk-project-test, default-branch resolution, isolated kit tests, per-mode protected list; ADR-0007 (Accepted, amends ADR-0005); kit 0.3.0; spec amendments applied | REQ-010, REQ-009 |
| 2026-10-14 | agk adopt implemented per SPEC-0002 (rules 1-4, 7, 9, 11, 13-18 and the adopted-mode templates of rule 12): adopt.py, adopt templates and manifest `adopt` section, marked-block appends, refusals, marker patterns, CODEOWNERS block check; ADR-0008 (Accepted); SPEC-0002 amendments applied; kit 0.4.0 | REQ-010 |

## Decisions
2026-10-14 — K0 exit met: make governance green; PR #1 merged under its own rules.
2026-10-14 — K0 closed: PRs #1–#3 merged; ADR-0003 Accepted.
2026-10-14 — K1 live proof met on agk-sandbox (SPEC-0001 rule 24).
2026-10-14 — K1 closed: agk init (SPEC-0001) proven live; ADR-0006 Accepted.
2026-10-14 — K2 adopt proven live on gbvraju/colorama (SPEC-0002 rules 19–20).
