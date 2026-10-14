# SPEC-0001: agk init

- Status: Draft
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
   content or a setting value (rule 8).
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
   `.github/PULL_REQUEST_TEMPLATE.md`, `CLAUDE.md`, `Makefile`, `.gitignore`, `config/protected-paths.txt`,
   `constitution/principles.md`, `docs/adr/TEMPLATE.md`, `docs/specs/TEMPLATE.md`, `docs/briefs/TEMPLATE.md`, every
   check and helper in `scripts/agk/` except `init.py` (`common.py`, `check_*.py`, `reviewers.py`,
   `traceability.py`), and `tests/kit/` (rule 17).
8. **Template set** (project-specific): `constitution/vision.md`, `docs/requirements.md`,
   `docs/adr/0001-adopt-agk.md`, `config/reviewers.yaml`, `config/neutrality.txt`, `docs/build-state.md`,
   `docs/runs/decisions-log.md`, `pyproject.toml`. Templates may use these variables only: `{{project}}` (TARGET's
   directory name), `{{date}}` (rule 14), `{{kit_version}}`.
9. **Duplication versus divergence.** The verbatim set is not duplicated under `kit/`: the manifest points at the kit's
   own files, so they cannot diverge. Templates are the only duplicated text. Tests (rule 20) fail when a file the kit
   uses as law is missing from the manifest, when a manifest path does not exist, or when a template does not pass
   neutrality (rule 18).

### Target result

10. **File list.** After a successful run TARGET contains exactly the verbatim and template files above, plus
    `.github/CODEOWNERS` (rule 12); nothing else is created. Files already in TARGET and not in the plan
    (for example `README.md`, `LICENSE`, product code) are never read, changed or listed as conflicts.
11. **Seeded requirements.** The target's `docs/requirements.md` contains `REQ-001`..`REQ-003` with the kit's own
    rules: protected paths change only with an ADR that names their class; agents never merge or bypass checks; every
    requirement is traceable to tests. Each is `- Status: planned` (init marks nothing done). The wording drops
    references to tooling that does not exist yet. Project requirements start at `REQ-101` (Q-K1-6).
12. **Reviewers and CODEOWNERS.** `config/reviewers.yaml` has the four classes of the kit with one team,
    `maintainers`, mapped to the placeholder handle `@REPLACE-ME`. `.github/CODEOWNERS` is rendered from it by
    `reviewers.render_codeowners`, so `reviewers.py --check-codeowners` passes immediately. Whether the placeholder
    makes a check fail is Q-K1-5; until decided, init prints a notice naming `config/reviewers.yaml` and the placeholder
    and the checks do not fail on it.
13. **ADR-0001.** `docs/adr/0001-adopt-agk.md` records the install: kit version, date, layout, the protected paths, the
    reviewer model, and the ruleset (rule 16). Its Status is `Proposed` (Q-K1-8). Its text contains every entry of the
    installed `config/protected-paths.txt`, so the target's first pull request is covered by ADR-0003-style cover.
14. **Version stamp and dates.** The installed `pyproject.toml` carries `[tool.agk]` with `version`, `installed`
    (a `YYYY-MM-DD` date), and `test_dirs = ["tests"]`. The first run takes the date from the UTC clock; a later run
    reads `installed` from the existing `pyproject.toml` and renders the same date, so output stays identical.

### Idempotence, refusal, dry run

15. **Idempotence.** Run again on an unchanged install, init writes nothing, prints `nothing to do`, and exits 0.
    A file that already equals what init would write is "unchanged". Modification times do not change.
16. **Refusal.** A file in the plan that exists and differs is never overwritten. Init lists every such file with its
    path class, writes nothing at all (checking happens before writing), and exits 1. This includes an existing
    `pyproject.toml`, `Makefile`, `CLAUDE.md` or `.gitignore` (Q-K1-9); merging existing repositories is K2 `agk adopt`.
    A partial install (some files present and equal, others missing) completes, since equal files are unchanged.
17. **Dry run.** `--dry-run` prints the plan, one line per file marked `create`, `unchanged` or `conflict`, writes
    nothing, and exits with the code the real run would (0 or 1).
18. **Tests directory.** `tests/kit/` is installed so the target can test its own checks and `make test` is green
    (Q-K1-6 covers marker collisions). Dropping it would leave `make test` with no tests.
19. **Branch-rule instructions.** After a run (and in `--dry-run`) init prints, for the user to apply by hand, the
    ruleset `main` and repository settings of ADR-0001 decision 3: Active; no bypass; target the default branch;
    restrict deletions; require linear history; require a pull request (0 approvals, dismiss stale approvals, squash
    only); block force pushes; required status check `governance`; allow auto-merge; auto-delete head branches. The
    text comes from `kit/templates/branch-rules.txt`; a test keeps it equal to the kit's ADR-0001 decision 3 (rule 20).
    Init does not configure GitHub.

### Neutrality

20. **Templates are neutral.** No rendered template contains `gbvraju`, a milestone name (`K0`..`K4`), a kit PR
    number, a `Q-K` id, or an ADR number other than `ADR-0001`. The tool name `agk` is allowed. Verbatim files carry no
    person or handle either (`gbvraju` absent).

### Proof

21. **Tests (`tests/kit/test_init.py`)** build a fresh git repository in `tmp_path` with one commit (a README), run init,
    then run `make governance` and `make test` in the target: both green. A second run: no change (file hashes and
    mtimes equal), message `nothing to do`. A pre-existing differing file: exit 1, the file listed, nothing else
    written. `--dry-run`: no file created. A target without git: notice, exit 0. The kit-self-target and
    Python-version refusals are tested.
22. **Live proof** is a maintainers' step: init into a throwaway public repository, commit, open a first PR with a
    two-item brief, and show the `governance` check green on GitHub. The repository name and access are the
    maintainers' to choose; the agent does not create it.

## Tests

- Rules 1–5, 15–17: `tests/kit/test_init.py`, marker `REQ-009 AC1`.
- Rules 6–14, 18–20: `tests/kit/test_init.py` and `tests/kit/test_kit_manifest.py`, marker `REQ-009 AC2`
  (governance green after init).
- Rule 21: the test run itself. Rule 22: the live proof, recorded in `docs/runs/`.
