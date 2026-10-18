# SPEC-0001: agk init

- Status: Approved
- Owner: maintainers
- Requirements: REQ-009

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.
Open points are raised as `Q-K1-n` in `docs/runs/day-2.md`; a rule that depends on one says so.

## Rules

### Interface and effects

1. **Command.** `python3 scripts/agk/init.py TARGET [--dry-run]`. Standard library only. TARGET is an existing
   directory. No other options in K1.
2. **Exit codes.** 0: success, including "nothing to do". 1: refusal (a conflict, or TARGET unusable); nothing is
   written. 2: usage error. 3: an I/O error while writing. Every non-zero exit prints a message that names the path
   class (the `config/protected-paths.txt` entry, or `scripts/`, `tests/`, `docs/`, …) and the file; never file
   content or a setting value (principle 8).
3. **No side effects beyond TARGET.** No network, no `git` or `gh` calls, no `git push`, no commits, no writes
   outside TARGET. Init refuses when a path it would write passes through a symlink. It does not require TARGET to be
   a git work tree; when it is not, init prints a notice (the checks need git).
4. **Interpreter.** Init refuses with exit 1 below Python 3.11 (the checks read `pyproject.toml` with `tomllib`).
5. **Self-target.** Init refuses when TARGET is, or is inside, the kit checkout it runs from.

### Source of truth

