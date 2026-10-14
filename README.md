# agk — Agentic Governance Kit

agk lets a team adopt Claude Code agents without drift. It installs the law (committed settings, hooks, CI
checks, branch rules) and the method (requirements, specs, ADRs, reviewer groups, briefs, audits) that keep agent
output consistent from the first feature to the last. See `constitution/vision.md` and
`constitution/principles.md`.

Status: **K0 — self-governed skeleton** (see `docs/adr/0002-milestones.md`). The kit governs its own build.

## Run the checks

    make governance   # all checks against the base branch (origin/main by default)
    make test         # tests of the checks (needs pytest)
    make lint         # ruff

Set `AGK_BASE=<ref>` (or pass `--base`) to compare against another base. In CI the pull-request base SHA is used.
`python3 scripts/agk/traceability.py` prints the requirement-to-test matrix to stdout; it is never committed.

Licence: Apache-2.0.
