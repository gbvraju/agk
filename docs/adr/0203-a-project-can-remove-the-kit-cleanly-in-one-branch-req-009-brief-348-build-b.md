# ADR-0203: a project can remove the kit cleanly in one branch (REQ-009, brief 348 build b)

- Status: Proposed
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0196
- Requirements: REQ-009

Protected classes: `scripts/agk/`, `skills/`, `tests/kit/`, `tests/kit_dev/`

## Context

Brief #348 asks for a safe way out of the kit: pause it, then remove it in one reviewable pull request that deletes only the
files the kit installed unchanged, keeps the project's own work, and says what to undo on GitHub by hand. Build (a), pause and
resume, merged as ADR-0196. The conductor's split field note makes this build (b): the removal (answers 2 to 4), the
`/agk:uninstall --pause` command that writes the line of build (a), answer 5 "no kit installed" and the tests of answer 6. The
refusal of `session.py` while paused is build (c), which closes the brief.

## Decision

1. **One command, a dry run by default (answers 1 and 2).** `scripts/agk/uninstall.py TARGET [--write] [--remove-docs]` and
   `TARGET --pause [--write]`, skill `/agk:uninstall`. It is kit-only, like `upgrade.py`: it runs from the plugin or a kit
   checkout, never from the target's copy, which the removal deletes; it is not in `kit/manifest.json`, and the manifest test
   lists it among the kit-only scripts (Q-348-9). Without `--write` it writes nothing and makes no branch. It needs a git work tree and
   refuses the kit checkout itself. Standard library and `git` only; it never calls `gh`.
2. **`--write` builds the branch, uncommitted (answer 2).** It refuses a work tree with changes or an existing branch of the
   name, makes one new branch (`agk-uninstall`, or `agk-pause`), writes the change there and commits nothing: the person reviews,
   commits, pushes and opens one pull request, which git can revert (Q-348-5).
3. **Deleted: kit files that match a released copy (answers 2 and 6).** A path any release row of `kit/hashes.json` lists is
   deleted when its bytes, CRLF read as LF, equal a digest that any row lists for it (verbatim, a template, or a marked block
   written whole), so a project installed at an older release is read by that release's row. `.github/CODEOWNERS` is deleted
   when it equals what the kit generates from the project's `config/reviewers.yaml`. A deleted script's bytecode in
   `__pycache__/` goes with it, and each directory the deletion emptied is removed.
4. **The kit's own lines only (answer 2).** In a file that also holds the project's lines (`.gitignore`, `.gitattributes`,
   `CLAUDE.md`, the pull request template, `CODEOWNERS`), only an agk block that a release shipped is taken out; a file left with
   no other line is deleted. When `agk.mk` is deleted and the project keeps a `Makefile`, the line `include agk.mk` is removed
   from it and nothing else. `agk.toml` is deleted when every top-level key and table in it is a setting the kit reads (its
   defaults, its templates' lines, set or commented out, and `version`, `installed`, `mode`, `paused`, `experimental_reviewer`);
   a file with any other key is listed and kept, never edited line by line (Q-348-6). The `.claude/` entries are the kit's
   agents, hooks and `settings.json`, removed as whole files by rule 3 (Q-348-7).
5. **A changed kit file is listed, not deleted (answer 2).** A kit path whose content matches no released copy, a changed or
   broken block, a symlink or a non-file is printed as `changed <path> (path class <class>: <why>; kept for you to decide)`;
   the message names the path class, never the content.
6. **The project's own work is kept (answer 3).** `docs/requirements.md`, `docs/build-state.md`, `constitution/vision.md` and
   everything under `docs/adr/`, `docs/specs/`, `docs/briefs/`, `docs/runs/`, `docs/design/` and `tests/` are never deleted or
   edited, even where they equal a kit template; the kit's `TEMPLATE.md` files under `docs/adr/`, `docs/specs/` and
   `docs/briefs/` are the kit's and follow rule 3. `pyproject.toml` is kept and printed as `kept` (Q-348-8). `--remove-docs`
   prints each of those documents as `remove by hand: <path>`; the tool never deletes them.
7. **GitHub, printed only (answer 4).** The output ends with the ruleset to delete or relax, by the name in the kit's
   `kit/templates/ruleset.json`; the kit's labels (the router's seven `agk:*` states, `agk-brief`, `agk-conductor`,
   `agk-shadow`, `agk-drift-audit`, `agk-metrics`, `agk-product-report`); the issues it opened (the red-branch issue by its
   title, and the issues labelled `agk-drift-audit`, `agk-metrics` and `agk-product-report`); and the plugin removal commands
   `claude plugin uninstall agk@agk` and `claude plugin marketplace remove agk` (verify) (Q-348-10). The tool does none of them.
8. **Reviewable (answer 2).** Like the upgrade, the output names the protected classes of every deleted or edited path and
   prints an ADR skeleton; the person writes the ADR. `--pause` adds the top-level line `paused = true` before the first line
   that is neither blank nor a comment (or replaces a top-level `paused = false`), checks with `tomllib` that the result is
   paused, prints the skeleton for `agk.toml` and says nothing is deleted; a paused project has nothing to do; a bad value is
   refused by the setting's name.
9. **Doctor: no kit installed (answer 5).** A git work tree with no `agk.toml`, no `[tool.agk]` stamp in `pyproject.toml` and
   none of the kit's files (`agk.mk`, `scripts/agk`, the governance, proof and router workflows, the stop hook) is reported as
   `no kit installed` (text: `agk doctor none`, one line, `summary: no kit installed`; `--json`: `"state": "no kit installed"`,
   no checks), exit 0, with no read of GitHub. Anything else without `agk.toml` keeps the refusal of SPEC-0006 rule 13
   (Q-348-4).
10. **Tests first (answer 6).** `tests/kit_dev/test_uninstall.py` (a fixture kit with two release rows, and one real install of
    this checkout) and `tests/kit/test_doctor_no_kit.py`: pause and resume, removal of unchanged files only, a changed kit file
    listed, the project's documents kept, a dry run that writes nothing, the GitHub list printed with no `gh` call, and a project
    at an older release. `tests/kit_dev/test_distribution.py` and `test_kit_manifest.py` list the new skill and script.

## Consequences

A person can leave the kit in one reviewed pull request that git can revert, with every changed file and every GitHub setting
named for them to decide. The removal pull request deletes the kit's workflows, so the ruleset's required checks cannot report
on it: relaxing or deleting the ruleset (printed first in the GitHub list) comes before merging it.

## Residual

- 2026-10-30: Q-348-4: SPEC-0006 rule 13 (Approved) says a missing `agk.toml` is a refusal; answer 5 says the doctor reports
  "no kit installed" after removal. Reading taken: both hold, by the narrow condition of decision 9; an amendment of rule 13 is
  the reviewers' to propose.
- 2026-10-30: Q-348-5: "builds the branch" is read as a new branch with the change uncommitted, as the upgrade never commits.
- 2026-10-30: Q-348-6, Q-348-7, Q-348-8: `agk.toml` whole or kept; `.claude/` entries as whole files; `pyproject.toml` kept.
- 2026-10-30: Q-348-9: `kit/manifest.json` is unchanged: the script is kit-only, as `upgrade.py` is.
- 2026-10-30: Q-348-10: the plugin removal commands are marked (verify).
