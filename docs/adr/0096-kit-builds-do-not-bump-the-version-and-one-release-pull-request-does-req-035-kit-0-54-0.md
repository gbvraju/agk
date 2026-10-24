# ADR-0096: kit builds do not bump the version and one release pull request does (REQ-035, SPEC-0028), kit 0.54.0

- Status: Proposed
- Date: 2026-10-24
- Deciders: maintainers
- Related: ADR-0095, ADR-0094
- Requirements: REQ-035

Protected classes: `.claude-plugin/`, `.github/`, `CLAUDE.md`, `agk.toml`, `constitution/`, `docs/requirements.md`, `kit/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`

## Context

SPEC-0028 (Approved, #162) is step 0b of the conductor plan (issue #160). This repository is in flow mode (ADR-0094), where independent kit builds should run in parallel; every build pull request bumped the three versions and
regenerated `kit/hashes.json`, so two parallel builds always collided on the same lines. The tests were written first (`tests/kit_dev/test_changelog_flow.py`, `test_release_check.py`, `test_flow_texts.py`; on unchanged `main`:
26 failed, 5 passed).

## Decision

1. **Changelog**: `CHANGELOG.md` (this repository only, not installed) with `## Unreleased` and one heading per release; a line is `- #<n> <one-line change>`; `kit/templates/changelog.md` holds the shape.
2. **Build pull request in flow mode**: `kit_hashes.py` replaces the bump rule, for a pull request that leaves `kit_version` as it is, by the rule that `CHANGELOG.md` gained a new `- #<n> ...` line under `## Unreleased` against the
   base (`flow_problems`); the current row of `kit/hashes.json` lists each build's digest, earlier rows are not touched; in strict mode the rule is unchanged.
3. **Release pull request**: `scripts/agk/check_release.py` (kit-only) fails, in flow mode, a pull request that raises `version` in `agk.toml` when it changes a file outside `CHANGELOG.md`, `agk.toml`,
   `kit/manifest.json`, `.claude-plugin/plugin.json` and `kit/hashes.json`, when the three versions differ or do not rise (compared as numbers), or when the Unreleased lines were not moved unchanged and in order under
   `## <version> (<date>)` with `## Unreleased` left empty and the older sections as they were. The messages name rule 5 and a path, never a version. The workflow runs it as the step `Release check`, guarded by
   `hashFiles('kit/agk-kit.mk') != ''` (a project has neither the script nor the file); the harness of the installed workflow skips such a step.
4. **The sessions' rules** (the ruling on step 0a): `CLAUDE.md` rule 2 and principle 3 say never stacked on another's unmerged change, a dependence is declared with `Depends-on: #n`, one open pull request per session,
   several sessions may have one each in flow mode and, in strict mode, a person has one open pull request at a time (both files are installed verbatim, so the strict-mode sentence keeps the text true for a project).
5. **Guide**: a section "Developing the kit" in `docs/guides/reference.md` names the changelog line, the release pull request and the one command, `python3 scripts/agk/kit_hashes.py --write`, for a collision.
6. Amendment 50 (`docs/runs/proposed-spec-amendments-50.md`) is applied to SPEC-0008 and SPEC-0025. `docs/requirements.md` sets REQ-035 `done`.
7. **Kit 0.54.0**: the manifest `kit_version`, the hashes, the plugin version and `version` in `agk.toml`. This build bumps itself: it is the last kit build that does (it is built while this repository's builds are serial); the next
   build adds a changelog line instead.

## Consequences

- Independent kit builds no longer collide on the version lines; they collide at most on the table of hashes and on `## Unreleased`, each with one stated resolution.
- A project that upgrades gets the new `CLAUDE.md` rule 2 and principle 3; nothing it runs changes.

## Residual

None.
