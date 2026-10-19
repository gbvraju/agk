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
- ADR-0025 positioning review 2026-10-17 | Risk (K4): overlap with spec-driven tools (Spec Kit, Kiro, BMAD and others): before the friends launch, compare in writing what each does after code is written (verification, decision records, drift, product-owner reporting) and state where AGK differs or overlaps, in `docs/runs/`; README claims follow that comparison (owner: maintainers) | (due 2026-12-31) | open
- ADR-0025 positioning review 2026-10-17 | Risk (K4): value is unproven until criterion a: if the product owner cannot answer the five questions from the report alone for two consecutive weeks, the maintainers re-evaluate K5's scope before any launch claim (owner: maintainers) | (due 2026-12-14) | open
- ADR-0025 positioning review 2026-10-17 | Risk (K4): cost of the method is unmeasured: before any launch claim, report cycle time and review rounds per change from the metrics issues, and compare with at least one comparable change made without the kit (owner: maintainers) | (due 2027-01-31) | open
- ADR-0025 positioning review 2026-10-17 | K5 candidate: collision-proof parallel agents: a brief declares the files it owns; a deterministic check fails a pull request that touches a file outside its claim or one claimed by another open brief, so several agents build at once without conflicting pull requests (owner: maintainers) | (due 2027-01-31) | open
- ADR-0025 positioning review 2026-10-17 | K5 candidate: session continuity from the repository: every new agent session starts from a brief generated from the facts document (decided, open, in progress), never from chat memory (owner: maintainers) | (due 2027-01-31) | open
- ADR-0025 positioning review 2026-10-17 | K5 candidate: acceptance pack at handover: a document generated from the facts listing each requirement, its approval, its tests, its proof outcome and its change history, for client sign-off (owner: maintainers) | (due 2027-02-28) | open
- ADR-0025 positioning review 2026-10-17 | K5 candidate: repeatable by someone else: a person other than the maintainers runs the playbook on a new project, without the maintainers in the session, to a governed merge; every step they could not do from the files is a finding (owner: maintainers) | (due 2027-02-28) | open
- ADR-0025 positioning review 2026-10-17 | K5 candidate: layering, not competing: prove AGK adopts onto a repository that already uses one spec-driven tool, with no conflict between their files and AGK's checks, recorded as a live proof (owner: maintainers) | (due 2027-02-28) | open
- ADR-0025 positioning review 2026-10-17 | K5 candidate: hosts beyond GitHub (GitLab, Azure DevOps): scope and cost written down before any enterprise or consulting pilot that needs them (owner: maintainers) | (due 2027-03-31) | open
- ADR-0025 positioning review 2026-10-17 | Before launch: security posture, one page: where code and prompts go, which Claude deployment options apply, where secrets live, what AGK itself stores (nothing); a document, not a feature (owner: maintainers) | (due 2026-11-30) | open
- ADR-0025 positioning review 2026-10-17 | Before launch: existing codebases, docs only: a playbook path for adopting mid-project that records today's behaviour as the baseline requirements before any change (owner: maintainers) | (due 2026-11-30) | open
- ADR-0025 positioning review 2026-10-17 | K5 candidate (small): model choice by work size: a fixed table in `agk.toml` maps role and the brief's declared size (S/M/L) to a Claude model; the architect role and L work use the strongest model, S work a cheaper one; two fix lists on one PR move it up one model; deterministic, no model chooses the model; metrics record the model per PR so the saving is measured, not claimed (owner: maintainers) | (due 2027-01-31) | open
- ADR-0025 positioning review 2026-10-17 | K5 candidate: contract to evidence: statement-of-work milestones mapped to requirements, so a milestone's completion is computed from the facts (owner: maintainers) | (due 2027-02-28) | open
- ADR-0025 positioning review 2026-10-17 | Later, only on demand from a paying user (no build before then): estimation from history, a reusable pattern library, non-functional evidence types, approvals from people outside GitHub, a multi-repository view, the support phase after go-live, training and certification; review the list, not build it (owner: maintainers) | (due 2027-06-30) | open
- ADR-0025 positioning review 2026-10-17 | K5 headline candidate (portal): a light portal for consulting firms and their clients over AGK: sign in with GitHub; create a project (repository, AGK installed, ruleset applied, kickoff drafted); roles as three GitHub teams per project (architects, product owners, engineers); role homes (Needs you, This week, Ask for something, Review queue, all projects); reads only the facts document and writes only GitHub actions through a GitHub App; stores nothing but sign-in sessions; the Claude credential belongs to the party the statement of work names and is never held by the portal; SSO (JumpCloud first) later; first slice read-only, then action buttons, then SSO; not started before the pilot proves the weekly report (criterion a) (owner: maintainers) | (due 2027-01-31) | open
- docs/runs/proof-checks-live-2.md 2026-10-17 | duplicate kit-test run in this repository (CI minutes): `governance` runs the kit tests in `Tests of the checks` and again in `Project tests`, because this repository's `project_tests` is the kit-test command; removing either changes verbatim kit files for every installed repository (Q-K4-135 ruled: keep) (owner: maintainers) | (due 2027-01-31) | open
- docs/runs/product-report-live-1.md 2026-10-17 | the Proven line of the product report shows REQ-001 and REQ-003 as not proven: the proof job of PR #60 ran without pytest (red-on-head, fixed by PR #61 and PR #63); a known false flag for criterion c, resolved when the next change to either requirement reads proven (maintainers' ruling 2026-10-18) (owner: maintainers) | (due 2026-10-31) | open
- ADR-0047 launch docs L1 2026-10-19 | the fix-list verdicts on PRs 76 to 84 were not posted as comments, so `review_rounds` and the report's fix counts for them are understated; note it in the K4 close record, no back-filling (owner: maintainers) | (due 2026-11-30) | open
- ADR-0047 launch docs L1 2026-10-19 | SPEC-0012 rule 10's example id `Q-S0014-1` collides with a real spec; use a number no spec has when the spec is next amended (owner: maintainers) | (due 2026-12-31) | open
- ADR-0047 launch docs L1 2026-10-19 | `playbook.py check-start` names the three items when one has no list under it; its message should name the item that lacks a list (owner: maintainers) | (due 2026-11-15) | open
- SPEC-0014 Q-S0014-1 ruled 2026-10-20 | K5 candidate (small): a file of release notes by kit version, so a reader of the report's `kit version:` line can look up what that version changed; none exists today and none is built before then (owner: maintainers) | (due 2027-01-31) | open

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
| docs/runs/product-report-live-1.md | the Proven line prints the proof reason next to not-proven (e.g. red-on-head) | ADR-0036: the proof workflow names carry the reason, the facts carry `proof_reason`, the Proven line prints it |
| docs/adr/0029-inbox-and-report-renderer.md | the facts carry a path for each spec and ADR so inbox lines link the file | ADR-0036: `path` in the facts; the inbox links the file |
