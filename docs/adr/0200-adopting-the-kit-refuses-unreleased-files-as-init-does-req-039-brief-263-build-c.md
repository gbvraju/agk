# ADR-0200: adopting the kit refuses unreleased files, as init does (REQ-039, brief 263 build c)

- Status: Proposed
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0160, ADR-0194, ADR-0183
- Requirements: REQ-039

Protected classes: `scripts/agk/`, `skills/`, `tests/kit_dev/`

## Context

Brief #263 build (c) is items 7 to 10: line endings, install from a release, an invalid configuration that names the key, and
text encoding. The conductor's field note asks that each item be reproduced on today's main first and that an item already fixed
be recorded, not rebuilt. On 9b73a2a (2026-10-30) all four were already fixed by 37a7824 (#268, ADR-0160, merged 2026-10-27):

- Item 7: `doctor.compare_tree` with a CRLF copy of an LF kit file returns `([], [])`, and `([], ['scripts/agk/x.py'])` on
  37a7824^; `kit/templates/gitattributes` pins `text eol=lf` for `scripts/agk/**` and every installed path.
- Item 8: `init.py <empty repository> --dry-run` from this checkout prints `refused: the plugin's kit files are not those of
  release 0.59.0 (path class kit/hashes.json); install the plugin at that release's tag ...`, exit 1.
- Item 9: `reviewers.py --check` with `spec_approvers` indented under `teams:` prints `FAIL reviewers: spec_approvers is indented
  under teams: it is a top-level key, so write it at the start of its line`.
- Item 10: `intake.py check` on a pure append with an em dash, under `LC_ALL=C PYTHONUTF8=0 PYTHONCOERCECLOCALE=0`, prints the same
  findings as with `PYTHONUTF8=1`; the script of 37a7824^ stops with a traceback there.

ADR-0160 left as a residual that `adopt.py` stamps the release's version without item 8's check. The conductor's answer to
Q-263-C2 on the brief is to build that residual here, and not the commit-stamp fallback. Before this change, `adopt.py` from this
checkout (between releases) installed its files and stamped `kit_version` 0.59.0; the tests were written first and 6 of 8 failed
at the first checkpoint of the pull request (632d2e2).

## Decision

1. **Adopt checks the release (ADR-0160's residual).** `adopt.py` runs `init.release_problem` after the target checks and before
   the plan is built, so before any write and in a dry run too. When any kit file or template it would install is not in the
   release row of `kit_version` in `kit/hashes.json` (CRLF read as LF), it prints `refused: the plugin's kit files are not those of
   release <version> (path class kit/hashes.json); install the plugin at that release's tag: the `ref` of the agk marketplace
   entry, as printed below; nothing was written`, then the plugin settings entries, and exits 1: the same refusal as init, naming
   the path class and the remedy. One function decides for both, so they cannot drift apart.
2. **`--unreleased`.** As for init, `--unreleased` installs the checkout as it is and prints `notice: --unreleased: the kit files
   are not those of release <version> ...`. The kit's own tests that run `adopt.py` from this checkout pass it
   (`test_adopt.py`'s helper, `test_distribution.py`, `test_experimental_reviewer.py`, `test_metrics_wiring.py`, `test_playbook.py`,
   `test_product_report_wiring.py`).
3. **The skill.** `/agk:adopt` says, as `/agk:init` does, to show the refusal and the settings entries and stop, so that the
   person installs the plugin at that release's tag.
4. **The check covers the files written as marked blocks (verdict on 7c7e85c, item 1).** `init.release_problem` in
   `scripts/agk/init.py` compared only the release row's `verbatim` and `templates`. The sources of the marked blocks
   (`kit/templates/gitignore`, and each `adopt.blocks` path that is not rendered) are listed in the row's `blocks`, so an
   unreleased `kit/templates/gitignore` was installed under the release's version by adopt and init alike. `release_problem` now
   also hashes each block source as `kit_hashes.snapshot_of` does (the text without trailing newlines, then one newline, after CRLF
   is read as LF) and compares it with `row["blocks"]`. The one function serves both installers, so init gains the same check.
   Init imports no module that runs a process (SPEC-0001 rule 3, `test_init.py`), and `kit_hashes` does, so the one-line
   normalisation is repeated in `init.block_text`, and a test keeps it equal to `kit_hashes.normalized`.
5. **Not built.** The commit-stamp fallback of item 8 stays ADR-0160's residual, as the conductor answered. The adopt section of
   `docs/guides/reference.md` is not changed here, since two open pull requests change that file (#354, #355); see Residual.
6. **The spec.** `docs/runs/proposed-spec-amendments-102.md` proposes the text of SPEC-0002 rules 1 and 15, and of SPEC-0001's
   release rule, that this changes.
7. **Tests.** `tests/kit_dev/test_adopt_from_release.py` (19): a kit at its release adopts; a CRLF cache at the release adopts with
   LF; a kit between releases is refused, dry run or not, with the target byte for byte as it was; no release row is refused; an
   unreleased adopt template is refused; `--unreleased` adopts with a notice; the usage names the option.
8. **Flow mode.** Fragment `changelog.d/adopt-from-release.md`; no version bump; `kit/hashes.json` is not edited (session rule 14).

## Log

- 2026-10-30, verdict on 7c7e85c (fix list): item 1, the release check missed the block sources; fixed in `release_problem`
  for init and adopt (decision 4), with tests. Item 2, the formatting-only change to `scripts/agk/minutes.py` (from a `ruff
  format` run over the whole tree) is left out of this pull request.
- Q-263-C3: the amendment number 102 is the next free one after 101.

## Consequences

- An existing repository adopted between two releases no longer gets unreleased files stamped with the last release's version,
  which an upgrade would then read as unknown.
- With build (c) recorded, the brief's ten answers are all on the default branch.

## Residual

- 2026-10-30: `docs/guides/reference.md` shows `adopt.py TARGET [--dry-run]` and does not name the release check or
  `--unreleased`; to be changed once #354 and #355 have merged (due 2026-12-15).
- 2026-10-30: ADR-0160's commit-stamp fallback and its Windows measurements stay open there (due 2026-12-31).
