# ADR-0181: a project learns when its kit is behind and what a newer release offers it (REQ-038, brief 320)

- Status: Proposed
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0017, ADR-0018, ADR-0108, ADR-0178
- Requirements: REQ-038

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`

## Context

Brief #320 (priority 1): on 2026-10-30 the kit released 0.59.0 with features built for problems a running pilot hit, while
the pilot was still on an older release. Nothing told the project it was behind, and features that are off by default
(`[proof]`, `unused_code`, `coverage`, `review_mode`) are switched on only by someone who reads the changelog. The brief names
no `Measured:` line. The tests were written first (`tests/kit/test_doctor_kit_behind.py` and
`tests/kit_dev/test_upgrade_opt_in.py`: 28 of 30 failed at the first checkpoint of the pull request).

## Decision

1. **The doctor (answer 1).** A warning `kit-behind`, after `kit-version`. With `--kit-root` it reads the `repository` of the
   kit's `.claude-plugin/plugin.json` (a github.com URL) and makes one GET, `gh api repos/{kit owner}/{kit repo}/releases/latest`;
   with `--api-dir` the recorded file is `kit-release.json`. The tag (`vX.Y.Z` or `X.Y.Z`) and `version` in `agk.toml` are
   compared as numbers. Older fails, and the message names both versions, as the brief asks: `(installed X, newest release Y)`.
   Equal is `ok`; newer (a checkout between releases) is `ok` with `(newer than the newest release: a checkout between
   releases)`. A release that cannot be read is `cannot-check`: `no-kit-root` without `--kit-root`; `bad-response` for an
   unreadable plugin file, an unreadable installed version or a tag that is not a version; `not-github` for a repository not
   on github.com; `no-release` for a 404; `release-unreadable` for a 403 (a rate limit or a private repository; the
   project-side reason `no-admin` would point to admin rights, which do not help here); and the classes of `gh` itself
   (`gh-missing`, `gh-unauthenticated`, `offline`). It is never `ok` without a readable release. The fix is to run
   `/agk:upgrade` with the newest kit release.
2. **The marker (answer 2).** A changelog fragment may end with one marker, `- <one-line change> (opt-in: <setting>)`, where
   the setting is a key of `agk.toml` or a dotted `table.key` (`[a-z][a-z0-9_]*`, joined by dots); a table is named by its
   name. `check_release.opt_in` reads it: a line with no marker, a marker not at the end, more than one marker, or a setting
   of another form offers nothing. The fragment's form (SPEC-0031 rule 1) already allows the marker, and the release moves the
   line unchanged (`check_release.py` rule 5), so the moved line keeps it; a test gathers and checks such a release.
3. **The listing (answer 3).** After a written upgrade (not a dry run, not `nothing to do`, not a refused or failed run),
   `upgrade.py` reads the kit's own `CHANGELOG.md` and prints, last, one line `opt-in: <setting>: <summary>` per entry of each
   released section `## V (<date>)` with old < V <= new that carries a marker, newest section first, in the changelog's order;
   `## Unreleased` is not read. The summary is the change up to its first `: `, cut to 120 characters at a word boundary. With
   none it prints nothing more. A changelog that cannot be read prints one line, `opt-in: the new features cannot be listed
   (path class CHANGELOG.md)`, and the upgrade still exits 0. It writes nothing. The upgrade test kit gained a `CHANGELOG.md`
   with no marker, so the earlier upgrade tests print what they printed.
4. **Tests (answer 4).** Behind, equal, newer (a pre-release checkout), numbers not text (0.9.0 against 0.10.0), and an
   unreadable release in each reason class, in recorded and in live mode with a stubbed `gh`; the doctor case `kit-behind`;
   the marker's forms; a release that keeps it; the listing with and without markers, a dry run, a second run, and an
   unreadable changelog. Settings and entries are invented. The doctor's report counts moved by one, the case
   `version-mismatch` (installed 9.8.0, release 9.9.9) now also fails `kit-behind`, and the live-mode tests read the kit's
   release as one more GET (the not-github test allows that one read, which is of the kit's repository, not the project's).
5. **The spec.** SPEC-0006 (rules 3, 5, 6 and 15), SPEC-0008 (a new rule after rule 12, and rule 20) and SPEC-0031 rule 1 are
   Approved; amendment 98 (`docs/runs/proposed-spec-amendments-98.md`) proposes their changes. The number is the next free one
   after 97 (95 is held for brief #305), to be confirmed (Q-320-1).
6. **Readings taken (the conservative ones).** Q-320-2: a malformed marker fails no check; the line is simply not listed. A
   new failure of the build or the release check is not in the brief. Q-320-3: the summary is the change up to its first
   `: `, since the brief asks for a one-line summary and the kit's lines carry the details after the colon. Q-320-4: the
   released sections of 0.59.0 and earlier carry no marker, and a release may not change an older section (SPEC-0028 rule 5),
   so an upgrade past 0.59.0 lists none of the features the brief's Why names; the solo-mode fragment already on the default
   branch has none either, and a build may not edit another's fragment. Nothing is changed here; adding the markers is a
   maintainers' decision.
7. **Flow mode.** Fragment `changelog.d/kit-behind-opt-in.md`; no version bump. `kit/hashes.json` is not edited (session rule
   14). The kit's `kit/templates/changelog.md` is not changed (the brief's `Touches:` does not list it); the marker is
   documented in `docs/guides/reference.md`.

## Consequences

- A project whose doctor runs with the plugin sees `kit-behind` until it upgrades, and learns the newest version's number.
- The doctor makes one more GET, to the kit's repository; a project offline or without `gh` sees `??`, never `ok`.
- An upgrade lists only what the changelog marks; a feature whose line has no marker is not offered.

## Residual

- 2026-10-30: the releases up to 0.59.0 carry no opt-in marker (Q-320-4), so their off-by-default features are not offered by
  an upgrade (due 2026-12-15).
