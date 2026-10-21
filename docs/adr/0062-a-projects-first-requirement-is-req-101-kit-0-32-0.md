# ADR-0062: a project's first requirement is REQ-101 (REQ-019, SPEC-0012), kit 0.32.0

- Status: Accepted
- Date: 2026-10-21
- Deciders: maintainers
- Related: ADR-0053, ADR-0060
- Requirements: REQ-019

Protected classes: `scripts/agk/`, `tests/kit_dev/`, `kit/`, `.claude-plugin/`, `agk.toml`

## Context

A project that installed the kit (agk.toml `mode` `init` or `adopt`) found that `intake.py ids` and `common.next_free_ids` gave it `REQ-004`, although the installed `docs/requirements.md` reserves
`REQ-001`..`REQ-099` for the kit and starts the project's requirements at `REQ-101` (SPEC-0001 rule 11). SPEC-0012 rule 2 fixed the rule as "highest + 1", which is right for this repository and wrong for a
project, whose seeded requirements are `REQ-001`..`REQ-003`. A project's intake therefore could not pass `intake.py check` with `REQ-101` (check C1 expected `REQ-004`) and could not start. It blocks the
portal and the first outside developer. The maintainers decided the defect is fixed now, before pull request A3 of the portal Part A (ADR-0060), not only recorded.

## Decision

1. **One function** (`scripts/agk/common.py`): `next_req_number(root, highest)` returns `highest + 1`, and in a project (agk.toml `mode` `init` or `adopt`) `max(highest + 1, 101)`, so a project gets
   `REQ-max(101, highest + 1)`. `PROJECT_FIRST_REQ = 101` is a named constant; `REQ-100` is left free. The kit's own repository has no `mode` and is unchanged.
2. **Every id comparison uses it.** `next_free_ids` calls it, and so do `intake.py ids`, `stub` and `check` (check C1 reads `next_free_ids`), `playbook.py` (its skeleton numbers). The `requirement` form of
   `new_spec.py` computed its own highest + 1 from the work tree; the script is stdlib-only (REQ-014 AC2: a test allows it `re`, `sys`, `datetime`, `pathlib` and nothing else), so it cannot import
   `common`: it restates the rule with the same constant and reads `mode` from `agk.toml` with a regular expression, and a test pins the constant equal to `common`'s and the ids equal (Q-K4-216).
3. **The mode is read from the work tree's agk.toml** with `load_config`, as every other setting is; the ids themselves are still read from the tree of the base (`--ref`), never the work tree.
4. **Amendment 29** (`docs/runs/proposed-spec-amendments-29.md`) is applied to SPEC-0012 rule 2 (the wording of `req`) and rule 11 (check C1).
5. **Tests, first** (`tests/kit_dev/test_project_req_ids.py`, new, kit-only): on an init target and an adopt target, the first id is `REQ-101`, an empty requirements file still gives `REQ-101`,
   `REQ-101` and `REQ-102` give `REQ-103`, `REQ-150` gives `REQ-151`, `new_spec.py requirement` agrees, and check C1 accepts a draft numbered `REQ-101` and refuses one that takes `REQ-004`; the kit's own
   repository (no `mode`, or `mode = ""`) still gives the highest plus one. They were run on unchanged `main` before any code (11 failed, 3 passed, the 3 being guards).
6. **Kit 0.32.0**: the manifest `kit_version`, the hashes of `common.py` and `new_spec.py`, the plugin version and `version` in this repository's `agk.toml` (ADR-0050 decision 7). No file is added to or
   removed from the manifest.
7. **Docs**: the existing-codebase guide's example requirement is `REQ-101`, not `REQ-004` (three places in step 3).

## Consequences

- A project's intake starts at `REQ-101` and passes `intake.py check`; the portal and the first outside developer are unblocked.
- A project that has already taken `REQ-004` by hand keeps it: the rule only decides the next id, and a project whose highest is above 101 continues from there.
- `new_spec.py` stays stdlib-only and restates the rule; it reads `mode` from `agk.toml` only (not from the legacy `[tool.agk]` table of `pyproject.toml`), so on a legacy install without `mode` in `agk.toml` it keeps highest + 1.

## Questions

| Id | Question | Reading taken |
| --- | --- | --- |
| Q-K4-216 | The brief wants every id comparison to use one function; `new_spec.py` must stay stdlib-only (REQ-014 AC2) and cannot import it | the rule is restated in `new_spec.py` with the same constant, and a test pins both: the constant equal and the ids equal on an init and an adopt target. Proposed for ruling. |

## Residual

- 2026-10-21: a project that took a kit id (`REQ-004`..`REQ-099`) before this fix is not renumbered or flagged by the kit (due 2026-12-31).
