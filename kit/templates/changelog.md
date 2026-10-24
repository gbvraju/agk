# Changelog

The shape of the changelog of a repository that releases in flow mode (SPEC-0028). A line is `- #<n> <one-line change>`: the number of the pull request and what it changes. A build pull request adds its line under `## Unreleased`. A release pull request moves the lines, unchanged and in order, under a new heading `## <version> (<YYYY-MM-DD>)` placed directly below `## Unreleased`, which stays and is left empty. Releases are listed newest first.

## Unreleased
