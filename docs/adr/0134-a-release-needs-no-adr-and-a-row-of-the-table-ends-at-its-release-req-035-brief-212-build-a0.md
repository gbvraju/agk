# ADR-0134: a release needs no ADR and a row of the table ends at its release (REQ-035, REQ-038, brief #212 build (a0))

- Status: Accepted
- Date: 2026-10-25
- Deciders: maintainers
- Amends: ADR-0108
- Related: ADR-0096
- Requirements: REQ-035, REQ-038

Protected classes: `scripts/agk/`, `tests/kit_dev/`

## Context

The first release made the flow-mode way (brief #212, the kit as 0.55.0, #214) found two gaps, and the conductor ruled both (the verdicts on its head, 2716126): a release changes `agk.toml`, `kit/` and `.claude-plugin/`,
which `check_protected_changes.py` requires an ADR for, while `check_release.py` forbids every file but the release files, so no ADR can be added; and `kit_hashes.py --write` groups the first-parent history by the version of each
commit, so every build since the tag, which still states 0.54.0 in flow mode, puts the files it added (the conductor, the router, the session rules and more) in the row of 0.54.0, and `upgrade.py` reads them as files
that 0.54.0 installed and a project deleted (`deleted-locally`): `tests/kit_dev/test_upgrade.py` for 0.54.0 init and adopt, and the one-hash rule of `test_kit_hashes.py`, fail on that table. ADR-0108 recorded the second as its
residual. ADR-0134 and amendment 70 were reserved on #212. The tests were written first; on the unchanged scripts the release exemption case and two row cases failed (3 failed, 7 passed in the two new files).

## Decision

1. **The release exemption.** `check_release.valid_release(root, mb)` is true when the pull request is in flow mode, raises `version` in `agk.toml`, changes nothing outside the files of the release (the five files of `check_release.ALLOWED`
   and the deleted fragments) and passes `check_release.check`. `check_protected_changes.py` prints `ok protected-changes (a release pull request)` for such a pull request and needs no ADR. It imports `check_release` and, when
   that kit-only script is absent (a project), has no exemption. One more file, a release that fails its own check, strict mode or no raised version leaves the check as it was.
2. **The row of a version.** In flow mode `kit_hashes.build_table` keeps, for a version other than 0.1.0, only the first snapshot of the first-parent history that states it (the release commit). A later commit that still states
   the version, a build between two releases, belongs to the next version's row, and between two releases the row of the current version stays the release's. Strict mode and every row before 0.54.0 are as before. The release
   pull request then regenerates the table with `kit_hashes.py --write` and the files added since 0.54.0 are in the row of 0.55.0 only.
3. Amendment 70 (`docs/runs/proposed-spec-amendments-70.md`) is applied to SPEC-0028 rule 4, SPEC-0008 rule 2 and SPEC-0031 rule 6. Flow mode (SPEC-0028, SPEC-0031): fragment `changelog.d/release-exemption-and-rows.md`; no version bump;
   `CHANGELOG.md` and `kit/hashes.json` as on `main`. This pull request does not release anything: #214 does, after it merges main.
4. **Readings taken where the verdicts leave a point open** (questions in the pull request, the most conservative reading each): the committed table is not regenerated here, because in flow mode a build leaves it to the release;
   "states V" is read from `kit_version` of the manifest at each commit; the exemption asks `check_release.check` itself, so a rule of the release check is never restated.

## Consequences

- A release pull request of the kit is green without an ADR, and it cannot carry an unreviewed change to another protected file.
- A project that upgrades from 0.54.0 gets the files added since, because the table no longer says 0.54.0 had them.

## Residual

- 2026-10-25: a version released with a build in the same commit as the release is one commit, so its row is that commit; a later correction of that release by a commit that keeps the version lands in the next row (due 2026-12-31).
