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
`python3 scripts/agk/traceability.py` prints the requirement-to-test matrix to stdout; it is never committed.

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

Licence: Apache-2.0.
