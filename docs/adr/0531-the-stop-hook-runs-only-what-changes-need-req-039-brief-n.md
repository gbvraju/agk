# ADR-0531: The stop hook runs only the checks a session's changes need

- Status: Accepted
- Date: 2026-11-14
- Deciders: maintainers
- Related: brief #1254, plan #661, ADR-0438 (brief #1029), session rule 31
- Requirements: REQ-039

Protected classes: `.claude/`, `agk.mk`, `agk.toml`, `scripts/agk/`, `tests/kit/`, `kit/`

## Context

`.claude/hooks/stop_check.py` ran the whole `make -f agk.mk agk-governance` at the end of every Claude turn
(timeout 300 s). On a project of 652 briefs on a 4-core cloud PC (kit 0.64.2) that took 53 s for a builder
and 4 min 48 s for the conductor, which changes no file at all. Governance still runs in full where it gates:
`prepush.py` before every push, CI's `governance` job, and the conductor's review. The owner's word
(2026-11-14 19:07 IST): "File it".

## Decision

1. The hook reads what the session changed with local git only: `git status --porcelain -z
   --untracked-files=all` (both sides of a rename) and `git diff --name-only <base>...HEAD`, where `<base>` is
   `origin/<default_branch>`, else `<default_branch>`. With no changed file it allows the stop at once, runs
   no check and reads no pull request body.
2. With changes it runs only the governance checks whose inputs the changed paths touch.
   `scripts/agk/governance_map.py`, an installed module, holds the commands of the `agk-governance` recipe in
   its order (a test compares them with `agk.mk`), a set that runs for every change (the protected-changes,
   neutrality, build-state, pull-request-mode and final-clearance checks, which read the whole diff or every
   tracked file), and a map from a path or folder to the further checks that read it (for example
   `docs/plan/` and `docs/sources/` to `check_plan.py`). A path that no entry names, or changes that git cannot
   read (no repository, no default branch), run the full `make -f agk.mk agk-governance`, as before. Only
   documentation and configuration paths are mapped; code and tests run the full set. A selected check that
   is red blocks the stop with its output, and the checks run in the recipe's order and stop at the first red
   one, as `make` does.
3. `[flow] stop_check` of `agk.toml` is `"changed"` (the default), `"full"` (the full set on every stop, as
   before this decision) or `"off"` (no check). `config.stop_check_mode(root)` refuses any other value, and
   `"off"` when `review_mode` is `"solo"`, which has no other gate before a push, naming `setting:
   flow.stop_check` and never the value; the hook then prints the refusal and works as `"changed"`.
4. Each run prints one line on standard error: `stop check: <n> checks for <m> changed files, <s> s`,
   `stop check: no changes`, `stop check: off`, `stop check: <n> checks (full set), <s> s` in `"full"` mode,
   or `stop check: <n> checks (changes not read), <s> s`; a blocking run puts the line first in its reason.
   Standard error, not standard output, because Claude Code reads a Stop hook's standard output as its JSON
   decision (verify).

5. This repository's `[[testing.map]]` in `agk.toml` maps `scripts/agk/governance_map.py` to its tests, and
   the `scripts/agk/config.py` entry also selects `tests/kit/test_stop_check_changed.py`.

## Consequences

A turn that changes nothing costs no check; a documentation change runs the always set and the checks of its
folders. A check the map leaves out for a path it does not read can no longer turn a stop red, but every push
still runs governance in full (`prepush.py`, CI), so nothing reaches the default branch unchecked. A new
governance step in `agk.mk` fails the map test until the map lists it.

## Residual

- 2026-12-14: measure the stop time again on the project of the brief and record it under the brief.
