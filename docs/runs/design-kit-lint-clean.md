# Design note: making kit code clean under project scanners (finding c)

Date: 2026-10-14 (from `date -u`). Docs only; no code changes tonight. Written for overnight item B.

## Problem

Adoption is zero-touch for product files, but a project that runs a scanner over `.` also scans the kit files that
adopt installs (`scripts/agk/`, `tests/kit/`, `.claude/hooks/`). The live proof on the colorama fork saw bandit report
255 findings after adoption and 0 before (`docs/runs/k2-live-proof.md`, finding c).

## Method

- Kit: this repository at `main` d64c42c (kit 0.4.0). A fresh `python3 scripts/agk/init.py` into an empty git
  repository outside this repository installs 49 files, of which 25 are Python: 11 in `scripts/agk/`, 13 in
  `tests/kit/`, 1 in `.claude/hooks/`.
- Tools in a throwaway virtual environment outside this repository (in the agent's scratch directory): bandit 1.9.4,
  flake8 7.4.1, mypy 2.4.0, pylint 4.1.3, codespell 2.4.3, plus pytest (the kit tests import it).
- Each tool run with **default settings, scanning `.`**, from the root of that target:
  `bandit -r . -f json -q`, `flake8 .`, `mypy .`, `pylint --recursive=y .`, `codespell .`. A plain `pylint .` was
  also run once and gave a different rating (8.64/10) because it lints only what it can import; counts below use
  `--recursive=y`. Nothing in the target was executed except by the tools themselves.
- Skip behaviour was measured separately in a probe tree: one file with the same violations (an `assert`, a
  `subprocess` call, a type error, a typo) in each of 17 candidate directories, then every tool run on `.`.

## Counts on a fresh init target

| Tool | Findings | `scripts/agk` | `tests/kit` | `.claude/hooks` | Notes |
| --- | --- | --- | --- | --- | --- |
| bandit | 255 | 9 | 243 | 3 | 224 B101 (asserts, all in `tests/kit`), 17 B603, 9 B607, 5 B404; all LOW severity, HIGH confidence; same numbers as the fork |
| flake8 | 196 | 80 | 109 | 7 | 183 E501 (79-column default, the kit uses 100), 13 E203 (slice spacing from `ruff format`) |
| mypy | 4 | 4 | 0 | not scanned | 3 in `check_protected_changes.py` (a `Path` reused as a `str`), 1 in `check_adrs.py` (missing annotation); `.claude/hooks` is a dot-directory and mypy skips it |
| pylint | 139 | 43 | 90 | 3 | 136 attributed to a path plus 3 `duplicate-code`; 64 missing-function-docstring, 40 redefined-outer-name (pytest fixtures), 14 subprocess-run-check; rating 9.10/10 |
| codespell | 0 | 0 | 0 | 0 | |

Per-path bandit detail: `tests/kit` 224 B101, 12 B603, 4 B607, 3 B404; `scripts/agk` 4 B603, 4 B607, 1 B404;
`.claude/hooks` 1 each of B603, B607, B404. The 31 subprocess findings are all fixed-argument-list calls without a
shell (`subprocess.run([...])`).

## Which directories each tool skips by default (measured, scanning `.`)

| Directory | bandit | flake8 | mypy | pylint | codespell |
| --- | --- | --- | --- | --- | --- |
| `.agk`, `.hidden/sub` (dot-directories) | scans | scans | skips | skips | skips |
| `.venv` | scans | scans | skips | skips | skips |
| `.git`, `.tox`, `.nox`, `.eggs` | scans | skips | skips | skips | skips |
| `__pycache__` | scans | skips | skips | scans | scans |
| `x.egg` | scans | skips | scans | scans | scans |
| `node_modules`, `site-packages` | scans | scans | skips | scans | scans |
| `venv`, `build`, `dist`, `_agk`, `vendor`, `third_party` | scans | scans | scans | scans | scans |

**No directory is skipped by all five tools.** bandit scanned every one of the 17 directories, including `.git` and a
dot-directory; flake8 scans dot-directories other than its short exclude list. Hidden directories are not a safe
place.

## What the proof target's own CI would do

colorama's `lint_python.yml` runs `bandit --recursive --skip B311 .` (line 12), so after adoption that step reports the
kit's 255 findings. Its other steps are advisory or narrow: `black --check . || true`, `flake8 . --select=E9,F63,F7,F82`
(syntax errors only), a second `flake8 --exit-zero`, `isort ... || true`, `mypy ... || true`, `pyupgrade || true`,
`codespell` (0 findings). Only bandit (and `pytest .`, handled by the collect-ignore of `tests/kit`) can turn a
project red because of the kit. The job was already red upstream, so adoption did not change its colour, but a
healthy project would see it go red.

## Options

| # | Option | Effort | Risk | Zero-touch | What it removes |
| --- | --- | --- | --- | --- | --- |
| 1 | Justified inline suppressions on kit source (`# nosec B603 B607 - fixed argv, no shell`) | small: about 31 lines in 13 files, plus 4 type fixes for mypy | low: comments and annotations only; each suppression states why | yes (kit files change, product files do not) | bandit B404/B603/B607 (31), mypy (4); not B101, not flake8/pylint style |
| 2 | Kit tests without bare `assert` (helper that raises, or `unittest` style) | large: 224 sites in 13 test files, installed verbatim | medium: loses pytest's assertion introspection or rewrites 150+ tests; every message hand-written | yes | bandit B101 (224); redefined-outer-name stays |
| 3 | Move kit files under one directory the tools skip by default | large: moves fixed paths (`.claude/hooks` is fixed by Claude Code; settings, workflow, `agk.mk`, protected list, ADRs) | high | yes in effect | **nothing**: no directory is skipped by all five tools, and bandit skips none |
| 4 | Documented per-tool exclude snippets the project adds itself (never written by adopt), for example `bandit -r . -x ./scripts/agk,./tests/kit,./.claude` or `exclude_dirs` in the project's bandit config, flake8 `--extend-exclude`, `[tool.pylint.main] ignore-paths`, mypy `exclude` | small: a documented block, optionally printed by init/adopt | low for adopt; relies on the project to apply it, so the first scanner run after adoption is red until it does | yes: adopt writes nothing; the project edits its own CI or config | everything, per tool, once applied |
| 5a | Kit code outside the project tree: the K3 plugin form (installed package or cache directory) | large, planned for K3 | medium: new install and upgrade path | yes | all findings: scanners never see the files |
| 5b | Per-file suppression through a project bandit baseline | small | medium: baselines drift and are the project's file | no (project config) | bandit only |

## Recommendation

Combine **4 + 1 now, 5a at K3**; do not do 2 or 3.

1. Option 4 now: document the exclude snippets (a short section in the README and in the adoption ADR template's
   Residual), and have init and adopt print them after a run, as they already print the ruleset. Adopt still writes
   nothing outside its owned set.
2. Option 1 for kit source: add the 31 justified `# nosec` comments to `scripts/agk/`, `.claude/hooks/` and the
   non-assert subprocess calls in `tests/kit/`, and fix the 4 mypy findings. Then the only default-bandit findings left
   are the 224 asserts in `tests/kit`, which projects commonly exclude or skip (B101 in test code is a widespread
   convention), and the single snippet `-x ./tests/kit` covers them.
3. Option 5a at K3: when the kit is a plugin, its code is outside the tree and the problem disappears.

Why not 2: it changes 224 assertions for a warning that is a convention in test code, and weakens the kit's own test
diagnostics. Why not 3: the measured matrix shows it cannot work.

Style findings (flake8 line length and slice spacing, pylint docstrings and fixture names) are advisory in the proof
target and in most projects; the kit's own gate is `ruff` with a 100-column line length. They are not a goal for
zero.

## Questions for maintainers

- **Q-ON-2:** adopt the recommended combination (snippets now, `# nosec` for the 31 subprocess findings plus the 4
  mypy fixes, plugin form at K3), or choose option 2 for the asserts as well?
- **Q-ON-3:** may init and adopt print the exclude snippets after a run (print only, as with the ruleset)?
- **Q-ON-4:** accept flake8, pylint and mypy findings on kit code as advisory (the kit keeps `ruff` at 100 columns), or
  should the kit also meet flake8's 79-column default and pylint's docstring rules?
- **Q-ON-5:** a follow-up code change for options 1 is a normal PR with tests; it changes installed files, so it
  needs an ADR and a kit version bump. Open that PR after this note is accepted?
