# ADR-0108: changelog fragments and the table of hashes left to the release (REQ-038, SPEC-0031)

- Status: Accepted
- Date: 2026-10-24
- Deciders: maintainers
- Related: ADR-0106, ADR-0096
- Requirements: REQ-038

Protected classes: `kit/`, `scripts/agk/`, `tests/kit_dev/`

## Context

SPEC-0031 (Approved, #177) is the build of brief #171. In flow mode a build added a line under `## Unreleased` of `CHANGELOG.md` and refreshed `kit/hashes.json`, so two builds open at once collided on both files
(#169 lost its CI for a round because #168 merged a line first). The tests were written first (`tests/kit_dev/test_changelog_fragments.py` and the updated `test_changelog_flow.py`; before the scripts: 26 failed, 8 passed in the
selected files). The number ADR-0108 is the one the conductor gave this build (ADR-0105 and ADR-0107 are held by open #175 and #178; `intake.py ids` is not used).

## Decision

1. **Fragment** (rules 1 and 2): a build adds `changelog.d/<slug>.md` (`[a-z0-9-]+`) with one line `- <one-line change>`, no pull request number, and does not edit `CHANGELOG.md`. `kit_hashes.py` `flow_problems` fails a build
   that edits `CHANGELOG.md`, that changes a file the installer writes (the trigger of SPEC-0028 rule 2) without adding exactly one fragment, that adds more than one, that adds a malformed one, or that removes or edits a
   fragment. A build that changes no installed file may add one.
2. **Release script** (rule 3): `scripts/agk/changelog_fragments.py gather --version V [--date D]` (kit-only) moves the lines under `## Unreleased`, unchanged, then the line of each committed fragment as `- #<n> <change>`
   in the order of the pull request numbers, under `## V (<date>)`, deletes the fragments and writes nothing else. `<n>` is read from the `(#<n>)` at the end of the subject of the commit that added the file
   (`git log --diff-filter=A`); if one cannot be read the script stops before writing (the verdict on #177 ruling Q-S0031-1).
3. **Release check** (rule 4): `check_release.py` accepts the deletion of a fragment among the release files, fails a fragment left, added or edited, a fragment line not moved with its number and in order, and a fragment whose
   number cannot be read. Strict mode and a pull request that raises no version are as before (rule 5).
4. **The table** (rule 6, measured below): in flow mode `kit_hashes.py` fails a build that edits `kit/hashes.json` and does not compare the row of the current version while the version is unchanged from the base; the release
   regenerates the table with `python3 scripts/agk/kit_hashes.py --write` and the table is then compared in full, as before. Rows of earlier versions are compared always.
5. **Amendment 54** (`docs/runs/proposed-spec-amendments-54.md`) is applied to SPEC-0028 (rules 2, 4, 5 and 6). The guide section "Developing the kit" and `kit/templates/changelog.md` say the above. This repository's
   `CHANGELOG.md` is not edited by this build, so its introductory sentence keeps the old wording until the first release made this way. Nothing here is installed in a project (the manifest is unchanged).

## Measurement

Measured on `main` at 6afc068 (full history, `git fetch --unshallow`), before the build, to decide whether the release can regenerate `kit/hashes.json`:

- `python3 scripts/agk/kit_hashes.py --write` on `main` rewrote exactly one line of the committed table: the `commits` list of the row `0.54.0` gained one commit (the merge of #172, which no pull request could name before its own
  merge). Every digest in every row was identical to the committed one, so the table is a function of the history and the tree and a build's refresh adds nothing the release cannot compute.
- Of the last 20 commits of the first-parent history of `main`, 10 changed `kit/hashes.json`: half the merged builds touched the second shared file.
- The committed row of `0.54.0` lists 71 paths with 77 digests in 3 commits, and 6 paths have more than one digest; those extra digests come from the history of merged builds, which the regeneration at the release reads again.

So the release can regenerate the table, and builds stop touching it. `upgrade.py` reads the table for released versions, installed from a tag; between releases the current row lacks the digests of builds not yet released
(see Residual).

## Consequences

- Two builds open at once share no file: each adds its own fragment. A conflict on `CHANGELOG.md` or `kit/hashes.json` can no longer come from builds.
- The release pull request does the gathering and the regeneration in two commands and `check_release.py` verifies it.

## Residual

- 2026-10-24: between two releases the row of the current version in the committed table lacks the digests of unreleased builds, so a consumer that reads the table of an unreleased checkout (not a tagged release) would see those
  files as modified; `upgrade.py` installs from tags, and the release regenerates the row (due 2026-12-31).
- 2026-10-24: the introductory sentence of `CHANGELOG.md` still describes the Unreleased line; the first release made with fragments rewrites it (due 2026-12-31).
