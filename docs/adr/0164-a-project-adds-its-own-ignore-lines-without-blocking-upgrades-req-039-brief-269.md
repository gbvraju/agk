# ADR-0164: a project adds its own ignore lines without blocking upgrades (REQ-039, brief 269)

- Status: Accepted
- Date: 2026-10-26
- Deciders: maintainers
- Related: ADR-0018, ADR-0160
- Requirements: REQ-039

Protected classes: `kit/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`

## Context

An init install receives the kit's `.gitignore` as a whole vendored file. A project that adds one line to it (a folder of
confidential local files, say) has, for `upgrade.py`, an edited vendored file: the upgrade reports `conflict .gitignore (path
class ...: differs from every released copy)` and refuses the whole run, at this upgrade and every later one, and the doctor
reports `vendored-differs`. The workarounds weaken the protection of confidential data. An adopt install already holds the kit's
lines in a marked block (`# >>> agk` to `# <<< agk`, SPEC-0002) whose outside belongs to the project; init installs did not.

The tests were written first (checkpoint c2023be): 9 of `tests/kit_dev/test_upgrade_project_lines.py` and
`tests/kit/test_doctor_project_lines.py` were red on the unchanged tree, among them the brief's case (the released `.gitignore`
plus one invented line, upgraded from an init install).

## Decision

1. **The kit's `.gitignore` is a marked block (answer 1).** The kit's `.gitignore` is now its lines between the two marker
   comments of the `hash` style already used by adopt, `# >>> agk` and `# <<< agk`; the lines themselves live in
   `kit/templates/gitignore`, which `adopt.block_sources` names as the block's text, so adopt's block and its release hash are
   unchanged. A test pins the kit's `.gitignore` to the block of that template. Everything outside the block belongs to the
   project.
2. **Only the block is compared and replaced (answer 2).** `kit/manifest.json` gains `extendable`, the installed files a
   project is expected to extend, with their marker style. In an init install `upgrade.py` and `doctor.py` treat each one as
   a marked block (the rules of SPEC-0008 rule 13 for adopt blocks), with the block hashes of the release row. Lines outside
   the block are kept byte for byte and are never a conflict or a difference; the upgrade line of the file ends with
   `(project lines kept: n)` and the doctor's `vendored-differs` message with `(.gitignore: project lines kept: n)`, once
   per run, and only when n is not zero. In an adopt install the same count is reported for an extendable file.
3. **Migration of a file without markers (answer 3).** When an extendable file has no markers, and its first lines hash as
   the installed release's kit lines (its whole-file row or its block row) and only other lines follow, the upgrade writes
   the block around the kit's present lines and keeps the following lines after it, byte for byte (`replace .gitignore
   (agk block added; project lines kept: n)`); an untouched file just gets the block. Any other difference is still a
   conflict, named as today (`differs from every released copy`): a changed or removed kit line, and project lines placed
   before the kit's lines (Q-269-2, accepted). Broken or duplicated markers and an edit inside the block stay conflicts.
4. **Other extendable files (answer 4).** None. `.gitignore` is the only installed file the kit expects a project to extend.
   `.gitattributes` and `pyproject.toml` are templates an init install creates once and never compares; `Makefile` and
   `CLAUDE.md` are the kit's own rules and entry points, and the guides ask for no project lines in them (project tests go
   in `project_tests` of `agk.toml`). A file is added to `extendable` only by a later ADR (Q-269-3, accepted).
5. **Generic (answer 5).** The tests use invented ignore lines and name no project. The upgrade tests are in `tests/kit_dev/`
   (upgrade is kit-only), the doctor's in `tests/kit/`; the brief's `tests/kit/test_upgrade*.py` does not exist. Flow mode:
   fragment `changelog.d/gitignore-project-lines.md`, no version bump and no edit of `kit/hashes.json`, which the release
   regenerates.

## Consequences

- A project adds ignore lines outside the block and upgrades keep them; an existing init install gets the block at its next
  upgrade, with no conflict, whether or not it already added lines after the kit's.
- The kit repository's own `.gitignore` carries the markers, so its next release row holds the marked file.
- The markers are the existing `# >>> agk` / `# <<< agk` pair of adopt installs; this ADR supersedes the pair `# agk: begin` /
  `# agk: end` that the brief names (Q-269-1, accepted in the verdict on ce7e674): one marker style per file, and no adopt
  install is migrated.
- Amendment 92 (`docs/runs/proposed-spec-amendments-92.md`) is applied to SPEC-0008 rule 13 (init's extendable `.gitignore`
  block, the project-line count and the migration of an unmarked file of kit lines plus project lines) and to SPEC-0006 rule 8
  (the doctor compares init's extendable files inside their markers), as the verdict on ce7e674 asked (Q-269-4).

## Residual

None. The residual of the first head (the spec amendment, Q-269-4) is closed by amendment 92.
