# Changelog

The shape of the changelog of a repository that releases in flow mode (SPEC-0028, SPEC-0031). A line is `- #<n> <one-line change>`: the number of the pull request and what it changes. A build pull request does not edit this file: it adds one file `changelog.d/<slug>.md` holding one line, `- <one-line change>`, without a number. A release pull request runs `python3 scripts/agk/changelog_fragments.py gather --version <version>`, which moves the lines under `## Unreleased` and the line of every fragment, in pull request order, under a new heading `## <version> (<YYYY-MM-DD>)` placed directly below `## Unreleased`, which stays and is left empty, and deletes the fragments. Releases are listed newest first.

## Unreleased
