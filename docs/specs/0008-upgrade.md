# SPEC-0008: agk upgrade

- Status: Approved
- Owner: maintainers
- Requirements: REQ-014 (to be added by ADR, see SPEC-0005); REQ-009 (init), REQ-010 (adopt)

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.
The open points Q-K3-50 to Q-K3-56 were ruled on by the maintainers on 2026-10-15 (`docs/runs/spec-0008-notes.md`). This spec is K3 criterion c of ADR-0015. It follows SPEC-0001 (init), SPEC-0002 (adopt) and SPEC-0005
rule 3 (no lock file in the target; the installed version is `version` in `agk.toml`). Facts about the repository
history used here were read on 2026-10-15 (`docs/runs/spec-0008-notes.md`).

## Rules

### The problem and the anchor

1. **What is detected, and how.** To tell a locally edited vendored file from an outdated one, the upgrade needs what
   the file was at the installed version X. The target keeps no lock file, and the plugin cache holds the current
   version only `(verify)`. The kit therefore keeps, inside the kit, a table `kit/hashes.json` of the SHA-256 of every
   installable file of every released version (rule 2). A file in the target is **outdated** if its hash is one of the
   hashes the table lists for X and for that path, **edited** if it is not, and **current** if it equals the kit's
   present file.
2. **The table.** `kit/hashes.json` is `{"table": 1, "releases": {"X.Y.Z": {"commits": [..], "verbatim": {path:
   [sha256, ..]}, "blocks": {path: [sha256, ..]}, "templates": {path: [sha256, ..]}}}}`. The hash lists hold more than
   one entry only for 0.1.0, whose files changed without a version bump (rules 22, 25). It is kit-only (not installed),
   written by a kit-only script `scripts/agk/kit_hashes.py` from the commits of the kit's history that each
   release's `commits` list names. It is a **committed generated file**, an exception to principle 5, and the
   implementation's ADR records that decision. It is acceptable where a lock file in the target was not because it is
   one file, in the kit only, never written into targets, and fully regenerable from history. A kit test regenerates
   **every** row from git history and compares it with the committed table, not only the current row, so the table can
   never drift; it also fails when `kit_version` has no row. The history is the first-parent history up to the merge base with
   the default branch (`AGK_BASE`, else `origin/<default>`), plus the working tree as the current version. A past version's row
   names exactly the commits at which its files changed (full SHAs); the current version's row is taken from the working tree
   and may name fewer commits (none, until the next bump), because the commit that releases it does not exist yet. A shallow
   clone is a failure. `kit_hashes.py --check` (the default) and `--write` are the interface. The kit-dev tests therefore need
   `fetch-depth: 0` in CI.
   The table is the one new source of truth; it is in the kit, not in the target.
3. **Tags are not read.** Release tags `vX.Y.Z` (SPEC-0005 rule 13) start with the K3 release; rows are regenerated from
   the commits each row names, not from tags, and upgrade does not read them and needs no network and no `git`. Today the repository has no tag and no release
   (rule 22).

### Interface and effects

4. **Command.** `python3 scripts/agk/upgrade.py TARGET [--dry-run]`, run from the kit checkout or the plugin root (as
   `init.py` and `adopt.py`; kit-only, never installed). Standard library only. The kit is the repository the script
   lives in; the current version is its `kit/manifest.json` `kit_version`. TARGET is an existing directory that is a git
   work tree with an `agk.toml`. No other options in K3. Exit codes, refusal order and the no-network, no-`git`, no
   commit, no write outside TARGET guarantees are those of SPEC-0001 rule 2: 0 success (including `nothing to do`);
   1 refusal (nothing written); 2 usage; 3 I/O error. Refusals name the path class and the file, never content.
5. **Preconditions (refusals, before any write).** `agk.toml` is absent and `pyproject.toml` has no `[tool.agk]` table with a
   `version` (the legacy case of rule 11), or `agk.toml` has no `version`, or `mode` is not `init` or `adopt` (class
   `agk.toml`); `version` is greater than the kit's (downgrade, "newer than this kit"; checked before the table lookup, because
   such a version is also not in the table); `version` is not in the table (class `kit/hashes.json`); a path to write passes
   through a symlink; the script runs below Python 3.11; TARGET is or is
   inside the kit. When `version` equals the kit's, the run still checks every file and prints `nothing to do` if all
   are current.
