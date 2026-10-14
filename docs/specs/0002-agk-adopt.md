# SPEC-0002: agk adopt

- Status: Approved
- Owner: maintainers
- Requirements: REQ-010

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.
Open points are raised as `Q-K2-n` in `docs/runs/day-5.md`; a rule that depends on one says so. Evidence for the
target facts used here is in `docs/runs/k2-target-survey.md`.

## Rules

### Interface and effects

1. **Command.** `python3 scripts/agk/adopt.py TARGET [--dry-run]`. Standard library only. TARGET is an existing
   directory that is a git work tree. No other options in K2.
2. **Guarantees of init apply.** Exit 0 success including "nothing to do"; 1 refusal (nothing written); 2 usage;
   3 I/O error. Every refusal names the path class and the file, never content (principle 8). No network, no `git` or
   `gh` calls, no commits, no writes outside TARGET. Refuse before any write. Refuse when a path to write passes
   through a symlink, when TARGET is or is inside the kit checkout, and below Python 3.11.
3. **Target files are data.** Adopt reads target files only to compare bytes, to find its own marked blocks and to read
   the default branch (rule 7). It never imports, executes or parses target code, and never runs its tools.

### What a product file is

4. **Three sets.** A *product file* is every file of TARGET that is not adopt-owned. Adopt-owned files are of two
   kinds:
   - **Created** (only when absent; a differing existing file is a conflict): `agk.mk`, `agk.toml`,
     `.github/workflows/governance.yml`, `scripts/agk/*` (checks and helpers), `tests/kit/*`, `.claude/settings.json`,
     `.claude/hooks/stop_check.py`, `.claude/agents/drift-auditor.md`, `config/*`, `constitution/*`, `docs/requirements.md`,
     `docs/adr/*`, `docs/specs/TEMPLATE.md`, `docs/briefs/TEMPLATE.md`, `docs/build-state.md`, `docs/runs/decisions-log.md`.
   - **Block-appended** (adopt may add one marked block, nothing else): `.gitignore`
     (`# >>> agk` … `# <<< agk`), and, when they already exist, `CLAUDE.md`, `.github/CODEOWNERS`,
     `.github/PULL_REQUEST_TEMPLATE.md` (`<!-- >>> agk -->` … `<!-- <<< agk -->`). When absent, they are created
     whole.
   Adopt **never writes** any other file: in particular `Makefile`, `pyproject.toml`, `setup.*`, `tox.ini`,
   `requirements*`, every other `.github/` file, `README*`, `LICENSE*`, sources and the project's tests.
