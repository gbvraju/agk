# K2 target survey: tartley/colorama (read-only)

Date: 2026-10-14 (from `date -u`).

## Method

- Read-only shallow clone of `https://github.com/tartley/colorama` (depth 1) into a directory outside this
  repository. Commit **841634ed2a0da5d5ac2d867db533da8131266cb2** (branch `master`, merge of PR #422, 2026-05-13).
- No file of the target was executed, imported or installed. Only `cat`, `ls`, `git ls-files` and `git rev-parse`
  ran against it, plus one static `ruff check` (a linter that parses source and runs nothing) with the kit's rule
  set, to answer friction point 5.
- `agk init` was not run on it. "What init would do" is reasoned from `kit/manifest.json` (kit 0.2.0) and
  `scripts/agk/init.py`; the planned paths were compared with the clone's file list.
- Clone size: 49 tracked files, 1886 lines of Python (`git ls-files '*.py' | wc -l`), BSD-3-Clause (`LICENSE.txt`,
  `pyproject.toml:11`).

## What `agk init` would do there today

- Planned: 43 files (33 verbatim, 9 templates, 1 rendered `.github/CODEOWNERS`).
- Already existing and differing, so **init refuses** (SPEC-0001 rule 16): `.gitignore`, `Makefile`,
  `pyproject.toml`. Nothing is written.
- Not conflicting (absent in the target): everything else, including `.github/workflows/governance.yml`,
  `.github/PULL_REQUEST_TEMPLATE.md`, `.github/CODEOWNERS`, `CLAUDE.md`, `docs/`, `config/`, `constitution/`,
  `scripts/`, `tests/`, `.claude/`. Top-level directory already present: `.github` only.

## Friction points (confirmed or refuted, with file and line)

1. **`Makefile` has its own `test` target** — CONFIRMED. `Makefile:45-47`:
   `test: ## Run tests` runs `$(python) -m unittest discover -p *_test.py` with `python=$(virtualenv)/bin/python`
   (`Makefile:16-19`, `~/.virtualenvs/colorama`). The kit's `Makefile:15-16` defines `test` as
   `$(PY) -m pytest tests -q`, and CI calls `make governance`, `make lint`, `make test`
   (`.github/workflows/governance.yml:27,34,36`). The same target name means two different things. The target's first
   goal is `help` (`Makefile:9`) and it greps `$(MAKEFILE_LIST)` (`Makefile:10`), so extra makefiles show up in its
   help. The target's CI does not call `make`; it calls `tox` (`.github/workflows/test.yml:55`).
2. **`pyproject.toml` exists (hatch)** — CONFIRMED. `pyproject.toml:1-5` (`hatchling`), `:51-52`
   (`[tool.hatch.version]`), `:54-64` (sdist and wheel `include` lists). The kit writes `[tool.agk]`,
   `[tool.pytest.ini_options]`, `[tool.ruff]`, `[project]` (`kit/templates/pyproject.toml:1-17`), so init refuses.
   Side facts: the sdist includes only `/colorama`, `/demos`, `/CHANGELOG.rst` (`:54-59`) and the wheel only
   `/colorama/*` (`:61-64`), so new top-level kit directories are not shipped. `requires-python = ">=3.9"`
   (`pyproject.toml:12`) while the kit's checks need Python 3.11 (`tomllib`, `scripts/agk/common.py:9,144`); CI uses
   3.12 (`.github/workflows/governance.yml:21`), but a maintainer's local `make governance` on 3.9 would fail.
   A `[tool.pytest.ini_options]` table would also apply to the project's own `pytest` runs (friction 4).
3. **Default branch is `master`; the kit assumes `main`** — CONFIRMED. Target: `.git/HEAD` is
   `ref: refs/heads/master` and `.git/refs/remotes/origin/HEAD` is `ref: refs/remotes/origin/master`. Kit:
   `.github/workflows/governance.yml:6-7` (`push: branches: [main]`, so no governance run after a merge to
   `master`), `scripts/agk/common.py:65` (`for candidate in ("origin/main", "main")`: neither resolves in a
   `master` repository, so outside CI the diff checks skip with a notice at `common.py:182`, and in CI a push
   event fails with "no base ref resolves in CI" at `common.py:69-70`), `kit/templates/branch-rules.txt:1` and
   `kit/templates/adr-0001.md:24` (the ruleset is named `main`), `CLAUDE.md:8` (`origin/main`) and
   `constitution/principles.md:7` ("branched from main"). Pull requests work today because the workflow passes the
   base SHA as `AGK_BASE` (`governance.yml:26`).
4. **Tests are `colorama/tests/*_test.py` run by `unittest`** — CONFIRMED. `colorama/tests/` holds
   `ansi_test.py`, `ansitowin32_test.py`, `initialise_test.py`, `isatty_test.py`, `winterm_test.py`, `utils.py`,
   `__init__.py`; run by `Makefile:46`, `tox.ini:6`, `test.ps1:4`. The kit counts markers only in `test_*.py`
   (`scripts/agk/common.py:158`, `rglob("test_*.py")`) under `test_dirs = ["tests"]`
   (`kit/templates/pyproject.toml:11`); the target has no top-level `tests/` directory, so no marker would ever be
   found and no requirement could become `done`. Also: `.github/workflows/lint_python.yml:22` runs `pytest .`,
   which would collect the installed `tests/kit/test_*.py` and read the installed `[tool.pytest.ini_options]`
   (`pythonpath = ["scripts/agk"]`) in the project's own lint job. (Reasoned from the files, not run.) `unittest
   discover -p *_test.py` (`Makefile:46`) does not match `test_*.py` names and ignores directories without
   `__init__.py`, so it would not pick up `tests/kit`.
5. **`ruff check .` with the kit's config over product code** — CONFIRMED, it would fail. Static run with the kit
   rule set (`E,F,I,B,UP`, line length 100, py311): **72 findings** in product paths — 27 in `colorama/`, 45 in
   `demos/` — by rule: 19 F401, 18 I001, 14 UP031, 13 E501, 3 E731, 3 F841, 1 B023, 1 B007. The kit's lint target is
   `ruff check .` (`Makefile:18-19`); fixing the findings would modify product code, which adopt must never do. The
   project already lints itself (`.github/workflows/lint_python.yml:12-24`: bandit, black, codespell, flake8, isort,
   mypy, pyupgrade, safety).
6. **Existing `.github/` content becomes protected** — CONFIRMED. `.github/FUNDING.yml`,
   `.github/workflows/test.yml`, `.github/workflows/lint_python.yml` exist (3 files). The kit's protected list
   contains `.github/` (`kit/templates/protected-paths.txt`), so any later change to them needs an ADR that names the
   class (principle 1). Their actions are unpinned: `actions/checkout@v4` (`test.yml:26`, `lint_python.yml:7`),
   `actions/setup-python@v5` (`test.yml:29`, `lint_python.yml:8`), `actions/cache@v4` (`test.yml:41`). The kit
   pin test covers only the kit's own workflow. `test.yml:3` triggers on `push` and `pull_request` for all
   branches. No `governance.yml` name collision.
7. **Other findings.**
   - No `CODEOWNERS`, `PULL_REQUEST_TEMPLATE.md`, `CLAUDE.md`, `.claude/`, `.pre-commit-config.yaml` or `docs/`
     (`ls`): all create-able without conflict.
   - `tox.ini` exists (`:1-6`, `isolated_build = true`, `unittest discover`): not conflicting; builds through hatch,
     which includes only the listed paths.
   - `.gitignore` (`:1-13`) ignores `*.pyc` but not `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`; the kit's
     `.gitignore` would conflict, but its entries are needed or untracked cache files appear.
   - Windows/PowerShell: `bootstrap.ps1`, `build.ps1`, `clean.ps1`, `release.ps1`, `test.ps1`,
     `test-release.ps1` plus a bash `test-release`; none conflict. `README-hacking.md:55-60` documents `make test`,
     `make bootstrap`, `make build`, so the Makefile's contract is public.
   - `requirements.txt` is `# none`; `requirements-dev.txt` has `-e .` (`:3`).
   - Upstream guidance is conservative about changes (`README-hacking.md:26-30`); an adoption PR that touches
     only governance files fits it.
   - Governance-relevant: `LICENSE.txt` (not `LICENSE`) — the kit writes no licence file.

## Summary of what adopt must do differently from init

- Never edit `Makefile`, `pyproject.toml`, `tox.ini`, workflows other than its own, or product tests.
- Take the default branch from the target.
- Find tests by configurable directories and patterns (`colorama/tests`, `*_test.py`).
- Limit kit lint to kit paths.
- Append marked blocks to `.gitignore` (and to `CLAUDE.md`, `CODEOWNERS`, PR template when they exist).
- Keep the kit's own tests from being collected or configured by the project's `pytest`.