6. **The installed set.** The paths the installer for `mode` writes: for `init`, `verbatim` without the kit-only paths
   (SPEC-0001 rule 3); for `adopt`, `verbatim` without `adopt.skip` and without `adopt.blocks`, plus the blocks. The
   `templates` and the `rendered` file are not in this set (rule 9).

### Per file

7. **The rules.** For each path of the installed set, with T the target file, N the kit's present file and H the
   hashes the table lists for X:

   | T | Rule | Line | Write |
   | --- | --- | --- | --- |
   | equals N | skip | `unchanged` | none |
   | absent, path not in H, in N | create | `create` | the file |
   | differs from N, hash in H | outdated | `replace` | the kit's file |
   | differs from N, hash not in H | edited | `conflict` | none; the run refuses (rule 8) |
   | absent, path in H | deleted locally | `deleted-locally` | none; reported |
   | present, path not in N | removed from the kit | `removed-in-kit` | deleted only when a regular file whose bytes equal a copy the table lists for that path in any release (`(unmodified, deleted)`); otherwise none (`(modified, kept)`) |

   File modes of created and replaced files are those the installer sets (SPEC-0001). `deleted-locally` applies when the file is
   absent and the path is in the row of X (for a block file, the block hashes); `removed-in-kit` applies when the row of X lists
   a path that the present manifest does not and the file exists in the target (in the target's mode, whether or not the file
   was installed in X's mode).
   **Create-only templates.** For each path that init and adopt create only when absent (`docs/runs/residuals.md`), the upgrade creates
   it when the target lacks it, from the present kit's template rendered as init renders it (`create PATH (absent)`; the dry run
   lists it the same way). A file that exists, with any content, is not read, compared, listed or rewritten. A symlink or a non-file at
   the path is a `conflict` (rule 8). The `template-changed` note for such a path is not printed.
8. **A conflict stops the run.** If any path is `conflict`, the real run writes nothing and exits 1, naming each
   edited path (a refusal lists them all, not the first). Partial application is not done. The printed
   fix per edited path: restore the kit's copy by hand, or move the edit out of the vendored file, then run again.
9. **Never rewritten.** `agk.toml` values (except the one `version` line of rule 11), `config/reviewers.yaml`, `config/protected-paths.txt`, `config/neutrality.txt`,
   ADRs, specs, `docs/requirements.md`, `docs/build-state.md`, `docs/runs/`, `constitution/` and `pyproject.toml` (the
   `templates` of the manifest for `init`, `adopt.templates` for `adopt`; the table keys them by kit source path) and the rendered `.github/CODEOWNERS` are not written by the upgrade. A test checks the
   bytes and modification times of each after a run.
10. **Templates and new keys are printed.** For each template whose kit source hash differs from the one the table
    lists for X, print `template-changed PATH` and the kit source path. For line-based templates
    (`config/protected-paths.txt`, `config/neutrality.txt`) also print each line of the kit's present template that the
    target file lacks. For `agk.toml`, print each key of the kit's present template that the target lacks, with the
    template's value; a key is never merged (as SPEC-0002 prints settings entries). `.claude/settings.json` is a
    verbatim file in the manifest (adopt refuses to merge an existing one, SPEC-0002), so it follows rule 7. The printed
    forms are `template-changed DEST (SRC)`; for `config/protected-paths.txt` and `config/neutrality.txt`,
    `template-line DEST LINE` for each non-placeholder line of the present template that the target lacks; for `agk.toml`,
    `template-key agk.toml KEY = VALUE` for each top-level key the target lacks. All of them are printed only when the
    template's hash differs from X's, so a second run prints none.
