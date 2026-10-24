# ADR-0104: the conductor role file and its guard hook (REQ-037 part b2, SPEC-0030 rule 6)

- Status: Proposed
- Date: 2026-10-24
- Deciders: maintainers
- Related: ADR-0100, ADR-0102, ADR-0098
- Requirements: REQ-037

Protected classes: `.claude/`, `kit/`, `tests/kit/`, `tests/kit_dev/`

## Context

SPEC-0030 (Approved, #167) rule 6 and the verdict on #172: this is build (b2), the conductor role file and its guard, measured before it was started (about 60 lines of role file, 70 of guard and 330 of tests). The architect's seven pre-verdict steps on issue #163 are in the role file. The tests were written first (`tests/kit/test_conductor_guard.py`, `tests/kit_dev/test_conductor_role.py`; on the unchanged tree: 58 failed).

## Decision

1. **`.claude/agents/conductor.md`** (installed, verbatim): tools `Read, Grep, Glob, Bash`; reviews every open pull request of the queue by the architect's protocol (the block between the markers is the architect's, verbatim); posts one verdict comment on each; orders the queue by `Depends-on`; runs the seven steps before every verdict, in the order of the architect's comment; edits no file; never merges, tags or enables auto-merge.
2. **`.claude/hooks/conductor_guard.py`** (installed, verbatim): every write tool is refused everywhere; `Bash` only for read-only `git`, `gh api` GET, the one comment POST on the origin repository (`-f` fields only) and `date -u`; PATCH, PUT, DELETE, other POSTs, scripts and `make` are refused naming rule 6, never the command. It imports the judging of `git` and `gh api` from `architect_guard.py` (Q-K4-266).
3. Flow mode: no version bump, one line under `## Unreleased` of `CHANGELOG.md`, manifest and hashes refreshed. Amendment 53 (`docs/runs/proposed-spec-amendments-53.md`) is applied to SPEC-0030; it also records that the learnings of issue #163 are later parts.

## Consequences

- A conductor session can read everything and post comments and nothing else; a verdict by it counts only when `verdict_authors` lists its account.
- `architect_guard.py` and `conductor_guard.py` must be installed together; both are in the manifest.

## Residual

None beyond SPEC-0030's.
