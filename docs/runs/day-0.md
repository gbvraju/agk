# Run report: day 0 (K0 skeleton)

Date: 2026-10-14 (from `date -u`).

## Decisions taken

- Layout, files and Makefile targets exactly as brief §3; `make governance` runs the six repository checks,
  `make test` runs `tests/kit`, `make lint` runs ruff (brief §3, §7).
- Protected path list = the five entries of `reviewers.yaml` class `protected`: `constitution/`, `config/`,
  `.claude/`, `.github/`, `docs/requirements.md`; `reviewers.py --check` fails if the two lists differ (brief §3, §6).
- `check_protected_changes` reads the protected list from the base commit when it exists there, so a PR cannot shrink
  the list it is judged by; ADR cover = added or modified `docs/adr/*.md` other than `TEMPLATE.md` (brief §3, rule 11).
- Checks compare the merge base to the working tree (including untracked files) so the Stop hook sees uncommitted work.
  Base: `--base`, `AGK_BASE`, `GITHUB_BASE_REF`, then `origin/main`/`main`. No base outside CI: diff checks print
  "skipped" and pass; in CI an unresolvable base fails (brief §3).
- Requirements format: `### REQ-nnn — title` sections with a `- Status:` line; marker directories from
  `[tool.agk] test_dirs` in `pyproject.toml` or `--tests-dir` (brief §3, §4).
- ADR format: header fields Status, Date, Deciders, Related, Requirements (optional Amends); Status in
  Proposed|Accepted|Superseded|Rejected; sections Context, Decision, Consequences, Residual (brief §3).
- `check_pr_body` requires `Advances:` containing a REQ id and `Build-state row:` containing a YYYY-MM-DD date;
  it runs in CI only on pull requests (brief §3, rule 0.7).
- Settings additionally deny `gh pr merge`, the GitHub merge tool, auto-merge and `--force-with-lease` (rule 2).
- CI job: checkout (full history), Python 3.12, `make governance`, PR body check, lint, tests, gitleaks (brief §3).
- `CODEOWNERS` is rendered by `reviewers.py --codeowners` but not committed here (brief §6, rule 5).

## Questions

- Q-K0-1: brief names branch `chore/k0-skeleton`; this session mandates `ccr-7649d887-m9hvn7`. Used the latter.
- Q-K0-2: in §4 the section-5 heading and the REQ-010 acceptance criteria are interleaved; read as
  REQ-010 AC1 "no product file modified", AC2 "idempotent".
- Q-K0-3: `.github/CODEOWNERS` is "generated, committed by a docs PR" but `.github/` is protected (ADR needed) and
  rule 5 says generated files are never committed. Not committed; needs a reviewer decision.
- Q-K0-4: `teams.maintainers.github_team` is a user handle, not an organisation team (as in brief §6); the schema
  accepts `@handle` or `@org/team`. AC3 holds because approvers name teams, never handles.
- Q-K0-5: `docs/build-state.md` must be created by this PR although `check_build_state` forbids feature PRs from
  touching it; creation (absent at base) is exempt. Reviewers to confirm.
- Q-K0-6: ADR-0001 and ADR-0002 are written `Accepted` as the brief states; maintainers confirm by merging.
- Q-K0-7: Stop hook contract (JSON `decision: block` with exit 0, `stop_hook_active`, `$CLAUDE_PROJECT_DIR`) is
  (verify). The hook allows the stop when `stop_hook_active` is true to avoid an endless loop; stricter reading
  would always block.
- Q-K0-8: permission rule syntax (`Bash(cmd:*)`, `Edit(./path/**)`, `Write(...)`), settings `hooks` shape, and agent
  frontmatter keys are (verify). Deny rules for `Edit`/`Write` cover Claude's edit tools, not shell redirects.
- Q-K0-9: GitHub Action versions (`checkout@v4`, `setup-python@v5`, `gitleaks-action@v2`) are (verify) and not
  pinned to SHAs; gitleaks-action licence terms for organisations are (verify). gitleaks is not installed in the
  sandbox, so the secret scan was not run locally.
- Q-K0-10: branch protection, required reviews and the "governance" required check are GitHub settings; not
  configurable or verifiable from this sandbox (REQ-002 AC1, `agk doctor` is later).
- Q-K0-11: `Advances: none` is rejected by the PR body check; docs-only PRs with no REQ must name one.
- Q-K0-12: requirement markers are counted in all files under `tests/`, including check fixtures that mention
  REQ ids; markers prove presence, not meaning.

## Verified

Run on 2026-10-14 in the sandbox:

- `make governance`: exit 0; ok protected-changes (covered by an ADR), requirements (12), adrs (2),
  neutrality (0 tokens), build-state (file created), reviewers.
- `make test`: 76 passed.
- `ruff check .`: All checks passed.
- `python3 scripts/agk/traceability.py`: matrix printed to stdout; nothing written.

## Reviewer interim rulings (2026-10-14)

- Q-K0-1 accepted.
- Q-K0-3: CODEOWNERS becomes a documented exception to rule 5 (ADR plus a match check) in PR #2 (ADR-0003).
- Q-K0-4: handle stays in `config/reviewers.yaml` as a mapping only; dated residual added to ADR-0001; fixtures use
  placeholders; authority lists hold team names only.
- Deferred to PR #2 (not in #1): CLAUDE.md, push allow (`git push -u origin HEAD` only), decisions-log.
- Deny rules in #1 tightened: push force/lease/`+refspec`/`--delete`/`:branch` in any flag position and
  `git reset * --hard`; wildcard rule syntax is (verify).

## CI result (2026-10-14)

- Governance runs 38587251218 and 38593030035 on PR #1: failed, 5-6 s. Job 115952558042 never started: the check
  annotation says recent account payments failed or the spending limit needs raising (GitHub Billing & plans).
  No step ran, so no gitleaks, lint or test output exists; no secret finding. `gh run view --log-failed` returned
  Forbidden and the logs API returned 404, so the annotation is the only evidence. This is not a code failure;
  no check was changed. The founder must fix billing and re-run.
- Added: test that the stop hook exits 0 silently when `stop_hook_active` is true; tests that the build-state
  creation exemption holds only when the file is absent at base (editing an existing file fails, committed or not).
- Deferred to PR #2: markers only in `test_*.py` (Q-K0-12), verification of Q-K0-8 facts, the `Advances: none` escape.
- Local after this commit: `make governance` exit 0; `make test` 80 passed; `ruff check .` passed.
