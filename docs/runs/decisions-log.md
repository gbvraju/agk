# Decisions log

One row per decision made outside an ADR, so a compacted session can be reconstructed from the repository.

| Date | Decision | Reason | Recorded in | By |
| ---- | -------- | ------ | ----------- | -- |
| 2026-10-14 | Session-mandated branch names accepted (Q-K0-1) | cosmetic | this log | reviewer |
| 2026-10-14 | CODEOWNERS is the one exception to rule 5 | GitHub needs it committed; changes rarely | ADR-0003 (planned) | reviewer |
| 2026-10-14 | Maintainers handle is a mapping only; approvers hold team names; replace by K1 exit (Q-K0-4) | neutrality | ADR-0001 residual | reviewer |
| 2026-10-14 | build-state creation exempt only when absent at base (Q-K0-5) | bootstrap | check_build_state.py + tests | reviewer |
| 2026-10-14 | Stop hook allows stop when `stop_hook_active` (Q-K0-7) | no infinite loop | stop_check.py + tests | reviewer |
| 2026-10-14 | Action versions on major tags until K1 exit, then SHA pins (Q-K0-9) | residual | this log | reviewer |
| 2026-10-14 | Branch protection documented in ADR-0001 until `agk doctor` (Q-K0-10) | not verifiable from sandbox | ADR-0001 | reviewer |
| 2026-10-14 | CI blocked by account billing; no merge on local verification alone | checks must run in CI | this log | reviewer |
| 2026-10-14 | Repository public from K0; K4 redefined as launch | no paid CI minutes | ADR-0001, ADR-0002 | maintainers |
| 2026-10-14 | Initial-commit author email accepted as public; force-push rewrite rejected (rules 2, 3) | history rewrite breaks rules | this log | maintainers |
| 2026-10-14 | Protected-path Edit/Write are `ask`, not `deny` | agents may change protected paths with an ADR (day-0 rule 0.3); CI and maintainers are the gate | settings.json, ADR-0001 | reviewer |
| 2026-10-14 | Colon-refspec deny removed; feature-branch deletion uncovered, `main` protected by ruleset | unconfirmed pattern syntax | day-0.md | reviewer |
| 2026-10-14 | `governance` added as required status check before merging PR #1 | merge gated by CI | ADR-0001 | maintainers |
| 2026-10-14 | Docs-only PRs carry their own dated build-state row; check_pr_body unchanged (Q-K1-1) | the check requires a dated row; `none (...)` was rejected | this log, PR #2 body | reviewer |
| 2026-10-14 | The governance workflow re-runs on PR body edits (`edited` type) | a body fix needs no empty commit | ADR-0003, governance.yml | reviewer |
| 2026-10-14 | Edit rules cover Write, and a leading `/` anchors at the project root; `Write(...)` rules removed (Q-K1-2) | Claude Code consults only Edit and Read path rules | ADR-0003, docs/runs/day-1.md | reviewer |
| 2026-10-14 | `permissions.ask` is a documented key; order deny, ask, allow; (verify) removed (Q-K1-3) | confirmed in the permissions and settings-reference pages | docs/runs/day-1.md | reviewer |
| 2026-10-14 | One ADR must name every changed protected class (Q-K1-4) | cover must state its scope | ADR-0003 decision 4 | reviewer |
| 2026-10-14 | Placeholder team `@REPLACE-ME`: warn only; `agk doctor` residual (Q-K1-5) | a failing check would break REQ-009 AC2 | SPEC-0001 rule 12 and Residual | reviewer |
| 2026-10-14 | Kit-defined requirement ids are `REQ-001..099`; project ids start at `REQ-101` (Q-K1-6) | installed tests carry kit markers | SPEC-0001 rule 11 | reviewer |
| 2026-10-14 | `kit/` is a protected path (Q-K1-7) | the installed law is made of it | ADR-0004 | reviewer |
| 2026-10-14 | Initial statuses conservative: ADR-0001 `Proposed`, REQ-001..003 `planned`; maintainers flip ADR-0001 in the proof PR (Q-K1-8) | agents do not decide | SPEC-0001 rules 11, 13, 24 | reviewer |
| 2026-10-14 | A target with its own pyproject.toml, Makefile, CLAUDE.md or .gitignore is refused in K1 (Q-K1-9) | merging is K2 `agk adopt` | SPEC-0001 rule 16 and Residual | reviewer |
| 2026-10-14 | Installed repositories inherit unpinned action tags and the gitleaks-action licence note until K1-exit SHA pinning (Q-K1-10) | residual | SPEC-0001 Residual | reviewer |
| 2026-10-14 | `tests/kit_dev/` is protected and kit-only (Q-K1-11) | it guards the installer | SPEC-0001 rule 21, ADR-0004 | reviewer |
| 2026-10-14 | `config/protected-paths.txt` is a template, not a verbatim copy (Q-K1-12) | the kit protects `kit/` without installing it | SPEC-0001 rule 21, ADR-0004 | reviewer |
| 2026-10-14 | Approved specs are not yet protected by a check; follow-up after PR #6 (rule 6) | principle 6 has no check yet | this log, ADR-0004 residual | maintainers |
| 2026-10-14 | Project tests must run under `make test` (`pytest tests`, `testpaths = ["tests"]`) | found while preparing the live proof: installed repositories skipped their own tests | ADR-0005, SPEC-0001 rule 18 amendment | maintainers |
| 2026-10-14 | Agent scripts that write text containing backticks or `$` use quoted heredocs (`<<'EOF'`) | an unquoted heredoc expanded backticks in PR #6 and split one fix across two commits | this log | maintainers |
| 2026-10-14 | `init` needs in-session maintainer authorization when run by an agent | a cloned `init.py` is blocked as external code until authorized | docs/runs/k1-live-proof.md | reviewer |
| 2026-10-14 | The sandbox's one direct first commit is authorized | an empty repository has no base branch for a PR; recorded in the target's ADR-0001 | docs/runs/k1-live-proof.md | maintainers |
| 2026-10-14 | Briefs say "final commit, then merge"; agents check PR state before pushing | a maintainer merge overtook an agent's final commit (sandbox PR #2) | docs/runs/k1-live-proof.md | reviewer |
| 2026-10-14 | A stray branch is deleted by maintainers, never by the agent or via the colon refspec | the deny list held and the colon form has no deny rule (ADR-0003 residual) | docs/runs/k1-live-proof.md | reviewer |
| 2026-10-14 | `date -u` is the authoritative date for every artifact, including briefs' dated lines (Q-K1-15) | the brief's 2026-10-15 disagreed with the session clock | docs/build-state.md, docs/runs/decisions-log.md | reviewer |
| 2026-10-14 | Actions in `governance.yml` are pinned to full commit SHAs (latest patch of the existing majors) with the tag in a comment | unpinned tags were a residual since ADR-0003 | ADR-0006, docs/runs/day-4.md | reviewer |
| 2026-10-14 | CODEOWNERS renders each path once, the later class winning | duplicate lines when a path is in two classes | ADR-0006 | reviewer |
| 2026-10-14 | A change to an Approved spec needs a proposed-spec-amendments file naming it (`check_specs.py`) | principle 6 had no check | ADR-0006 | reviewer |
| 2026-10-14 | The `maintainers` handle mapping stays until a second maintainer joins, then becomes an organisation team | K1 exit passed without an organisation | ADR-0006 (amends ADR-0001 residual) | reviewer |
| 2026-10-14 | The installed ADR-0001 names the repository's creation commit as its one direct commit | an empty repository needs one direct first commit | ADR-0006, kit/templates/adr-0001.md | reviewer |
| 2026-10-14 | README gains an "Installing" section; kit version is 0.2.0 | installed content changed | ADR-0006, kit/manifest.json | reviewer |
| 2026-10-14 | Keep the current action majors; evaluate newer majors in a dedicated PR (Q-K1-16) | a major change is a behaviour change | ADR-0006 residual | reviewer |
| 2026-10-14 | gitleaks-action licence stays a residual; proposed resolution: the MIT gitleaks binary (verify licence), K2 or K4 (Q-K1-17) | org-owned targets should need no key | ADR-0006 residual | reviewer |
| 2026-10-14 | The K2 target is a fork of `tartley/colorama` (`gbvraju/colorama`) | a real codebase for `agk adopt`; read-only until the fork exists | this log | maintainers |
| 2026-10-14 | K2 is split into three specs (adopt, reviewer agent, drift audit), each approved before its implementation | one reviewable step at a time | this log | reviewer |
| 2026-10-14 | The kit's commands live in `agk.mk` and its configuration in `agk.toml`; init and this repository use them, the `Makefile` is thin aliases (Q-K2-1) | adopt must not edit a project's Makefile or pyproject.toml; one workflow serves every mode | ADR-0007 | reviewer |
| 2026-10-14 | Kit tests are collected only through `agk.mk` (`AGK_KIT_TESTS=1`) and run with their own `tests/kit/pytest.ini` (Q-K2-2) | a project's `pytest .` must not collect or be configured by kit tests | ADR-0007 | reviewer |
| 2026-10-14 | The base branch comes from `agk.toml` (default `main`), and the workflow has no branch name | adopted repositories may use `master` or any default branch | ADR-0007 | reviewer |
| 2026-10-14 | Installed protected list gains `agk.mk` and `agk.toml`; this repository's list also has `kit/` and `tests/kit_dev/` | the kit's commands and config are law | ADR-0007 | reviewer |
| 2026-10-14 | "main" in installed text becomes "the default branch"; kit version is 0.3.0 (Q-K2-7) | installed content changed | ADR-0007 | reviewer |
| 2026-10-14 | `agk adopt` creates adopt-owned files only when absent and appends one marked block to `.gitignore`, `CLAUDE.md`, CODEOWNERS and the PR template; it never writes `Makefile`, `pyproject.toml` or other product files | adoption must not change product code (ADR-0002) | ADR-0008, SPEC-0002 rules 4, 11 | reviewer |
| 2026-10-14 | Adopt refuses before any write on a differing created file, a changed or duplicated block, a symlink or an unknown default branch | no partial installs | ADR-0008, SPEC-0002 rule 15 | reviewer |
| 2026-10-14 | Adopt detects `test_dirs` and `test_patterns` from the target and excludes `tests/kit` from the marker search in adopt mode | projects use `*_test.py` and their own layouts | ADR-0008, SPEC-0002 rule 9 | reviewer |
| 2026-10-14 | `reviewers.py --check-codeowners` compares only the marked block of a project CODEOWNERS; kit version is 0.4.0 | a project's own CODEOWNERS lines are not the kit's | ADR-0008 | reviewer |
| 2026-10-14 | K2 `agk adopt` is proven live on `gbvraju/colorama` (agk d64c42c): no product file changed except a `.gitignore` block; checks green; colorama's `Test` matrix green; `lint_python` red upstream since 2026-05-13 | SPEC-0002 rules 19-20 | docs/runs/k2-live-proof.md | maintainers |
| 2026-10-14 | Finding (a): adopt's refusal when `origin/HEAD` is missing names the fix `git remote set-head origin --auto` | session clones may lack `refs/remotes/origin/HEAD` | docs/runs/k2-live-proof.md (item E, ADR-0009) | reviewer |
| 2026-10-14 | Finding (b): `reviewers.py --codeowners --write` writes CODEOWNERS or the marked block; plain `--codeowners` still prints | agents cannot always redirect stdout | docs/runs/k2-live-proof.md (item E, ADR-0009) | reviewer |
| 2026-10-14 | Finding (c): project-wide linters scanning `.` flag kit files (bandit 255 findings in the fork); a design note comes before any code change | kit files are scanned like product files | docs/runs/k2-live-proof.md, docs/runs/design-kit-lint-clean.md | reviewer |
| 2026-10-15 | Suffixed branch names (`-b` ... `-e`) accepted for parallel overnight PRs | one session-mandated name, several PRs (Q-ON-1) | PR #14 | reviewer |
| 2026-10-15 | Kit-code scanner policy: documented exclude snippets plus justified `# nosec` for the 31 subprocess findings and 4 mypy fixes now; plugin form at K3 (Q-ON-2) | no directory is skipped by all five tools | PR #15, docs/runs/design-kit-lint-clean.md | reviewer |
| 2026-10-15 | init and adopt print the scanner exclude snippets after a run, print only (Q-ON-3) | consistent with the printed ruleset | PR #15 | reviewer |
| 2026-10-15 | flake8, pylint and mypy findings on kit code are advisory (Q-ON-4) | the kit keeps `ruff` at 100 columns | PR #15 | reviewer |
| 2026-10-15 | The `# nosec` code PR is separate and later (Q-ON-5) | it changes installed files: ADR and kit version | PR #15 | reviewer |
| 2026-10-15 | Reviewer definition and scripts are installed by init and adopt (Q-ON-6) | SPEC-0003 rule 13 | PR #16, docs/specs/0003-reviewer-agent.md | reviewer |
| 2026-10-15 | The reviewer's GitHub Action form and its cost budget are deferred to K3 (Q-ON-7, Q-ON-8) | needs a maintainer-held secret and K3 metrics | PR #16, SPEC-0003 rule 14 | reviewer |
| 2026-10-15 | Reviewer metrics are aggregated at K3; K2 uses hand-recorded transcripts and no replay harness (Q-ON-9, Q-ON-10) | SPEC-0003 rules 17, 22 | PR #16 | reviewer |
| 2026-10-15 | The reviewer reviews every PR (Q-ON-11) | SPEC-0003 rule 12 | PR #16 | reviewer |
| 2026-10-15 | Reviewer truncation caps are configurable in `agk.toml` as `review_diff_cap` and `review_other_cap` (Q-ON-12) | caps were placeholders | PR #16, SPEC-0003 rule 6 | reviewer |
| 2026-10-15 | The reviewer shadow-reviews real PRs alongside the human reviewer; agreements and misses are recorded in `docs/runs/` | live proof before reliance | PR #16, SPEC-0003 rule 23 | reviewer |
| 2026-10-15 | Drift audit: staleness limit N = 14 days for Draft specs and Proposed ADRs (Q-ON-13) | SPEC-0004 rule 8 | PR #17, docs/specs/0004-drift-audit.md | reviewer |
| 2026-10-15 | Drift audit: residual due dates use `(due YYYY-MM-DD)`, with a later backfill (Q-ON-14) | without it D4 finds nothing | PR #17, SPEC-0004 rule 9 | reviewer |
| 2026-10-15 | Drift audit: a clean run writes nothing; an open audit issue stays until a maintainer closes it (Q-ON-15) | SPEC-0004 rules 14, 15 | PR #17 | reviewer |
| 2026-10-15 | Drift audit workflow is installed by default by init and adopt (Q-ON-16); the model summary is deferred to K3 (Q-ON-17) | needs only the `GITHUB_TOKEN` | PR #17, SPEC-0004 rules 3, 16 | reviewer |
| 2026-10-15 | Drift audit schedule is Saturday 06:17 UTC (Q-ON-18), final | placeholder confirmed | PR #17, SPEC-0004 rule 4 | reviewer |
| 2026-10-15 | Drift audit issue title, label and label creation accepted (Q-ON-19); the audit documents and reports that GitHub may disable schedules after inactivity and keeps `workflow_dispatch` | SPEC-0004 rules 13, 23 | PR #17 | reviewer |
