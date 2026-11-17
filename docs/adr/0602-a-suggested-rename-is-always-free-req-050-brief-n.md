# ADR-0602: A suggested rename is always a free name

- Status: Proposed
- Date: 2026-11-17
- Deciders: maintainers
- Related: brief #1441, brief #1425, ADR-0598, ADR-0388, ADR-0583, Q-1425-1
- Requirements: REQ-050

Protected classes: `scripts/agk/`, `tests/kit/`, `.claude/`, `config/`

## Context

Brief #1425 started from a conductor fix line that proposed renaming a folder to a name a running brief already used.
ADR-0598 made `plan_names.py` give free names and refuse a held `Adds:` entry, but nothing checked the name a verdict
suggests: `conductor.py check-verdict` read the verdict's shape only. Q-1425-1 asked for a rule line or a check; the
owner chose neither, so brief #1441 takes both, the check first. A review gap of #1439 found that `plan_names.py impact
src/gaps1` also listed a brief naming only `src/gaps10`.

## Decision

1. `conductor.py check-verdict FILE [--pr N] [--root DIR] [--open-briefs FILE]` reads every numbered fix item and every
   `MALFORMED:` line of the verdict for `rename <old> to <new>`, the one form of a rename. A `<new>` that the default
   branch's tree, another open brief's `Adds:` (or a `Touches:` at or below it) or a file an open pull request adds
   holds, by the matching of ADR-0598, is refused with `brief #1441 answer 1: item <n> renames to <new>, held by
   <holder> (<their path>); free: <name>`, the free name from `plan_names.free` at the holder's level.
2. With `--pr N` the pull request's own brief (`Brief: #n`) and its pull requests hold nothing.
3. The open briefs come from `--open-briefs FILE` or the plan's read cache, as `check_brief.py` reads them; never by a
   request. With neither, the tree alone is compared. A verdict with no rename reads nothing more than before.
4. `.claude/agents/conductor.md` says in one line, outside any list, that a rename takes its name from `plan_names.py
   next --base <feature>-m<milestone>-<part>` and is written in that form; the conductor's word budget is raised by the
   standing ruling of ADR-0583 (no new rule line).
5. `plan_names.py impact PATH` matches a path only as a whole segment: at a `/`, or at the end of the path.
6. The plan's `MALFORMED:` line suggests no name of its own; the only name the plan suggests is the `CLASH:` line's,
   from `plan_names.free` (no change).

## Consequences

A fix list cannot send a builder to a name another brief holds without the guard's check saying so, with a free name to
use instead. A rename written in other words is not read; the conductor's line names the one form.

## Residual

- A rename in prose (`move src/a under src/b`) is not read by the check.