11. **The version stamp.** The upgrade rewrites exactly the line `version = "..."` of `agk.toml` to the kit's version, as
    its last write and only when every other write succeeded. Every other line of `agk.toml` stays byte for byte as it
    was. With a conflict, a refusal or an I/O error the line is not written, so the next run starts from the same
    `version`. **The legacy stamp** (ruling Q-K3-71, option (a)): kits 0.1.0 and 0.2.0 wrote no `agk.toml`; the stamp is
    `version` and `installed` in `[tool.agk]` of `pyproject.toml`, and there is no `mode` (init only). When `agk.toml` is absent
    and `pyproject.toml` has a `[tool.agk]` table with a `version`, the upgrade treats the target as mode init at that version;
    takes `installed` and `default_branch` from the stamp (or the template default); and creates `agk.toml` from the kit's
    template with the kit's current version, as the last write and only when every other write succeeded (on a conflict, a
    refusal or an I/O error it is not created, so a re-run starts from the stamp again). It never writes `pyproject.toml`; it
    prints `legacy-stamp pyproject.toml [tool.agk]: obsolete after this upgrade; remove it in your own change`. The created
    `agk.toml` counts in `N files`, the summary reads `upgraded N files; agk.toml is created with version V`, and the
    `template-changed agk.toml` line is not printed for it. Any other target without `agk.toml` is still refused.
12. **CODEOWNERS.** After a run the script prints `python3 scripts/agk/reviewers.py --codeowners --write` when
    `config/reviewers.yaml` or the generator was part of the change, because the file is rendered from the target's
    own configuration (SPEC-0001 rule on rendered files).
13. **Marked blocks (adopt).** For `.gitignore`, `CLAUDE.md` and `.github/PULL_REQUEST_TEMPLATE.md`, T is the text between
    the markers (`# >>> agk` and `<!-- >>> agk -->` styles of SPEC-0002) and N is the kit's block. The rules of rule 7
    apply to the text between the markers; a replacement rewrites only that text. A file with no markers, or an end
    marker without a start, is `conflict` (class `marked block`). Text outside the markers is never read for the
    comparison and never written. A second run changes nothing. adopt writes a block file that did not exist (`CLAUDE.md`,
    the pull request template) whole, without markers: such a file with no markers whose text equals the present kit text is
    `unchanged`; whose text hashes as an old block body is `replace` (the whole file); otherwise it is `conflict` (class
    `marked block`). `.gitignore` is created with markers.
14. **Dry run.** `--dry-run` prints one line per path (`create`, `replace`, `unchanged`, `conflict`, `deleted-locally`,
    `removed-in-kit`, `template-changed`), sorted by path, writes nothing, and exits with the code the real run would;
    the real run prints the same lines before it writes (the summary line says how many files would change and how many would be deleted). Under `nothing to do` no file is touched (hashes and
    modification times are equal).
15. **Order and atomicity.** All decisions are made before the first write. Writes are in sorted path order, then the deletions of rule 7 in sorted path order (and the directories they emptied, never the target root or a directory directly under it: amendment 26), each file
    through a temporary file `.<name>.agk-upgrade` in its directory and a rename (a created or replaced file has the default mode of
    a new file); an I/O error stops the run (exit 3) and reports the files
    already written; the `agk.toml` version line (rule 11) is the last write and is skipped in that case.

### The pull request in the target

