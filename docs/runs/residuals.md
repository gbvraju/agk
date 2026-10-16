# Residuals register

Date: 2026-10-15 (from `date -u`). SPEC-0004 rule 9 reads this register (amendments 5, applied). Accepted ADRs and Approved specs cannot change except their Status line
(and, for specs, through an amendment), so the due dates of their `## Residual` bullets live here instead.

Each open line is `- <source> | <text> | (due YYYY-MM-DD) | open`. The source is the file and the date of the
bullet. The K3 target is 2026-11-30 and the K4 target is 2026-12-31 (ADR-0015); lines due at K3 start carry 2026-11-30.

## Open

- docs/adr/0001-the-kit-governs-itself.md 2026-10-14 | branch protection and required-review settings are GitHub settings, not files; `agk doctor` documents and verifies them (REQ-002 AC1) | (due 2026-12-31) | open
- docs/adr/0002-milestones.md 2026-10-14 | exit criteria for K4 need measurable thresholds before K4 starts (K3: ADR-0015) | (due 2026-12-01) | open
- docs/adr/0003-agent-context-push-rule-codeowners-check-hardening.md 2026-10-14 | colon-refspec branch deletion (`git push origin :branch`) has no deny rule; revisit when `agk doctor` exists | (due 2026-12-31) | open
- docs/adr/0003-agent-context-push-rule-codeowners-check-hardening.md 2026-10-14 | class naming in an ADR is a substring match on the ADR text (repeated in ADR-0004, ADR-0006, ADR-0007, ADR-0008 and ADR-0009); replace it with a required `Protected classes:` line check | (due 2026-12-15) | open
- docs/adr/0004-init-protected-list-and-neutral-context.md 2026-10-14 | in a target with no `main` or `origin/main`, the diff checks of `make governance` skip with a notice outside CI | (due 2026-12-31) | open
- docs/adr/0006-k1-exit.md 2026-10-14 | the action SHAs were confirmed only by `git ls-remote`; signatures not checked, no attestation verified | (due 2026-12-15) | open
- docs/adr/0006-k1-exit.md 2026-10-14 | evaluate newer majors of the actions (checkout v7, setup-python v7, gitleaks-action v3) in a dedicated PR (Q-K1-16) | (due 2026-11-30) | open
- docs/adr/0006-k1-exit.md 2026-10-14 | gitleaks-action licence terms for organisations unconfirmed; proposed replacement by the MIT gitleaks binary (verify licence) (Q-K1-17) | (due 2026-12-15) | open
- docs/adr/0006-k1-exit.md 2026-10-14 | `check_specs.py` treats a Status-only change of an Approved spec as needing an amendment (conservative) | (due 2026-12-15) | open
- docs/adr/0007-shared-kit-layout.md 2026-10-14 | no upgrade path between kit versions (K3); also SPEC-0002 and ADR-0008 | (due 2026-11-30) | open
- docs/adr/0009-adopt-refusal-fix-codeowners-write-branch-wording.md 2026-10-14 | `--write` is not atomic (temporary file plus rename would be) | (due 2026-12-15) | open
- docs/specs/0001-agk-init.md 2026-10-14 | nothing flags the placeholder team `@REPLACE-ME` after init; `agk doctor` or the drift audit (D5) should report it | (due 2026-12-15) | open
- docs/specs/0002-agk-adopt.md 2026-10-14 | Python 3.11 is required to run the checks even where the project supports 3.9 | (due 2026-11-30) | open
- docs/specs/0002-agk-adopt.md 2026-10-14 | no JSON merge for an existing `.claude/settings.json` | (due 2026-11-30) | open
- docs/specs/0003-reviewer-agent.md 2026-10-14 | the GitHub Action form is deferred to K3 and depends on facts to confirm: the action's name, version, inputs and permissions (verify) | (due 2026-11-30) | open
- docs/specs/0003-reviewer-agent.md 2026-10-14 | the agent's judgement is not measured in CI (rule 22); shadow-review records stand in | (due 2026-11-30) | open
- docs/specs/0003-reviewer-agent.md 2026-10-14 | no inline review comments in K2; one advisory comment at most | (due 2026-11-30) | open
- docs/specs/0004-drift-audit.md 2026-10-14 | the model summary is not in the first implementation (K3) | (due 2026-11-30) | open
- docs/specs/0004-drift-audit.md 2026-10-14 | scheduled-workflow behaviour (jitter, the period after which GitHub may disable schedules) is (verify) against current documentation | (due 2026-11-15) | open
- docs/adr/0012-drift-audit.md 2026-10-15 | workflow token label creation (verify on first live run) | (due 2026-10-22) | open
- docs/runs/shadow-review-summary.md 2026-10-15 | reviewer effectiveness: 0 of 3 human findings caught in each of shadow reviews 2 and 3; measure again and improve | (due 2026-11-30) | open
- docs/runs/plugin-live-proof.md 2026-10-16 | a doctor `warn` check for the repository's Pull requests feature turned off (a comment on a pull request was refused with "Pull requests are disabled" while the repository was otherwise healthy) | (due 2026-11-30) | open
- docs/runs/plugin-live-proof.md 2026-10-16 | a drift-audit check that every tag matches `vX.Y.Z` (lowercase); a tag `V0.10.0` existed beside `v0.10.0` | (due 2026-11-30) | open
- docs/runs/plugin-live-proof.md 2026-10-16 | the skills quote the script path, so a simple `Bash(python3 …/init.py *)` allow rule does not match; the rule needs `Bash(python3 *scripts/agk/init.py* *)` (Q-K3-73) | (due 2026-11-30) | open
- docs/runs/plugin-live-proof.md 2026-10-16 | Q-K3-72: the committed project-scope `.claude/settings.json` form with `ref` is untested, because it needs an interactive workspace-trust dialog | (due 2026-11-30) | open
- docs/runs/doctor-live-proof.md 2026-10-16 | a live doctor run with a non-admin token (plan step 15: the ruleset checks should print `??` with `no-admin`, never `ok`); accepted without it for criterion b (Q-D10-2) | (due 2026-11-30) | open

## Closed (not findings)

| Source | Text | Why it is closed |
| --- | --- | --- |
| docs/adr/0003-agent-context-push-rule-codeowners-check-hardening.md | action versions stay on major tags until K1 exit, then SHA pins | ADR-0006 pinned them to SHAs |
| docs/adr/0001-the-kit-governs-itself.md | `teams.maintainers.github_team` maps to a user handle until an organisation team exists; replace by K1 exit | ADR-0006 amended it: the handle stays until a second maintainer joins |
| docs/adr/0004-init-protected-list-and-neutral-context.md | approved specs are not yet protected by a check | `check_specs.py` exists (ADR-0006) |
| docs/adr/0005-project-tests-run-under-make-test.md | approved specs are not yet protected by a check | same |
| docs/adr/0007-shared-kit-layout.md | `agk adopt` and the adopted-mode protected list are not part of this ADR | ADR-0008 and PR #13 |
| docs/adr/0008-agk-adopt.md | the live proof on a real codebase is still to be done | `docs/runs/k2-live-proof.md` |
| docs/specs/0001-agk-init.md | installed repositories inherit the unpinned action tags and the gitleaks-action licence note; SHA pinning is at K1 exit | pinned in ADR-0006; the licence note is still open and listed above |
| docs/specs/0001-agk-init.md | a target with `pyproject.toml`, `Makefile`, `CLAUDE.md` or `.gitignore` is refused until K2 `agk adopt` | adopt exists (ADR-0008) |
