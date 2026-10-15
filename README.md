# agk — Agentic Governance Kit

agk lets a team adopt Claude Code agents without drift. It installs the law (committed settings, hooks, CI
checks, branch rules) and the method (requirements, specs, ADRs, reviewer groups, briefs, audits) that keep agent
output consistent from the first feature to the last. See `constitution/vision.md` and
`constitution/principles.md`.

Status: **K0 — self-governed skeleton** (see `docs/adr/0002-milestones.md`). The kit governs its own build.

## Run the checks

    make governance   # all checks against the base branch (the default branch in agk.toml)
    make test         # tests of the checks (needs pytest)
    make lint         # ruff over the kit paths in agk.toml

The kit's own commands are in `agk.mk` (`make -f agk.mk agk-governance | agk-lint | agk-test`); the `Makefile` is thin
aliases of them. Kit tests are collected only through `agk.mk` (they need `AGK_KIT_TESTS=1`).

Set `AGK_BASE=<ref>` (or pass `--base`) to compare against another base. In CI the pull-request base SHA is used.
`python3 scripts/agk/reviewers.py --codeowners` prints the rendered CODEOWNERS; with `--write` it writes the file (in an
adopted repository only the marked block). `python3 scripts/agk/traceability.py` prints the requirement-to-test matrix to stdout; it is never committed.

## Installing

1. Create the target repository empty (no files).
2. Make one first commit directly on the default branch (a PR needs a base branch); record it in the target's
   ADR-0001.
3. From a checkout of agk, run init as a maintainer-approved step (an agent session blocks running a cloned script
   until a maintainer authorizes it):

       python3 scripts/agk/init.py TARGET [--dry-run]

   Init never overwrites a differing file (it refuses and lists it) and a second run changes nothing.
4. Apply the printed ruleset and repository settings by hand on GitHub; init configures nothing there.

See `docs/specs/0001-agk-init.md` and `docs/runs/k1-live-proof.md`.

## Adopting an existing repository

    python3 scripts/agk/adopt.py TARGET [--dry-run]

Run from a checkout of agk as a maintainer-approved step. TARGET is an existing git work tree. Adopt touches no
product file: it creates its own files (`agk.mk`, `agk.toml`, `scripts/agk/`, `tests/kit/`, `.claude/`, `config/`,
`constitution/`, `docs/`, `.github/workflows/governance.yml`), appends one marked block to `.gitignore` and, when they
exist, to `CLAUDE.md`, `.github/CODEOWNERS` and `.github/PULL_REQUEST_TEMPLATE.md`, and refuses rather than overwrite.
The project's `Makefile`, `pyproject.toml` and tests are untouched. See `docs/specs/0002-agk-adopt.md`.

## Existing scanners

Project-wide scanners (bandit, flake8, pylint, mypy) that read the whole tree also read the kit's code. The kit's
subprocess calls carry justified `# nosec` comments and its type findings are fixed, so what remains for bandit is
the bare `assert` of the kit's tests (rule B101). Init and adopt print the exclusions below after a run and write
none of them (ADR-0010, `docs/runs/scanner-fix.md`):

```
Scanner exclusions (print only; the kit writes none of this). The kit's code under scripts/agk, tests/kit and
.claude/hooks is the kit's, not yours. If a scanner you run reads the whole tree, exclude those paths in your own
configuration:
  bandit:  bandit -r . -x ./scripts/agk,./tests/kit,./.claude/hooks
  flake8:  flake8 --extend-exclude scripts/agk,tests/kit,.claude/hooks
  pylint:  [tool.pylint.main] ignore-paths = ['^scripts/agk/.*$', '^tests/kit/.*$'] and ignore = ['.claude']
  mypy:    [tool.mypy] exclude = ['^scripts/agk/', '^tests/kit/', '^\.claude/hooks/']
```

Licence: Apache-2.0.
