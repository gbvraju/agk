# SPEC-0008: agk upgrade

- Status: Draft
- Owner: maintainers
- Requirements: REQ-014 (to be added by ADR, see SPEC-0005); REQ-009 (init), REQ-010 (adopt)

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.
Open points are raised as `Q-K3-n` (this spec uses 50 to 69) in `docs/runs/spec-0008-notes.md`; a rule that depends on
one says so. This spec is K3 criterion c of ADR-0015. It follows SPEC-0001 (init), SPEC-0002 (adopt) and SPEC-0005
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
   one entry when a release's files changed without a version bump (rule 5). It is kit-only (not installed), written
   by a kit-only script `scripts/agk/kit_hashes.py` from a commit of the kit's history, and a kit test fails when the
   entry for the current `kit_version` does not equal the working tree, or when `kit_version` has no entry. The table
   is the one new source of truth; it is in the kit, not in the target.
3. **Tags are optional.** Release tags `vX.Y.Z` (SPEC-0005 rule 13) are the way to regenerate a row from the history;
   upgrade does not read them and needs no network and no `git`. Today the repository has no tag and no release
   (rule 22).

### Interface and effects

4. **Command.** `python3 scripts/agk/upgrade.py TARGET [--dry-run]`, run from the kit checkout or the plugin root (as
   `init.py` and `adopt.py`; kit-only, never installed). Standard library only. The kit is the repository the script
   lives in; the current version is its `kit/manifest.json` `kit_version`. TARGET is an existing directory that is a git
   work tree with an `agk.toml`. No other options in K3. Exit codes, refusal order and the no-network, no-`git`, no
   commit, no write outside TARGET guarantees are those of SPEC-0001 rule 2: 0 success (including `nothing to do`);
   1 refusal (nothing written); 2 usage; 3 I/O error. Refusals name the path class and the file, never content.
5. **Preconditions (refusals, before any write).** `agk.toml` is absent or has no `version`, or `mode` is not `init` or
   `adopt` (class `agk.toml`); `version` is not in the table (class `kit/hashes.json`); `version` is greater than the
   kit's (downgrade); a path to write passes through a symlink; the script runs below Python 3.11; TARGET is or is
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
   | present, path not in N | removed from the kit | `removed-in-kit` | none; never deleted |

   File modes of created and replaced files are those the installer sets (SPEC-0001).
8. **A conflict stops the run.** If any path is `conflict`, the real run writes nothing and exits 1, naming each
   edited path (a refusal lists them all, not the first). Partial application is not done (Q-K3-51). The printed
   fix per edited path: restore the kit's copy by hand, or move the edit out of the vendored file, then run again.
9. **Never rewritten.** `agk.toml` values, `config/reviewers.yaml`, `config/protected-paths.txt`, `config/neutrality.txt`,
   ADRs, specs, `docs/requirements.md`, `docs/build-state.md`, `docs/runs/`, `constitution/` and `pyproject.toml` (the
   `templates` of the manifest for `init`, `adopt.templates` for `adopt`; the table keys them by kit source path) and the rendered `.github/CODEOWNERS` are not written by the upgrade. A test checks the
   bytes and modification times of each after a run.
10. **Templates and new keys are printed.** For each template whose kit source hash differs from the one the table
    lists for X, print `template-changed PATH` and the kit source path. For line-based templates
    (`config/protected-paths.txt`, `config/neutrality.txt`) also print each line of the kit's present template that the
    target file lacks. For `agk.toml`, print each key of the kit's present template that the target lacks, with the
    template's value; a key is never merged (as SPEC-0002 prints settings entries). `.claude/settings.json` is a
    verbatim file in the manifest (adopt refuses to merge an existing one, SPEC-0002), so it follows rule 7.
11. **The version stamp.** The upgrade prints the line `version = "<kit version>"` for `agk.toml` and does not write
    it (rule 9). The next `agk doctor` run reports `kit-version` until it is changed (SPEC-0006). Q-K3-52 asks whether
    this one line may be rewritten.
12. **CODEOWNERS.** After a run the script prints `python3 scripts/agk/reviewers.py --codeowners --write` when
    `config/reviewers.yaml` or the generator was part of the change, because the file is rendered from the target's
    own configuration (SPEC-0001 rule on rendered files).
13. **Marked blocks (adopt).** For `.gitignore`, `CLAUDE.md` and `.github/PULL_REQUEST_TEMPLATE.md`, T is the text between
    the markers (`# >>> agk` and `<!-- >>> agk -->` styles of SPEC-0002) and N is the kit's block. The rules of rule 7
    apply to the text between the markers; a replacement rewrites only that text. A file with no markers, or an end
    marker without a start, is `conflict` (class `marked block`). Text outside the markers is never read for the
    comparison and never written. A second run changes nothing.
14. **Dry run.** `--dry-run` prints one line per path (`create`, `replace`, `unchanged`, `conflict`, `deleted-locally`,
    `removed-in-kit`, `template-changed`), sorted by path, writes nothing, and exits with the code the real run would;
    the real run prints the same lines before it writes. Under `nothing to do` no file is touched (hashes and
    modification times are equal).
