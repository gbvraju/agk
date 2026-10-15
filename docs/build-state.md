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
| 2026-10-14 | K2 adopt live proof record; build-state rows for PRs #11-#13 | REQ-010 |
| 2026-10-14 | Design note: making kit code clean under project scanners (bandit, flake8, mypy, pylint, codespell measured on a fresh init target) | REQ-010 |
| 2026-10-14 | SPEC-0003 reviewer agent (Approved) and notes; REQ-013 not added | REQ-010 |
| 2026-10-14 | SPEC-0004 drift audit (Approved) and notes | REQ-011 |
| 2026-10-14 | Adopt refusal names `git remote set-head origin --auto`; `reviewers.py --codeowners --write`; printed branch-rule text says "ruleset for the default branch"; ADR-0009 (Accepted); kit 0.4.1 | REQ-010, REQ-005 |
| 2026-10-15 | Build-state rows for PRs #14-#18, decisions-log rows for the morning rulings (Q-ON-1 to Q-ON-19), residuals register (docs/runs/residuals.md) read by SPEC-0004 rule 9 (amendments 5 applied) | REQ-006, REQ-011 |
| 2026-10-15 | Kit code under project scanners: justified `# nosec` on the 31 bandit subprocess findings, 4 mypy findings fixed, scanner exclusion snippets printed by init and adopt and quoted in the README; ADR-0010 (Accepted); kit 0.4.2 | REQ-010 |
| 2026-10-15 | SPEC-0004 rules 9 and 18 amended (amendments 5 applied: D4 reads docs/runs/residuals.md); residuals register open; SPEC-0001 rule 19 and SPEC-0002 rule 8 name the printed scanner-exclusion block (amendments 6 applied) | REQ-011, REQ-010 |
| 2026-10-15 | Reviewer agent per SPEC-0003 rules 1-22: review_context.py, check_review_report.py, read-only reviewer subagent, fixture PRs F1-F10 with their tests installed in tests/kit, REQ-013 added (planned); ADR-0011 (Accepted); kit 0.5.0 | REQ-013 |
| 2026-10-15 | Drift audit per SPEC-0004 (with amendments 5 and 8): drift_audit.py (D1-D6), weekly drift-audit.yml, fixture repositories with known drift, tests installed in tests/kit; ADR-0012 (Accepted); ADR-0005 set to Accepted; kit 0.6.0 | REQ-011 |
| 2026-10-15 | Shadow review 1 (SPEC-0003 rule 23): reviewer agent run on #12 and #6 (first commits), #22 (final) and #23 (open); reports recorded verbatim in docs/runs/shadow-review-1.md; validator ok on all four | REQ-013 |
| 2026-10-15 | Shadow review 2 (SPEC-0003 rule 23): reviewer agent re-run on #12 (bd381ef), #6 (e001628) and #22 (071ded6) with minimal bodies; reports recorded verbatim in docs/runs/shadow-review-2.md; validator ok on all three | REQ-013 |
| 2026-10-15 | Reviewer fix from shadow review 2: the context always includes the operating rules of CLAUDE.md and the full current text of every changed file, and the agent checks every Accepted ADR decision and Approved spec rule against the whole diff; fixtures F11 and F12; SPEC-0003 amendments 9 applied; ADR-0013 (Accepted); kit 0.6.1 | REQ-013 |
| 2026-10-15 | Shadow review 3 (SPEC-0003 rule 23): reviewer agent re-run on #12 (bd381ef), #6 (e001628) and #22 (071ded6) against origin/main fa06529 (kit 0.6.1) with the same minimal bodies; reports verbatim in docs/runs/shadow-review-3.md; validator ok on all three | REQ-013 |
| 2026-10-15 | Installed-tests check: scripts/agk/check_kit_tests.py fails when a scripts/agk/check_*.py of the manifest's verbatim set has no test file under tests/kit/ in the same set that imports or runs it; run by agk-governance; ADR-0014 (Proposed); kit 0.6.2 | REQ-009 |
| 2026-10-15 | SPEC-0005 distribution (Approved): recommends the hybrid (law vendored and enforced by CI, plugin carries the workflow commands, no lock file), compares options A, B and C, lists eight /agk: commands, states that GitHub issues are intake only; Q-K3-4 to Q-K3-11 ruled; REQ-014 to be added by ADR | REQ-012 |

## Decisions
2026-10-14 — K0 exit met: make governance green; PR #1 merged under its own rules.
2026-10-14 — K0 closed: PRs #1–#3 merged; ADR-0003 Accepted.
2026-10-14 — K1 live proof met on agk-sandbox (SPEC-0001 rule 24).
2026-10-14 — K1 closed: agk init (SPEC-0001) proven live; ADR-0006 Accepted.
2026-10-14 — K2 adopt proven live on gbvraju/colorama (SPEC-0002 rules 19–20).
2026-10-15 — SPEC-0003 and SPEC-0004 Approved; kit 0.4.1.
2026-10-15 — drift-audit live run #1 (workflow_dispatch, 60ac2b4) succeeded; see docs/runs/drift-audit-live-run-1.md.
2026-10-15 — K2 closed.
2026-10-15 — SPEC-0005 Approved (distribution: hybrid, no lock file).
