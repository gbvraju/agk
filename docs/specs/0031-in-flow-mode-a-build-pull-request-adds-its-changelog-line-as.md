# SPEC-0031: In flow mode a build pull request adds its changelog line as its own file, and the release pull request gathers the files into the changelog

- Status: Approved
- Owner: reviewer group (a team from config/reviewers.yaml)
- Requirements: REQ-038

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.
Written by the intake of one sentence (SPEC-0012): "In flow mode a build pull request adds its changelog line as its own file, so two builds open at once never conflict on `CHANGELOG.md`, and the release pull request gathers the files into the changelog." It follows SPEC-0028, whose build pull request adds its line under `## Unreleased` of `CHANGELOG.md`. Evidence: #169 lost its CI for a round because #168 merged a line under `## Unreleased` first; GitHub runs no pull_request workflow on a conflicted pull request, so the session waited with no signal; `kit/hashes.json` is the second shared file and conflicts the same way. It is generic and project-agnostic: it holds for any repository in flow mode and names no repository.
The maintainers gave 5 answers before it was written, in the brief of issue #171 and not as interview questions: (1) a build writes `changelog.d/<pr-or-branch-slug>.md` with one line and does not edit `CHANGELOG.md`, and the flow-mode check fails a build that edits `CHANGELOG.md` and accepts one that adds exactly one fragment; (2) the release pull request runs a script that moves every fragment, in pull request order, under the new version heading and deletes the fragments, and `check_release.py` accepts those deletions as release files; (3) `kit/hashes.json` is measured first, and if the release can regenerate it builds stop touching it, otherwise the ADR records why; (4) the rule is generic; (5) intake first (requirement, spec, ADR), then the build, each its own pull request from the default branch.
Folded into SPEC-0028 (brief #386, amendment 108, ADR-0245): the eight rules below are now rules 11 to 18 of SPEC-0028, text unchanged, and SPEC-0028 rules 2, 4, 5 and 6 carry the text that rule 7 gave them. The number of this spec and its history stay; each rule is a pointer line.

## Rules

1. Now SPEC-0028 rule 11.
2. Now SPEC-0028 rule 12.
3. Now SPEC-0028 rule 13.
4. Now SPEC-0028 rule 14.
5. Now SPEC-0028 rule 15.
6. Now SPEC-0028 rule 16.
7. Now SPEC-0028 rule 17.
8. Now SPEC-0028 rule 18.

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
