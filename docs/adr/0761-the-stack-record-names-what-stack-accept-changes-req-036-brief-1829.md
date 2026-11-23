# ADR-0761: The stack record names what stack-accept changes, so the accepting change passes governance (REQ-036, brief #1829)

- Status: Proposed
- Date: 2026-11-23
- Deciders: maintainers
- Related: brief #1829, ADR-0228, ADR-0671, ADR-0680, ADR-0735, ADR-0760, SPEC-0029, SPEC-0072
- Requirements: REQ-036, REQ-069

Protected classes: `scripts/agk/`, `kit/`, `skills/`, `tests/kit/`, `tests/kit_dev/`

## Context

In a clean solo project, `engines.py stack-write`, `stack-check` and `stack-accept --option A` all agreed, and then the
project's governance failed the accepting branch: `FAIL protected-changes: protected path class 'agk.toml' changed
without an ADR that names it` (brief #1829, measured on main at e13f4f53 and again at 1d14d65). `stack-accept`'s second
commit changes `agk.toml`, and `check_protected_changes.covering_adrs` counts an ADR only when its text names every
changed class. `kit/templates/stack-adr.md` never named `agk.toml`; ADR-0228 decision 2 relied on the architect writing
it by hand, and since brief #1591 the accept is mechanical. In an adopted project the gates also write
`config/agk-baseline/` on that branch, and the foundation steps (`stack-files`, `layers.py --write-record`,
`front_door.py derive-write`) write protected paths without saying which classes. No test ran governance on what a kit
step writes.

## Decision

1. `kit/templates/stack-adr.md` has one plain header line `Protected classes: {{classes}}` after `- Requirements:`.
   `stack-write` fills it, each class in backticks, from the project's own `config/protected-paths.txt` (read from
   `--ref` or the default branch, else the working tree, as `check_protected_changes.main` reads it): the class each
   changed path first matches (`agk.toml`, and the record's own path when the project lists `docs/adr/`) and, in
   `mode = "adopt"`, also `config/` and `config/agk-baseline/`. A list that cannot be read is refused before anything
   is written: `rule 5: the protected path list cannot be read (path class config/)`. The helpers are
   `check_protected_changes.classes_met`, `step_classes` and `protected_line`; the check itself is unchanged (Q-1829-4).
2. `stack-accept` reads the record's `Protected classes:` line (plain or `- ` bullet). A Proposed record without it, or
   missing a class, gets the line added or completed in the first commit beside Status and Chosen, and the accept prints
   `added: Protected classes names <n> classes (setting: config/protected-paths.txt)` (Q-1829-1). In an adopted project
   it prints `next: run_gates.py --root . writes config/agk-baseline/ for the new gates; commit it in this pull request`
   and makes no third commit (Q-1829-3). After its commits it runs `check_protected_changes.py --base <default branch>`
   and prints its lines; a failure gives rc 1 and nothing more is committed.
3. `steward_owner.work_type_adr` writes its `Protected classes:` line with the same helper (`agk.toml` alone when the
   list cannot be read); nothing else in that record changes (Q-1829-2).
4. `engines.py stack-files`, `gates/layers.py --write-record` and `front_door.py derive-write` print, after what they
   wrote, one line `protected: <classes> (name them in this change's ADR)` from the project's list, never a value.
5. `skills/stack/SKILL.md` step 4 says the record's line is written by `stack-write` and names the adopted project's
   `next:` line.
6. `tests/kit/test_kit_step_governance.py` holds one table of every kit step that writes into a project. Each case runs
   the step in a scratch project of `init.py` or `adopt.py --unreleased`, adds what the step's own output says to add,
   and requires `ok protected-changes`; the settings that reach the check are cases of the accept, and two cases run
   the project's whole governance (plugin and full copy). A census of `scripts/agk/` fails for a write to a literal
   path of `agk.toml`, `config/`, `pyproject.toml`, `docs/architecture.md` or `docs/requirements.md` by a function that
   neither the table nor its list of writers held elsewhere names.
7. The three kit_dev stack tests whose shared fixture has no protected path list (`test_engines_stack.py`,
   `test_stack_adr_testing.py`, `test_stack_playbook.py`) copy the init list into it, since decision 1 refuses
   without one; `tests/kit_dev/` is named for that test-only change (the conductor's Answer on #1855).

## Consequences

The accepting pull request, the work-type pull request in an adopted project and the foundation build pass
`protected-changes` on their first run. A Proposed stack record written before this change is completed by the accept;
an Accepted one is never rewritten. A project whose protected path list cannot be read can no longer write a stack
record until it can.

## Residual

- 2026-11-23: the five writers listed as held elsewhere (`personal.upgrade`, `req_status.edit`, `setup.write_settings`,
  `uninstall.pause`, `wsl.make_pr`) are named with their reason and not run by the table. The census sees only literal
  targets, so a step that writes a protected path through a computed name (as `derive-write` does) is held by its row.
