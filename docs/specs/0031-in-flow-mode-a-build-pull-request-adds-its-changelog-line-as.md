# SPEC-0031: In flow mode a build pull request adds its changelog line as its own file, and the release pull request gathers the files into the changelog

- Status: Approved
- Owner: reviewer group (a team from config/reviewers.yaml)
- Requirements: REQ-038

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.
Written by the intake of one sentence (SPEC-0012): "In flow mode a build pull request adds its changelog line as its own file, so two builds open at once never conflict on `CHANGELOG.md`, and the release pull request gathers the files into the changelog." It follows SPEC-0028, whose build pull request adds its line under `## Unreleased` of `CHANGELOG.md`. Evidence: #169 lost its CI for a round because #168 merged a line under `## Unreleased` first; GitHub runs no pull_request workflow on a conflicted pull request, so the session waited with no signal; `kit/hashes.json` is the second shared file and conflicts the same way. It is generic and project-agnostic: it holds for any repository in flow mode and names no repository.
The maintainers gave 5 answers before it was written, in the brief of issue #171 and not as interview questions: (1) a build writes `changelog.d/<pr-or-branch-slug>.md` with one line and does not edit `CHANGELOG.md`, and the flow-mode check fails a build that edits `CHANGELOG.md` and accepts one that adds exactly one fragment; (2) the release pull request runs a script that moves every fragment, in pull request order, under the new version heading and deletes the fragments, and `check_release.py` accepts those deletions as release files; (3) `kit/hashes.json` is measured first, and if the release can regenerate it builds stop touching it, otherwise the ADR records why; (4) the rule is generic; (5) intake first (requirement, spec, ADR), then the build, each its own pull request from the default branch.

## Rules

1. **The fragment.** In flow mode a build pull request adds one file `changelog.d/<slug>.md`, where `<slug>` is the pull request number or the branch slug (`[a-z0-9-]+`). The file holds exactly one line, `- <one-line change>`, and a newline; it carries no pull request number.
2. **The build.** In flow mode a pull request that changes a file the installer writes adds exactly one fragment and does not edit `CHANGELOG.md`. A pull request needs a fragment exactly when SPEC-0028 rule 2 requires a changelog line (the trigger of SPEC-0028 rule 2); one that does not meet that trigger may add a fragment and is not failed for it. The flow-mode check (the check of the bump rule of SPEC-0028 rule 2) fails, naming the rule and the path class and never a value, when `CHANGELOG.md` is edited, when no fragment is added, when more than one is added, or when a fragment does not have the form of rule 1. The line under `## Unreleased` that SPEC-0028 rule 2 requires is replaced by the fragment.
3. **The release script.** A script in `scripts/agk/` (kit-only) run by the release pull request moves the line of every file under `changelog.d/` under the new heading `## <version> (<date>)` of `CHANGELOG.md`, in the order of the pull request numbers, each written as `- #<n> <one-line change>`, deletes the fragments, and writes no other file. The script reads `<n>` from the pull request that added the fragment: the merge or squash commit that added the file (`git log --diff-filter=A`), whose subject carries `(#<n>)`. A fragment whose pull request number cannot be read stops the script. `## Unreleased` stays and is empty.
4. **The release check.** `check_release.py` (SPEC-0028 rule 5) adds `changelog.d/` to the files a release pull request may change, accepts the deletion of a fragment and nothing else there, and fails, naming the rule and the path class, when a fragment is left, when a fragment line is not under the new heading with its `#<n>` and in order, when the pull request number of a fragment cannot be read, or when a fragment is added or edited.
5. **Strict mode.** In strict mode nothing changes: no fragment is required and `CHANGELOG.md` is as before.
6. **`kit/hashes.json`.** Before the build, its ADR records a measurement of whether the release can regenerate `kit/hashes.json` from the files of the release. If it can, a build pull request in flow mode does not edit the file and the check of rule 2 fails one that does; the release regenerates it and `check_release.py` accepts that. If it cannot, the ADR records why and the builds refresh the file as SPEC-0028 rule 2 says.
7. **How it changes.** SPEC-0028 (rules 2, 4, 5 and 6) is Approved: the build changes it by `docs/runs/proposed-spec-amendments-N.md`, applied by its ADR, which names each protected class it touches. The build is its own pull request from the default branch after this intake, tests first.
8. **The tests.** Fixtures in `tmp_path`, with git: a build with one fragment and one with none, two, a malformed line, or an edit of `CHANGELOG.md`, and a change to a file outside the trigger with and without a fragment; strict mode; two builds merged one after the other with no conflict on `CHANGELOG.md`; a release that gathers the fragments in pull request order, one that leaves a fragment, one that changes a line while moving it, one whose fragment has no readable pull request number, and one that touches a sixth file; the regeneration of `kit/hashes.json` if the measurement says it can be. No network and no model.

## Tests

- Rules 1 and 2: a build with exactly one well-formed fragment and no edit of `CHANGELOG.md` passes; REQ-038 AC1.
- Rule 2: a build that edits `CHANGELOG.md` fails naming the rule and the path class; REQ-038 AC2.
- Rule 2: a build with no fragment, more than one, or a malformed line fails; REQ-038 AC3.
- Rule 3: the release script moves the lines in pull request order, deletes the fragments and writes no other file; REQ-038 AC4.
- Rule 4: a release that deletes the fragments passes, and a fragment left, a line not moved unchanged or a fragment without a readable pull request number fails; REQ-038 AC5.
- Rule 5: in strict mode no fragment is required; REQ-038 AC6.
- Rule 6: the ADR of the build records the measurement and the check follows it; REQ-038 AC7.

## Proof

REQ-038 AC1 to AC3: *two builds open at once never conflict on `CHANGELOG.md`.* Rules 1 and 2. REQ-038 AC4 and AC5: *the release pull request gathers the files and a check verifies it.* Rules 3 and 4. REQ-038 AC6: *strict mode is as before.* Rule 5. REQ-038 AC7: *the second shared file is measured, not guessed.* Rule 6.

## Residual

- 2026-10-24: whether the fragment check and the release script are installed in a project or stay kit-only is not decided here; they are written without naming this repository, so installing them later changes no rule (due 2026-12-31).

## Open questions

none
