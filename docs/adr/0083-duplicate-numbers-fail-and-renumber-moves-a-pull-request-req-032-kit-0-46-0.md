# ADR-0083: duplicate numbers fail and renumber moves a pull request's numbers (REQ-032 part a, SPEC-0025), kit 0.46.0

- Status: Accepted
- Date: 2026-10-24
- Deciders: maintainers
- Related: ADR-0082, ADR-0081
- Requirements: REQ-032

Protected classes: `.claude-plugin/`, `.github/`, `agk.mk`, `agk.toml`, `kit/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`

## Context

SPEC-0025 (Approved, #140) lets a team run independent pull requests in parallel. Two pull requests that each start from the same default branch both take the next free requirement, spec and ADR numbers;
the second to merge collides. This part (a) builds rules 1 and 2 (AC1 and AC2): a governance check that fails on a duplicate number, and a command that moves a pull request's own numbers. The tests were written
first and run on unchanged `main` (16 failed; the output is in the pull request body).

## Decision

1. **The check**: `scripts/agk/check_numbers.py` (installed verbatim) fails when two requirements in `docs/requirements.md`, two specs or two ADRs carry the same number in the checked-out tree, naming the rule
   and the id and never a title (`FAIL numbers: rule 1: ...`; `ok numbers`). It reads files only. It is an eleventh step of `agk-governance` and of the workflow; a local `make governance` prints ten `ok` lines
   and the `skipped` line. Duplicate requirement ids were already refused by `check_requirements.py`; the new check names all three kinds under one rule, so a duplicate requirement fails both steps.
2. **The command**: `python3 scripts/agk/intake.py renumber <id> [--ref REF]` takes `REQ-nnn`, `SPEC-nnnn` or `ADR-nnnn` of the pull request's own, finds the requirement, spec and ADR the pull request added
   (against the merge base with the default branch), moves them to the next free numbers on `origin/<default branch>` (several own requirements keep their order and move in one pass), renames the added files with
   `git mv`, rewrites the ids (`REQ-`, `SPEC-`, `ADR-`, the spec's question family `Q-S<spec>-n`, the `req-nnn` of an ADR file name and the numbers in `docs/specs/` and `docs/adr/` paths) in the files it added
   and in the lines it added to other files, and changes no other line. It prints what it moved, prints `nothing to move` when the numbers are already the next free ones (a second run), and refuses when the work
   tree is not clean or the id is not the pull request's own. It makes no network call: the default branch is read from the ref, as `ids` does.
3. **Amendment 43** (`docs/runs/proposed-spec-amendments-43.md`) is applied to SPEC-0012 (the intake script gains `renumber`). The guides say ten checks.
4. **Tests, first** (`tests/kit/test_numbers.py`, installed; `tests/kit_dev/test_renumber.py`, kit-only): unique and duplicate numbers of the three kinds, the message, no network import; `renumber` on a branch behind
   a merge that took the same numbers, the rewrites and renames, nothing of the default branch touched, two own requirements, idempotence, the refusals. The governance step counts in `tests/kit/test_workflow.py`
   and `tests/kit_dev/test_init.py` follow the eleventh step.
5. **Kit 0.46.0**: the manifest `kit_version` and the new verbatim file, the hashes, the plugin version and `version` in this repository's `agk.toml` (ADR-0050 decision 7).

## Consequences

- A project that upgrades gets the check; a collision with the default branch fails the pull request's governance run, and `renumber` is the fix.
- Parts (b) and (c) follow with their own kit bumps.

## Residual

None.
