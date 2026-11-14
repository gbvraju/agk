# ADR-0538: A local router run writes an ignored pipeline file

- Status: Proposed
- Date: 2026-11-14
- Deciders: maintainers
- Related: SPEC-0036, ADR-0141, ADR-0534, brief #1263, brief #1272, plan #661
- Requirements: REQ-039

Protected classes: `scripts/agk/`, `kit/`, `tests/kit/`

## Context

ADR-0141 put the pipeline document at `pipeline.json` in the working directory, or at the file `AGK_PIPELINE_FILE`
names; the router workflow sets that variable to a file of the runner's temp directory and uploads it (SPEC-0036 rule
5). Since ADR-0534 the conductor runs `route.py --all` on every pass in local mode, where the variable is unset, so the
run left an untracked and unignored `pipeline.json` in the project root that a builder could commit. Brief #1263 answer
8 asked for this change; #1268 merged without it.

## Decision

1. `scripts/agk/route.py` `write_pipeline`: with `AGK_PIPELINE_FILE` unset or empty, the document is
   `.agk-pipeline.json` in the repository root (`git rev-parse --show-toplevel`, the root the run already reads), not the
   current folder; with it set, the path is unchanged. It is still written after every run that is not `--dry-run`
   (SPEC-0036 rule 2), and a failed write still fails no routing (rule 4).
2. `kit/templates/gitignore` and the kit's own `.gitignore` block carry the line `.agk-pipeline.json`, beside the other
   `.agk-*` lines, so `init.py` and `adopt.py` installs and `/agk:upgrade` ignore it.

The CI path, the workflow file, the artifact and schema 1 of the document do not change.

## Consequences

A router run by hand or by the conductor in local mode leaves no file for `git status` to show. A project that already
holds an untracked `pipeline.json` from an earlier run keeps it until a person deletes it; the router never reads it.
Tests: `tests/kit/test_pipeline.py` (a) the local file in the root and no `pipeline.json`, (b) a set path unchanged,
(c) `git check-ignore` matches in a temporary `init.py` and `adopt.py` install; the earlier pipeline and router tests
stay as they were. Protected path classes changed: `scripts/agk/` (`route.py`), `kit/` (`kit/templates/gitignore`)
and `tests/kit/` (`test_pipeline.py`).
