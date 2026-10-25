# ADR-0133: a check on every pushed tag (brief #212 build (b), SPEC-0028 rules 4 and 5)

- Status: Proposed
- Date: 2026-10-25
- Deciders: maintainers
- Related: ADR-0096, ADR-0108, ADR-0134
- Requirements: REQ-035

Protected classes: `.github/`, `scripts/agk/`, `kit/`, `tests/kit/`, `tests/kit_dev/`

## Context

A tag `v0.55.0` and a GitHub release of that name were made by hand on a commit that was not a release (the merge commit of #208: the changelog still listed the fragments as unreleased, the version read 0.54.0 and
`kit/hashes.json` was 0.54.0's), so it was not a release a project could upgrade to. The maintainers approved on 2026-10-26 a check on every pushed tag (brief #212, the comment of the conductor on build (b)). Build (a) was the
release pull request (#214), which `check_release.py` limits to the release files, so this is its own pull request. ADR-0133 and amendment 69 were reserved on #212. The tests were written first
(`tests/kit_dev/test_check_tag.py`); on the unchanged tree all 12 failed, and after the build they pass.

## Decision

1. **The workflow** `.github/workflows/agk-tag.yml` runs on the push of a tag `v*`, checks the tagged commit out with `fetch-depth: 0` and runs `scripts/agk/check_tag.py --tag "$GITHUB_REF_NAME"`. It is this
   repository's own workflow: it is not in `kit/manifest.json`, because its script is kit-only and a project would get a workflow that cannot act (the verdict on the first head). The permissions are `contents: read`
   and `issues: write`.
2. **The check** `scripts/agk/check_tag.py` (kit-only) fails, naming the first check that failed and no value, when the tag is not `vN.N.N`; when `agk.toml`, `kit/manifest.json` or `.claude-plugin/plugin.json` states another
   version; when `CHANGELOG.md` has no section `## <version> (`; when a fragment is left under `changelog.d/`; or when `kit_hashes.problems(root, <first parent>)` is not empty, which compares the row of the new version.
3. **The issue.** On a failure the job fails and opens, or updates when it exists open, the one issue `The tag <tag> is not a release`, labelled `agk-release` (the step creates the label when it is missing). It is a plain
   issue for a person, not a brief: only a person can fix a tag, and a brief would be handed to a builder by `session.py next`. It has no `Priority:`, `Advances:` or `Touches:`; it names the commit, the failing check with its
   output and the fix: delete the tag and its release and tag the merge commit of the release pull request. The check writes the issue as JSON (`--issue-json`); the workflow step is the only thing that calls GitHub. It deletes
   nothing, moves no tag, makes no release and no commit.
4. **The guide** (`docs/guides/reference.md`, the release section) says: tag only the merge commit of a release pull request, and what the workflow does. Amendment 69 (`docs/runs/proposed-spec-amendments-69.md`) is applied to
   SPEC-0028 rules 4 and 5. Flow mode: fragment `changelog.d/tag-check.md`; no version bump; `CHANGELOG.md` and `kit/hashes.json` as on `main`.
5. **Readings taken where the brief leaves a point open** (questions in the pull request, the most conservative reading each): the hashes are compared against the first parent of the tagged commit, so that the row of a new
   version is compared and not skipped as a row between releases; a tag on a commit with no parent is compared with itself; the tagged commit is HEAD of the checkout; the issue is not a brief (the verdict on the first head).

## Consequences

- A tag made by hand on a commit that is not a release fails at once and leaves one issue that tells the maintainers what to do; nothing is changed for them.
- A project receives nothing: the workflow and its script are the kit repository's own.

## Residual

- 2026-10-25: the check runs after the tag exists; it cannot stop a tag from being pushed, and it does not look at a GitHub release made without a tag (due 2026-12-31).
