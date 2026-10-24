# SPEC-0028: In flow mode a kit build pull request does not bump the version, and one release pull request bumps it for all of them

- Status: Approved
- Owner: reviewer group (a team from config/reviewers.yaml)
- Requirements: REQ-035

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.
Written by the intake of one sentence (SPEC-0012): "In flow mode a kit build pull request does not bump the version, and one release pull request bumps it for all of them, so independent kit builds can run in parallel." It is step 0b of the conductor plan (issue #160) and follows SPEC-0025 rule 8, whose release model was left to this intake. It is about how this repository releases the kit: it changes nothing a project installs or runs, and in strict mode nothing changes at all. Evidence: every kit build pull request bumps `agk.toml`, `kit/manifest.json` and the plugin and regenerates `kit/hashes.json`, so two parallel kit builds always collide on the same lines.
The maintainers gave 4 answers before it was written, in the brief of issue #160 and not as interview questions: (1) in flow mode a build pull request leaves the three versions as they are, adds one line under an Unreleased heading of a new `CHANGELOG.md` naming its pull request and its one-line change, and refreshes `kit/hashes.json` for the files it changed, and the kit-version checks accept that; (2) a release pull request, opened by a session on the maintainers' word, moves the Unreleased lines under the new version and bumps the three versions together and nothing else, a check fails a release pull request that changes any other file, and the maintainers merge and tag it; (3) in strict mode nothing changes, a build pull request bumps as today; (4) `check_numbers`, `renumber` and the union logs apply as built, and a collision in `kit/hashes.json` between two parallel builds is resolved by regenerating it after the rebase with one command.

## Rules

1. **The changelog.** `CHANGELOG.md` at the root of this repository (a new kit file; not installed in a project) has the heading `# Changelog`, then `## Unreleased`, then one `## <version> (<YYYY-MM-DD>)` heading for each release, newest first. A line is `- #<n> <one-line change>`: the number of the pull request and what it changes, in one line. `kit/templates/changelog.md` holds the shape.
2. **A build pull request in flow mode.** In flow mode (`pr_mode = "flow"` in `agk.toml`) a pull request that changes a file the installer writes (the files `kit/manifest.json` lists) leaves `version` in `agk.toml`, `kit_version` in `kit/manifest.json` and `version` in `.claude-plugin/plugin.json` as they are, adds at least one line under `## Unreleased` of `CHANGELOG.md`, and refreshes `kit/hashes.json` with `python3 scripts/agk/kit_hashes.py --write`. The check of the bump rule (`kit_hashes.py`) accepts a change to an installed path without a bump when `CHANGELOG.md` gained a line under `## Unreleased` against the base; without that line it fails naming the rule and the path class, as the bump rule does today. The row of the current version in the table then lists more than one digest for a changed path, which the table already allows; the rows of earlier versions are never touched.
3. **Strict mode.** In strict mode (the default) the bump rule, the checks of the versions and `kit/hashes.json` are exactly what they are before this spec: a build pull request bumps the three versions, and no changelog line is required.
4. **The release pull request.** In flow mode a pull request that raises `version` in `agk.toml` is a release pull request. It is opened by a session on the maintainers' word, and it changes only these five files: `CHANGELOG.md`, `agk.toml`, `kit/manifest.json`, `.claude-plugin/plugin.json` and `kit/hashes.json` (the row of the new version). It moves every line under `## Unreleased` under a new heading `## <new version> (<date>)`, unchanged and in order, leaves `## Unreleased` empty, and raises the three versions to the same new number, which is greater than the old one. The maintainers merge it and tag it; no check merges or tags.
5. **The release check.** A new check, `scripts/agk/check_release.py` (kit-only, never installed; a step of the governance workflow of this repository), reads git and the files of the work tree only. In strict mode and when no version is raised it prints `ok release` and checks nothing. For a release pull request it fails, naming the rule and the path class and never a value, when a changed file is outside the five of rule 4, when the three versions differ or do not rise, when the Unreleased lines were not moved unchanged, or when `## Unreleased` is not empty afterwards.
6. **Collisions.** `check_numbers.py`, `intake.py renumber` and the `merge=union` logs apply as built (SPEC-0025). A collision in `kit/hashes.json` between two parallel builds is resolved by regenerating it after the rebase or merge of the default branch: `python3 scripts/agk/kit_hashes.py --write`, then commit. A collision in `CHANGELOG.md` under `## Unreleased` is resolved by keeping both lines.
7. **The rules of the sessions.** The build changes `CLAUDE.md` rule 2 and `constitution/principles.md` rule 3 (protected files, named by the build's ADR) to say: one open pull request per session; several sessions may have one each; a pull request never stacks on another's unmerged change; dependence is declared with `Depends-on`. The ruling of the verdict on step 0a puts this change in the build of this spec.
8. **The guide.** A section on developing the kit (in `docs/guides/reference.md`) tells a kit developer, in flow mode, to add the changelog line, how a release pull request is made and checked, and the one command that resolves a `kit/hashes.json` collision.
9. **How it changes.** SPEC-0008 (the bump rule and the table) and SPEC-0025 (rule 8: the release model) are Approved: the build changes them by `docs/runs/proposed-spec-amendments-N.md`, applied by its ADR. The build is a kit change of this repository only, measured first and split at about 600 changed lines of code and tests: the changelog and its template, the bump-rule change, the release check and its workflow step, the two protected files, the guide section, an ADR that names the protected classes it touches, tests first. Whether it bumps itself: it is the first change under this rule and it still bumps, as the last build that does (it is built while this repository's own builds are serial).
10. **The tests.** Fixtures in `tmp_path`, with git: a flow-mode change to an installed file with and without a changelog line, and in strict mode; a release pull request that is right, one with a sixth file, one with versions that differ or do not rise, one that changes an Unreleased line while moving it, and one that leaves Unreleased non-empty; the regeneration after a collision; the text of `CLAUDE.md`, the principles and the guide section. No network and no model.

## Tests

- Rule 2: a flow-mode change to an installed file with an Unreleased line and refreshed hashes passes the checks; REQ-035 AC1.
- Rule 2: the same change without the line fails naming the rule and the path class; REQ-035 AC2.
- Rule 3: in strict mode the bump is required and no line is; REQ-035 AC3.
- Rules 4 and 5: a release pull request that moves the lines and raises the three versions passes; REQ-035 AC4.
- Rule 5: a sixth changed file, versions that differ or do not rise, a changed or unmoved line, or a non-empty Unreleased fails; REQ-035 AC5.
- Rule 6: after two builds collide in the hashes table, the regenerated table is accepted; REQ-035 AC6.
- Rule 7: `CLAUDE.md` and the principles hold the new text; REQ-035 AC7.
- Rule 8: the guide section names the changelog line, the release pull request and the one command; REQ-035 AC8.

## Proof

REQ-035 AC1 to AC3: *independent kit builds do not touch the version lines, and strict mode is as before.* Rules 2 and 3. REQ-035 AC4 and AC5: *a release is one small pull request that a check can verify.* Rules 4 and 5. REQ-035 AC6: *a collision in the table has one command.* Rule 6. REQ-035 AC7 and AC8: *the sessions' rules and the guide say how.* Rules 7 and 8. The first release made this way, with the number of collisions it avoided, is recorded by the maintainers.

## Residual

- 2026-10-24: the table of hashes lists more than one digest for a path in the row of the current version between releases, so the upgrade treats any of them as unmodified for that version; a later change may split an Unreleased row from the released one (due 2026-12-31).
- 2026-10-24: whether `init` and `adopt` install a `CHANGELOG.md` in a project is not decided here; this repository's changelog is not installed (due 2026-12-31).

## Open questions

none