6. **Two sources, one manifest.** `kit/manifest.json` lists, under `verbatim`, every file copied byte-for-byte from
   the kit checkout, and under `templates`, each target path with its template in `kit/templates/`. Init reads only the
   manifest; it copies nothing else. Init runs from a checkout of the kit; neither `scripts/agk/init.py` nor `kit/` is
   installed in the target (K3's plugin form may change this).
7. **Verbatim set** (the law and its tests; never project-specific): `.claude/settings.json`,
   `.claude/hooks/stop_check.py`, `.claude/agents/drift-auditor.md`, `.github/workflows/governance.yml`,
   `.github/PULL_REQUEST_TEMPLATE.md`, `CLAUDE.md`, `Makefile` (thin aliases of `agk.mk`), `agk.mk`, `.gitignore`,
   `constitution/principles.md`, `docs/adr/TEMPLATE.md`, `docs/specs/TEMPLATE.md`, `docs/briefs/TEMPLATE.md`, every
   check and helper in `scripts/agk/` except `init.py` (`common.py`, `check_*.py`, `config.py`, `reviewers.py`,
   `traceability.py`), and `tests/kit/` (rule 18, including `tests/kit/pytest.ini`). Kit-only files are never installed: `scripts/agk/init.py`, `kit/`, `tests/kit_dev/`.
8. **Template set** (project-specific): `constitution/vision.md`, `docs/requirements.md`,
   `docs/adr/0001-adopt-agk.md`, `config/reviewers.yaml`, `config/protected-paths.txt` (rule 21),
   `config/neutrality.txt`, `docs/build-state.md`, `docs/runs/decisions-log.md`, `docs/runs/residuals.md` (created only when absent; an existing file of any content
   is left as it is, never a conflict), `pyproject.toml`, `agk.toml`.
   Templates may use these variables only: `{{project}}` (TARGET's directory name), `{{date}}` (rule 14),
   `{{kit_version}}`, `{{default_branch}}`.
9. **Duplication versus divergence.** The verbatim set is not duplicated under `kit/`: the manifest points at the kit's
   own files, so they cannot diverge. Templates are the only duplicated text. Tests (rule 23) fail when a file the kit
   uses as law is missing from the manifest, when a manifest path does not exist, or when a template does not pass
   neutrality (rule 20).

### Target result

10. **File list.** After a successful run TARGET contains exactly the verbatim and template files above, plus
    `.github/CODEOWNERS` (rule 12); nothing else is created. Files already in TARGET and not in the plan
    (for example `README.md`, `LICENSE`, product code) are never read, changed or listed as conflicts.
11. **Seeded requirements.** The target's `docs/requirements.md` contains `REQ-001`..`REQ-003` with the kit's own
    rules: protected paths change only with an ADR that names their class; agents never merge or bypass checks; every
    requirement is traceable to tests. Each is `- Status: planned` (init marks nothing done). The wording drops
    references to tooling that does not exist yet. `REQ-001`..`REQ-099` are reserved for kit-defined ids; project requirements start at `REQ-101`.
12. **Reviewers and CODEOWNERS.** `config/reviewers.yaml` has the four classes of the kit with one team,
    `maintainers`, mapped to the placeholder handle `@REPLACE-ME`. `.github/CODEOWNERS` is rendered from it by
    `reviewers.render_codeowners`, so `reviewers.py --check-codeowners` passes immediately. The placeholder does not
    make any check fail (warn only); init prints a notice naming `config/reviewers.yaml` and the placeholder. A
    check for it is a residual for `agk doctor` (see Residual).
13. **ADR-0001.** `docs/adr/0001-adopt-agk.md` records the install: kit version, date, layout, the protected paths, the
    reviewer model, and the ruleset (rule 19). Its Status is `Proposed`; maintainers flip it to `Accepted` in the live-proof PR (rule 24). Its text contains every entry of the
    installed `config/protected-paths.txt`, so the target's first pull request is covered by an ADR that names every changed class.
14. **Version stamp and dates.** The installed `agk.toml` carries `mode = "init"`, `version`, `installed` (a
    `YYYY-MM-DD` date), `default_branch`, `test_dirs = ["tests"]`, `lint_paths` and `project_tests`; the installed
    `pyproject.toml` carries no `[tool.agk]` table. The first run takes the date from the UTC clock; a later run reads
    `installed` (and `default_branch`) from the existing `agk.toml`, or from `[tool.agk]` in the `pyproject.toml` of an
    older install, and renders the same values, so output stays identical.

### Idempotence, refusal, dry run

15. **Idempotence.** Run again on an unchanged install, init writes nothing, prints `nothing to do`, and exits 0.
    A file that already equals what init would write is "unchanged". Modification times do not change.
16. **Refusal.** A file in the plan that exists and differs is never overwritten. Init lists every such file with its
    path class, writes nothing at all (checking happens before writing), and exits 1. This includes an existing
    `pyproject.toml`, `Makefile`, `CLAUDE.md` or `.gitignore`; merging existing repositories is K2 `agk adopt`.
    A partial install (some files present and equal, others missing) completes, since equal files are unchanged.
17. **Dry run.** `--dry-run` prints the plan, one line per file marked `create`, `unchanged` or `conflict`, writes
    nothing, and exits with the code the real run would (0 or 1).
18. **Tests directories.** `tests/kit/` (tests of the checks) is installed so the target can test its own checks and
    `make test` is green. The kit-only tests, `tests/kit_dev/test_init.py` and `tests/kit_dev/test_kit_manifest.py`,
    are not installed. `make test` runs `agk-test` (the kit tests, with `tests/kit_dev` when it exists) and then
    `agk-project-test`, which runs the `project_tests` command of `agk.toml` (for an init repository `python3 -m
    pytest tests -q --ignore=tests/kit_dev`, treating pytest exit 5, nothing collected, as success). `testpaths` in
    `[tool.pytest.ini_options]` is `["tests"]` in the kit's and the installed `pyproject.toml`. A test added under
    `tests/` in a target is collected and run by `make test` and by the CI step `agk-project-test`; a failing one
    makes both fail.
19. **Branch-rule instructions.** After a run (and in `--dry-run`) init prints, for the user to apply by hand, the
    ruleset `main` and repository settings of ADR-0001 decision 3: Active; no bypass; target the default branch;
    restrict deletions; require linear history; require a pull request (0 approvals, dismiss stale approvals, squash
    only); block force pushes; required status check `governance`; allow auto-merge; auto-delete head branches. The
    text comes from `kit/templates/branch-rules.txt`; a test keeps it equal to the kit's ADR-0001 decision 3 except
    that the phrase `The ruleset main` reads `The ruleset for the default branch` (ADR-0009). After the ruleset text
    init prints the scanner-exclusion block of `kit/templates/scanner-excludes.txt`: the bandit, flake8, pylint and
    mypy settings that exclude `scripts/agk`, `tests/kit` and `.claude/hooks`. It is printed only, nothing is written,
    and a test keeps the printed block equal to the template and to the README's "Existing scanners" section
    (ADR-0010).
    Init does not configure GitHub.

### Neutrality

20. **Installed text is neutral.** No rendered template and no verbatim file contains `gbvraju`, a day marker
    (`day-<digit>`), a milestone name (`K0`..`K4`), a kit PR number (`PR #<digits>`) or a `Q-K<digit>` id; rendered
    templates also contain no ADR number other than `ADR-0001`. The tool name `agk` is allowed. A test scans the
    rendered output and every verbatim file for these patterns. `CLAUDE.md` currently cites a day marker; PR #6 rewrites
    it neutrally (same rules, no day or milestone references), covered by ADR-0004.

### Protected paths

21. **Installed protected list.** The installed `config/protected-paths.txt` is `constitution/`, `config/`, `.claude/`,
    `.github/`, `docs/requirements.md`, `CLAUDE.md`, and also `scripts/agk/`, `tests/kit/`, `Makefile`,
    `pyproject.toml`, `agk.mk`, `agk.toml`, so a target cannot change its checks, their tests or its build files without an ADR that names
    the class. The installed `reviewers.yaml` `protected` class lists the same entries (`reviewers.py --check` equality).
    The kit adopts the same entries via ADR-0004 in PR #6; the kit's own list is those entries plus the kit-only
    `kit/` and `tests/kit_dev/`. The installed list is rendered from `kit/templates/protected-paths.txt`; a test
    asserts the kit's list equals the template plus `kit/` and `tests/kit_dev/`.

### Markers

22. **Undefined ids never fail.** A test marker `REQ-nnn` for an id that `docs/requirements.md` does not define is
    ignored by every check and by the traceability matrix; it never causes a failure. (The installed `tests/kit/`
    carries markers for kit-defined ids a project may not define.) A test in `tests/kit/test_check_requirements.py`
    covers it.

### Proof

23. **Tests (`tests/kit_dev/test_init.py`)** build a fresh git repository in `tmp_path` with one commit (a README), run init,
    then run `make governance` and `make test` in the target: both green. A second run: no change (file hashes and
    mtimes equal), message `nothing to do`. A pre-existing differing file: exit 1, the file listed, nothing else
    written. `--dry-run`: no file created. A target without git: notice, exit 0. The kit-self-target and
    Python-version refusals are tested.
24. **Live proof** is a maintainers' step: init into a throwaway public repository, commit, open a first PR with a
    two-item brief, flip ADR-0001 to `Accepted` in that PR, and show the `governance` check green on GitHub. The repository name and access are the
    maintainers' to choose; the agent does not create it.

## Tests

- Rules 1–5, 15–17: `tests/kit_dev/test_init.py`, marker `REQ-009 AC1`.
- Rules 6–14, 18–21, 23: `tests/kit_dev/test_init.py` and `tests/kit_dev/test_kit_manifest.py`, marker
  `REQ-009 AC2` (governance green after init).
- Rule 22: `tests/kit/test_check_requirements.py`, marker `REQ-003 AC2`.
- Rule 24: the live proof, recorded in `docs/runs/`.

## Residual

- 2026-10-14: nothing flags the placeholder team `@REPLACE-ME` after init; `agk doctor` (later) should report it
  until `config/reviewers.yaml` is edited.
- 2026-10-14: installed repositories inherit the unpinned action tags and the gitleaks-action licence note; SHA
  pinning is at K1 exit.
- 2026-10-14: a target that already has `pyproject.toml`, `Makefile`, `CLAUDE.md` or `.gitignore` is refused until
  K2 `agk adopt`.
