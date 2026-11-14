# ADR-0532: A release row is checked against its commit

- Status: Accepted
- Date: 2026-11-14
- Deciders: maintainers
- Related: brief #1259, brief #1257, PR #1258 (Q-1257-1), SPEC-0028 rule 4, ADR-0108
- Requirements: REQ-038

Protected classes: `scripts/agk/`, `tests/kit_dev/`

## Context

The 0.64.3 release row of `kit/hashes.json` carried `commits: []` and named a fingerprint of `scripts/agk/doctor.py`
(`99f707fc`) that the release commit b097acc did not ship (`1bd6cdf3`), and `kit_hashes.py --check` printed
`ok kit-hashes`. In flow mode, between two releases, the check skips the current version's row (ADR-0108
decision 4), because builds change installed files and only the next release regenerates the row; so a stale row
of the version just released was never compared with anything. Brief #1257 answer 2 asked for the check; a release
pull request may change only its release files, so it is built here.

## Decision

1. `kit_hashes.py --check` fails every release row, except the current version's, whose `commits` list is empty,
   with one line `kit/hashes.json: row <version> lists no commits`.
2. Every row with a commit is checked against its last commit: each fingerprint path in `verbatim` whose file at
   that commit hashes to none of the row's digests (or is missing there) fails with one line naming the version and
   the path, never a digest.
3. The current version's row: in a release pull request and in strict mode it is compared with the working tree as
   before. Between two releases in flow mode, when its `commits` list is empty, it is checked as in decision 2
   against its release commit, the first first-parent commit up to the base whose `kit_version` is the current
   version; the working tree is not used there, since builds after the release legitimately change it.
4. The check still refuses a shallow clone, as before; it reads only local git history, no network.

## Consequences

On b097acc the check now fails with two lines naming 0.64.3, one for `scripts/agk/config.py` and one for
`scripts/agk/doctor.py`. The repository's own table
passes. No workflow changes; governance runs the check as before. Projects do not run it (the script is kit-only).

## Residual

- None.
