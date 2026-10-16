# Proposed spec amendments 12 (SPEC-0008)

Date: 2026-10-16 (from `date -u`). Found while building SPEC-0008 (day 9, item D; ADR-0018). Approved specs change only
through a proposal like this one (principle 6). Nothing here is applied; until the maintainers apply it, the code is ahead
of the Approved text of the rules below.

## SPEC-0008 (`docs/specs/0008-upgrade.md`)

1. **Rule 5 and rule 11: an install stamped only in `pyproject.toml` (ruled: Q-K3-71, option (a)).** Kits 0.1.0 and 0.2.0
   wrote no `agk.toml`; the stamp is `version` and `installed` in `[tool.agk]` of `pyproject.toml`, and there is no `mode` (init
   only). The sandbox `gbvraju/agk-sandbox` is such an install (read on 2026-10-16: `[tool.agk] version = "0.1.0"` and no
   `agk.toml`). Rule 5 as Approved refused it, so criterion c ("the 0.1.0 sandbox upgrades") could not pass. The maintainers
   ruled option (a): when `agk.toml` is absent and `pyproject.toml` has a `[tool.agk]` table with `version`, the upgrade treats the
   target as mode init at that version; takes `installed` and `default_branch` from the stamp (or the template default); creates
   `agk.toml` from the kit's template with the kit's current version, as the last write and only when every other write
   succeeded (on a conflict, a refusal or an I/O error it is not created, so a re-run starts from the stamp again). It never writes
   `pyproject.toml`; it prints `legacy-stamp pyproject.toml [tool.agk]: obsolete after this upgrade; remove it in your own change`.
   Any other target without `agk.toml` is still refused. Built as ruled; the `agk.toml` line counts in `N files`, the summary reads
   `upgraded N files; agk.toml is created with version V`, and the `template-changed agk.toml` line is not printed for it.
   Proposed: replace the `agk.toml` precondition of rule 5 and add the legacy case to rule 11.
2. **Rule 2, regeneration and the commit list.** Built: the history is the first-parent history up to the merge base with the
   default branch (`AGK_BASE`, else `origin/<default>`), plus the working tree as the current version. A past version's row
   names exactly the commits at which its files changed (full SHAs); the current version's row is taken from the working tree
   and may name fewer commits (none, until the next bump), because the commit that releases it does not exist yet. A shallow
   clone is a failure. `kit_hashes.py --check` (default) and `--write` are the interface. Proposed: say so in rule 2.
3. **Rule 5, order.** Built: a version newer than the kit is refused as "newer than this kit" before the table lookup (it is also
   not in the table). Proposed: swap the order of the two clauses.
4. **Rule 7, the sets.** Built: `deleted-locally` when the file is absent and the path is in the row of X for the whole-file
   hashes (for a block file, the block hashes); `removed-in-kit` when the row of X lists a path that the present manifest does
   not and the file exists in the target (in the target's mode, whether or not the file was installed in X's mode). Proposed:
   say so.
5. **Rule 10, printed forms.** Built: `template-changed DEST (SRC)`; for `config/protected-paths.txt` and
   `config/neutrality.txt` `template-line DEST LINE` for each non-placeholder line of the present template the target lacks; for
   `agk.toml` `template-key agk.toml KEY = VALUE` for each top-level key the target lacks. All of them only when the template's
   hash differs from X's, so a second run prints none. Proposed: say so.
6. **Rule 13, a block file adopt created whole.** adopt writes a file that did not exist (`CLAUDE.md`, the pull request template)
   without markers. Built: a block file with no markers whose text equals the present kit text is `unchanged`; whose text
   hashes as an old block body is `replace` (the whole file); otherwise `conflict` (class marked block). `.gitignore` is created
   with markers. Proposed: add this to rule 13.
7. **Rules 14 and 16, wording.** Built summary lines: `dry run: N files would change; the version line of agk.toml would be set to
   V; nothing was written`, `upgraded N files; the version line of agk.toml is set to V`, `nothing to do`. The `Protected classes:`
   line is built from the target's own list for the written paths and `agk.toml` when its version line is written; the ADR
   skeleton's date is `YYYY-MM-DD` so that the output is deterministic. Proposed: say so.
8. **Rule 15, the write.** Built: each file is written to `.<name>.agk-upgrade` in its directory and renamed; a created or replaced file
   has the default mode of a new file. Proposed: say so.
9. **Rule 18 and 19, tests.** In addition to the small-kit fixture, a test installs each real kit version from 0.3.0 to 0.8.0 with
   its own `init.py` (and `adopt.py` from 0.4.0), taken from the commit that the table names, and upgrades it with this kit and the
   real table: no conflict, every installed file equals the kit's, a second run says `nothing to do`. Kits 0.1.0 and 0.2.0 are
   tested as refused (item 1). Proposed: add these to rule 19.
10. **Rule 24, protected classes.** Built: the ADR names `scripts/agk/`, `kit/` and `tests/kit_dev/`. `skills/upgrade/SKILL.md`
    belongs to the plugin item (SPEC-0005) and is not built here.
11. **Rule 25, no installed file changes.** The build changes no installed path, yet the kit version is bumped to 0.9.0 (the day 9
    brief: one bump per item). Proposed: none.

## Question (answered)

- **Q-K3-71** ruled on 2026-10-16: option (a), item 1.