5. **Zero-touch design (Q-K2-1).** The kit owns its commands in `agk.mk` (targets `agk-governance`, `agk-lint`,
   `agk-test`, `agk-project-test`), called as `make -f agk.mk agk-governance`; the workflow, the stop hook and the
   settings call that form. The kit's configuration lives in `agk.toml`: `mode` (`"init"` or `"adopt"`), `version`,
   `installed`, `default_branch`, `test_dirs`, `lint_paths`, `project_tests` and, from rule 9 on, `test_patterns`; keys
   a repository does not need may be omitted (this repository's `agk.toml` carries no stamp). `scripts/agk/config.py
   KEY` prints one value so `agk.mk` can read it. The checks read `agk.toml` first and fall back to `[tool.agk]` in
   `pyproject.toml` (earlier installs). `project_tests` is a shell command: for init, the project's pytest command with
   exit 5 (nothing collected) treated as success; for adopt, empty, which makes `agk-project-test` print a notice (the
   project's own CI runs its tests). The workflow runs `agk-project-test` after the kit tests. `init` installs the
   same `agk.mk` and `agk.toml` and keeps a thin `Makefile` (aliases `governance`, `lint`, `test` to the `agk-*`
   targets; `test` runs `agk-test` then `agk-project-test`), so an earlier init repository behaves as before. `agk-test`
   also runs `tests/kit_dev` when it exists (this repository only). This changes the shared kit: ADR-0007, kit version
   0.3.0. The agk repository adopts `agk.mk` and `agk.toml` itself (its `Makefile` becomes thin aliases), because the
   workflow is verbatim and calls `make -f agk.mk`; ADR-0007 covers it.
6. **No project config is reshaped.** Kit tests run with their own `tests/kit/pytest.ini`, selected by `-c`, so the
   project's `[tool.pytest.ini_options]`, `pytest.ini`, `tox.ini` and `conftest.py` are neither read nor changed.
   `tests/kit/conftest.py` puts `scripts/agk` on `sys.path`. Kit tests are collected only when run through `agk.mk`
   (an environment flag set there); a project's own `pytest .` ignores them (Q-K2-2).

### Default branch

7. **From the target, not assumed.** Adopt reads the default branch from `TARGET/.git` files without calling git:
   `refs/remotes/origin/HEAD` (a `ref: refs/remotes/origin/<name>` line), else `HEAD` of a repository with no
   `origin` remote, else it refuses and asks the user to set it (exit 1). The name is written to
   `agk.toml` (`default_branch`) (Q-K2-6). Init uses the same detection and falls back to `main` instead of refusing; it
   reuses the stamped `default_branch` of an existing `agk.toml`.
8. **Shared fix, init too (Q-K2-1).** `scripts/agk/common.py` resolves the base as `--base`, `AGK_BASE`,
   `GITHUB_BASE_REF`, then `origin/<default_branch>` and `<default_branch>` from `agk.toml` (K1 installs default to
   `main`). The workflow runs on `pull_request` and on every `push`, with a job condition
   `github.event_name == 'pull_request' || github.ref_name == github.event.repository.default_branch`, so no branch
   name is written into it. Printed ruleset instructions name the detected branch; the installed ADR template uses the
   variable `{{default_branch}}` and `kit/templates/branch-rules.txt` keeps its text. The words "main" in installed
   text (`CLAUDE.md`, `constitution/principles.md`, the ADR template) become "the default branch" (ADR-0007).

### Tests, markers, lint

9. **Discovery is configurable.** `agk.toml` `test_dirs` (default `["tests"]`) and `test_patterns` (default
   `["test_*.py"]`); adopt detects `*_test.py` and `test_*.py` files and writes the directories that contain them
   (for the survey target: `colorama/tests`, `*_test.py`). Markers are `REQ-nnn` strings in matching files
   (docstring or comment), so unittest-style projects work. Kit tests live in `tests/kit/`, which is excluded from
   the project's marker search unless listed.
10. **Lint scope.** `agk-lint` runs `ruff check --isolated` with the kit's rule set and line length given as flags, over
    `lint_paths` (default `scripts/agk tests/kit .claude/hooks`). It never reads project lint config and never
    covers product paths; product lint stays the project's own.

### Existing files that adopt meets

11. **Per file.**
    | Existing file | Adopt does |
    | --- | --- |
    | `Makefile`, `pyproject.toml`, `tox.ini`, `requirements*` | nothing |
    | `.github/workflows/*` (other than `governance.yml`), `FUNDING.yml` | nothing; they become protected by class `.github/` (Q-K2-3) |
    | `.gitignore` | append one marked block with the kit's entries; a second block or a changed block refuses |
    | `CLAUDE.md`, `.github/CODEOWNERS`, `.github/PULL_REQUEST_TEMPLATE.md` | append one marked block (Q-K2-5) |
    | `.claude/settings.json` | refuse (no JSON merge in K2) (Q-K2-4) |
    | `.claude/*` other, `config/*`, `docs/*` colliding with a created path, `scripts/agk/*` | refuse when the path exists and differs |
### Protected paths per mode

12. **Per-mode protected list.** Each mode renders `config/protected-paths.txt` and the `protected` class of
    `config/reviewers.yaml` from its own template. Adopted repositories protect `constitution/`, `config/`, `.claude/`,
    `.github/` (all of it), `docs/requirements.md`, `CLAUDE.md`, `scripts/agk/`, `tests/kit/`, `agk.mk` and `agk.toml`,
    and never the project's `Makefile` or `pyproject.toml`. Init repositories keep their current list (`Makefile` and
    `pyproject.toml` included) and add `agk.mk` and `agk.toml`. The agk repository's own list is the init list plus
    `kit/` and `tests/kit_dev/`. `reviewers.py --check` keeps each rendered pair equal. Tests render both modes and
    compare with the expected lists, and assert the adopted list contains neither `Makefile` nor `pyproject.toml`.

13. **ADR-0001 for an adopted repository.** `docs/adr/0001-adopt-agk.md` is rendered from an adopt template. It
    records the adoption date, the kit version, the default branch, the list of existing protected-class files it
    found (`.github/*`), the protected paths, the reviewer model and the ruleset; it states that history before the
    adoption date is not governed, that the adoption PR is the first governed change, and makes no "creation commit"
    claim. Its Status is `Proposed` (maintainers flip it); its text names every protected path class.

### Idempotence, refusal, dry run

14. **Idempotence.** A second run changes nothing and prints `nothing to do` (hashes and mtimes equal). A block-appended
    file whose block equals the kit's is unchanged. Partial installs complete.
15. **Refusal.** Differing created files, a changed or duplicated block, a symlink and an unknown default branch each
    refuse before any write, listing every problem with its path class.
16. **Dry run.** `--dry-run` prints one line per file (`create`, `append`, `unchanged`, `conflict`), writes nothing, and
    exits with the code the real run would.
17. **Init and adopt together.** `adopt` on a repository installed by `init` (`agk.toml` or `[tool.agk]` present) refuses
    with "already installed by init"; `init` on an `agk.toml` with `mode = "adopt"` refuses likewise. Upgrades between
    modes are out of scope (K3).

### Proof

18. **Tests (`tests/kit_dev/test_adopt.py`)** build synthetic existing repositories in `tmp_path`: (a) a `Makefile` with
    its own `test` target, (b) a hatch `pyproject.toml`, (c) default branch `master` with `origin/HEAD` set,
    (d) `*_test.py` unittest tests under `pkg/tests/`, (e) `.gitignore`, a `.github/workflows/ci.yml` and a
    `CODEOWNERS`. After adopt: every pre-existing file is byte-identical except the marked blocks; `make -f agk.mk
    agk-governance` and `agk-test` pass in the target; the project's `make test` still runs its own tests; a marker in
    `pkg/tests/x_test.py` is found; a bare `pytest .` in the target (no `-c`) collects no `tests/kit` test; a second run changes nothing; each refusal case writes nothing; init after adopt
    and adopt after init refuse.
19. **Live proof** (maintainers' and agents' steps, recorded in `docs/runs/`): adopt into `gbvraju/colorama`, a fork of
    `tartley/colorama` (BSD-3-Clause). The adoption PR changes **no product file**, verified by listing its diff
    (only adopt-owned paths and the `.gitignore` block); the project's existing CI (`test.yml`, `lint_python.yml`) still
    passes; `governance` is green; then one small change traced to a requirement.
20. **Safety.** In the fork, every PR targets `gbvraju/colorama` `master`, never the upstream repository. Agents run
    `gh repo set-default gbvraju/colorama` and pass `--repo gbvraju/colorama` explicitly on every `gh` call. Opening
    anything on `tartley/colorama` is forbidden. Agents never run the target's code.

## Tests

- Rules 1–3, 14–17: `tests/kit_dev/test_adopt.py`, marker `REQ-010 AC2` (idempotent, refusals).
- Rules 4–13, 18: `tests/kit_dev/test_adopt.py` and `tests/kit_dev/test_kit_manifest.py`, marker `REQ-010 AC1`
  (no product file modified); rule 12 also compares both modes' rendered protected lists.
- Rules 5–8, 10 (shared kit): `tests/kit/` tests of `common.py`, `agk.mk` and the workflow, markers `REQ-009 AC2`
  and `REQ-010 AC1`.
- Rules 19–20: the live proof, recorded in `docs/runs/`.

## Residual

- 2026-10-14: no upgrade path between kit versions or between init and adopt (K3).
- 2026-10-14: Python 3.11 is required to run the checks even where the project supports 3.9.
- 2026-10-14: no JSON merge for an existing `.claude/settings.json`.
