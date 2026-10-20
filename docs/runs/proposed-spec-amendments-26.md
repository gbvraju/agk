# Proposed spec amendments 26 (lean install: SPEC-0001, SPEC-0002, SPEC-0006, SPEC-0008)

Date: 2026-10-20 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0052. The paths:
`docs/specs/0001-agk-init.md`, `docs/specs/0002-agk-adopt.md`, `docs/specs/0006-doctor.md`, `docs/specs/0008-upgrade.md`.

The maintainers' brief of 2026-10-20 stops installing the kit's own tests in a project (measured: 559 of the 611 files, 526,467 of the 750,024 bytes of an init). The items below change only what that
makes false or adds. `docs/specs/0005-distribution.md` rule 2 (the repository works without the plugin) is read and needs no change.

1. **SPEC-0001, the installed set and rule 18.** The verbatim set no longer contains `tests/kit/`; rule 18 says the kit's own tests are not installed, that `agk-test` runs them when `tests/kit/pytest.ini` exists and otherwise
   prints a notice and succeeds, and that the `project_tests` default of an init repository is `[ -d tests ] || exit 0; python3 -m pytest tests -q --ignore=tests/kit_dev; ...` (a fresh project has no `tests/`, so pytest would
   otherwise fail with exit 4). Rule 22's parenthesis about the installed `tests/kit/` says the tests are not installed. The integrity of the installed checks is the doctor's hash comparison and the protected class
   `scripts/agk/`.
2. **SPEC-0002, rules 4, 6, 9 and 10.** `tests/kit/*` leaves the created set; `.gitattributes` joins `.gitignore` as a block-appended file (and as the `.gitattributes` row of the file table); rule 6 and rule 10 say that the kit's
   tests are not installed and that `lint_paths` defaults to `scripts/agk .claude/hooks`, a missing path being skipped.
3. **SPEC-0006, rule 14.** `tests/kit/test_doctor.py` and its fixtures are in the kit repository and are not installed.
4. **SPEC-0008, rules 7 and 15.** The directories a deletion empties are removed, but never the target root **or a directory directly under it**: a project whose only `tests/` content was the kit's own tests keeps `tests/`.
   An absent block file that no release has shipped (`.gitattributes`) is added to an existing file of the project as one marked block (the action `replace`, detail `agk block added`), as adopt does.
5. **A fresh install does not mention `tests/kit/` (maintainers' ruling on Q-K4-207, 2026-10-20).** SPEC-0001 rule 21 and SPEC-0002 rule 12: the installed protected list, the `protected` and `kit` classes of the installed
   `reviewers.yaml` and the rendered `CODEOWNERS` no longer name `tests/kit/` (the kit's own list is the installed list plus `tests/kit/`, `kit/` and `tests/kit_dev/`); SPEC-0001 rule 17: the printed scanner exclusions name
   `scripts/agk` and `.claude/hooks` only; SPEC-0008 rule 16: the classes an upgrade writes no longer include `tests/kit/`. The installed `CLAUDE.md` rule 4, `.claude/settings.json`, `agk.mk`, `agk.toml`, the ADR-0001
   template and the installed scripts carry no `tests/kit` text either; a test greps the tree of a fresh init and of a fresh adopt for it. Existing installs get the verbatim files through an upgrade; a project's own
   files (`config/`, `agk.toml`, `docs/adr/0001-adopt-agk.md`) are never rewritten.