16. **Protected classes.** The files an upgrade writes lie in classes the target's `config/protected-paths.txt`
    protects (`scripts/agk/`, `.claude/`, `.github/`, `agk.mk`, `Makefile`), so the target's
    `check_protected_changes` requires an ADR in the same pull request that names each changed class. After the lines
    of rule 14 the script prints, from the target's own list, the `Protected classes:` line for the paths it would write
    and an ADR skeleton (title, `Status: Proposed`, empty Context and Decision) to stdout. It writes no ADR: the number,
    the reasons and the decision are the maintainers', and there is no `--draft-adr`. The summary lines are `dry run: N files
    would change; the version line of agk.toml would be set to V; nothing was written`, `upgraded N files; the version line of
    agk.toml is set to V` and `nothing to do`. The `Protected classes:` line is built from the target's own list for the written
    paths, and includes `agk.toml` when its version line is written; the skeleton's date is `YYYY-MM-DD`, so the output is
    deterministic.
17. **The skill.** `/agk:upgrade` (SPEC-0005 rule 8) runs `--dry-run`, shows the lines, asks, then runs the real command.
    It does not commit, push or open the pull request, and does not write the ADR.

### Tests and proof

18. **Tests, no network, no `git`.** `tests/kit_dev/test_upgrade.py` and `tests/kit_dev/test_kit_hashes.py` (kit-only):
    for init and adopt targets built in `tmp_path` by the installers of an older kit fixture, then upgraded: each
    row of rule 7; a file edited by the user stops the run with nothing written and lists every edited path; a file
    deleted locally; a file removed from the kit; a new file in the kit; a key added to the kit's `agk.toml`
    template; each block with markers intact, edited, and missing; rules 9, 14, 15; X equal to the kit's, X above it,
    X unknown; a symlinked path; the `version` line rewritten last and only on full success (and left alone on a conflict or an I/O error), every other `agk.toml` line byte for byte.
19. **An older kit fixture.** A test builds a second, smaller kit directory (two versions of a few files and a manifest
    with a `hashes.json`) so the old and new versions are known without the real history. The real table is tested for
    shape, for the current version's entry (rule 2), and for the listed versions of rule 22. In addition, a test installs each
    real kit version from 0.3.0 to 0.8.0 with its own `init.py` (and `adopt.py` from 0.4.0), taken from the commit that the table
    names, and upgrades it with this kit and the real table: no conflict, every installed file equals the kit's, and a second run
    says `nothing to do`. Kits 0.1.0 and 0.2.0 are tested through the legacy stamp (rule 11).
20. **Determinism.** The same inputs give byte-identical output; a dry run and the following real run print the same lines.
21. **Idempotence.** An upgraded target is upgraded again with `nothing to do`.
22. **The 0.1.0 gap (what is missing today).** The repository has no tag and no release. The table can be built from
    the history of `kit/manifest.json` for 0.1.0, 0.2.0, 0.3.0, 0.4.0, 0.4.1, 0.4.2, 0.5.0, 0.6.0, 0.6.1 and 0.6.2, but
    0.1.0 spans two commits that changed kit files (the second changed `Makefile`, a verbatim file, without a version
    bump), so its entries carry both hashes. No tag is created retroactively: the first tag is the K3 release, and
    tagging is a maintainers' step at each release. The table does not depend on tags.
23. **Proof (criterion c of ADR-0015; a maintainers' step, not done by an agent).** On the 0.1.0 sandbox
    (`gbvraju/agk-sandbox`): run `--dry-run` and then the real command from the current kit; record the lines; open the
    upgrade pull request with the ADR of rule 16; expect `governance` green and `git diff --stat` against the sandbox's
    default branch to list no product file (paths outside the installed set, SPEC-0001 rule 4). The run, the commands
    and the result are recorded in `docs/runs/`.
24. **Protected classes of the implementation.** `scripts/agk/upgrade.py`, `scripts/agk/kit_hashes.py`, `kit/hashes.json`
    (`scripts/agk/`, `kit/`), `tests/kit_dev/` and `skills/upgrade/SKILL.md`; the PR carries an ADR naming each.
    Neither the script nor the table is installed into targets. The ADR of the build names `scripts/agk/`, `kit/` and
    `tests/kit_dev/`; `skills/upgrade/SKILL.md` belongs to the plugin item (SPEC-0005) and is not part of the upgrade build.

25. **Bump rule.** From the next release, a change to any installed path needs a `kit_version` bump in the same pull
    request. The full-history regeneration test of rule 2 enforces it: it fails when any version other than 0.1.0 has
    a second hash for a path. 0.1.0 is the one recorded exception.

## Tests

- Rules 4-8, 13-15, 18, 20, 21: `tests/kit_dev/test_upgrade.py`, marker `REQ-014 AC5`.
- Rules 9-12, 16: the same file, marker `REQ-014 AC5`.
- Rules 1-3, 19, 22, 25: `tests/kit_dev/test_kit_hashes.py`, marker `REQ-014 AC5`.
- Rule 17: `tests/kit_dev/test_distribution.py` (SPEC-0005 rule 19), marker `REQ-014 AC2`.
- Rule 23: a record in `docs/runs/`, checked by the maintainers, not by a test.

## Residual

- 2026-10-15: no release tag exists; the hash table is generated from history and checked in the kit tests. A release
  without a table row is caught by a kit test, not by a tag check (due 2026-11-30).
- 2026-10-15: a release whose files changed without a version bump (0.1.0) makes the "outdated" test weaker for that
  version (any listed hash passes); rule 25 stops it for later releases (due 2026-11-30).
- 2026-10-15: templates are compared and printed only; a user cannot be told which of their edits to a template
  conflict with the kit's change (due 2026-12-31).
- 2026-10-15: the plugin cache may hold only the current version `(verify)`; the table makes old versions
  unnecessary, but a file the user installed from an unreleased kit commit is reported as `conflict` (due 2026-11-30).
