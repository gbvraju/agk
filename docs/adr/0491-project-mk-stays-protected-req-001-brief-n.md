# ADR-0491: project.mk stays protected beside Makefile

- Status: Proposed
- Date: 2026-11-12
- Deciders: maintainers
- Related: brief #1155, issue #485, brief #390, ADR-0214
- Requirements: REQ-001

Protected classes: `scripts/agk/`, `agk.toml`, `kit/`, `tests/kit/`

## Context

Brief #390 (ADR-0214) moved a project's own make targets out of the kit's `Makefile` into `project.mk`, which the
kit's `Makefile` includes and an upgrade never writes. An upgrade refused over an edited `Makefile` says to move the
targets there (`PROJECT_MK_FIX` in `scripts/agk/upgrade.py`). The init templates `kit/templates/protected-paths.txt`
and `kit/templates/reviewers.yaml` protect `Makefile` but not `project.mk`, so following the fix line moved a
project's governance targets out of its protected paths. The pilot run of 2026-11-02 (issue #485) hit this and added
`project.mk` to its protected paths and reviewers by hand.

## Decision

1. The init templates list `project.mk` right after `Makefile`: in `kit/templates/protected-paths.txt` and in
   `classes.protected.paths` of `kit/templates/reviewers.yaml`, so the two still match (`reviewers.py --check`).
   The adopt templates, which protect no `Makefile`, are unchanged, and so is this repository's own `config/`.
2. `PROJECT_MK_FIX` gains one clause: "and, where Makefile is protected, add project.mk to config/protected-paths.txt
   and config/reviewers.yaml in the same pull request".
3. `docs/guides/getting-started.md` says it in the bullet that describes `project.mk`.
4. `tests/kit/test_project_mk_protected.py` tests the three, and the `[[testing.map]]` entry of `scripts/agk/upgrade.py`
   in `agk.toml` lists it.

## Consequences

Every new init project protects `project.mk`; an existing project is told by the upgrade's fix line to protect it in
the same pull request that moves its targets. The kit still never installs, hashes or writes `project.mk`.

## Residual

The `kit` class of `kit/templates/reviewers.yaml` also lists `Makefile` and is left as the brief names only the
protected class (Q-1155-1 reading). An existing project is not changed by an upgrade; the fix line only tells it.