15. **Order and atomicity.** All decisions are made before the first write. Writes are in sorted path order, each file
    through a temporary file in its directory and a rename; an I/O error stops the run (exit 3) and reports the files
    already written.

### The pull request in the target

16. **Protected classes.** The files an upgrade writes lie in classes the target's `config/protected-paths.txt`
    protects (`scripts/agk/`, `tests/kit/`, `.claude/`, `.github/`, `agk.mk`, `Makefile`), so the target's
    `check_protected_changes` requires an ADR in the same pull request that names each changed class. After the lines
    of rule 14 the script prints, from the target's own list, the `Protected classes:` line for the paths it would write
    and an ADR skeleton (title, `Status: Proposed`, empty Context and Decision) to stdout. It writes no ADR: the number,
    the reasons and the decision are the maintainers' (Q-K3-54 asks whether `--draft-adr` should write it).
17. **The skill.** `/agk:upgrade` (SPEC-0005 rule 8) runs `--dry-run`, shows the lines, asks, then runs the real command.
    It does not commit, push or open the pull request, and does not write the ADR.

### Tests and proof

18. **Tests, no network, no `git`.** `tests/kit_dev/test_upgrade.py` and `tests/kit_dev/test_kit_hashes.py` (kit-only):
    for init and adopt targets built in `tmp_path` by the installers of an older kit fixture, then upgraded: each
    row of rule 7; a file edited by the user stops the run with nothing written and lists every edited path; a file
    deleted locally; a file removed from the kit; a new file in the kit; a key added to the kit's `agk.toml`
    template; each block with markers intact, edited, and missing; rules 9, 14, 15; X equal to the kit's, X above it,
    X unknown; a symlinked path.
19. **An older kit fixture.** A test builds a second, smaller kit directory (two versions of a few files and a manifest
    with a `hashes.json`) so the old and new versions are known without the real history. The real table is tested for
    shape, for the current version's entry (rule 2), and for the listed versions of rule 22.
20. **Determinism.** The same inputs give byte-identical output; a dry run and the following real run print the same lines.
21. **Idempotence.** An upgraded target is upgraded again with `nothing to do`.
22. **The 0.1.0 gap (what is missing today).** The repository has no tag and no release. The table can be built from
    the history of `kit/manifest.json` for 0.1.0, 0.2.0, 0.3.0, 0.4.0, 0.4.1, 0.4.2, 0.5.0, 0.6.0, 0.6.1 and 0.6.2, but
    0.1.0 spans two commits that changed kit files (the second changed `Makefile`, a verbatim file, without a version
    bump), so its entries carry both hashes. The maintainers decide whether tags are created for the past versions
    (Q-K3-53); the table does not depend on them.
23. **Proof (criterion c of ADR-0015; a maintainers' step, not done by an agent).** On the 0.1.0 sandbox
    (`gbvraju/agk-sandbox`): run `--dry-run` and then the real command from the current kit; record the lines; open the
    upgrade pull request with the ADR of rule 16; expect `governance` green and `git diff --stat` against the sandbox's
    default branch to list no product file (paths outside the installed set, SPEC-0001 rule 4). The run, the commands
    and the result are recorded in `docs/runs/`.
24. **Protected classes of the implementation.** `scripts/agk/upgrade.py`, `scripts/agk/kit_hashes.py`, `kit/hashes.json`
    (`scripts/agk/`, `kit/`), `tests/kit_dev/` and `skills/upgrade/SKILL.md`; the PR carries an ADR naming each.
    Neither the script nor the table is installed into targets.

## Tests

- Rules 4-8, 13-15, 18, 20, 21: `tests/kit_dev/test_upgrade.py`, marker `REQ-014 AC5`.
- Rules 9-12, 16: the same file, marker `REQ-014 AC5`.
- Rules 1-3, 19, 22: `tests/kit_dev/test_kit_hashes.py`, marker `REQ-014 AC5`.
- Rule 17: `tests/kit_dev/test_distribution.py` (SPEC-0005 rule 19), marker `REQ-014 AC2`.
- Rule 23: a record in `docs/runs/`, checked by the maintainers, not by a test.

## Residual

- 2026-10-15: no release tag exists; the hash table is generated from history and checked in the kit tests. A release
  without a table row is caught by a kit test, not by a tag check (due 2026-11-30).
- 2026-10-15: a release whose files changed without a version bump (0.1.0) makes the "outdated" test weaker for that
  version (any listed hash passes). The remedy is a bump rule for the kit, which is the maintainers' (Q-K3-55) (due 2026-11-30).
- 2026-10-15: templates are compared and printed only; a user cannot be told which of their edits to a template
  conflict with the kit's change (due 2026-12-31).
- 2026-10-15: the plugin cache may hold only the current version `(verify)`; the table makes old versions
  unnecessary, but a file the user installed from an unreleased kit commit is reported as `conflict` (due 2026-11-30).
