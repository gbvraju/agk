# Proposed spec amendments 98 (SPEC-0006, SPEC-0008, SPEC-0031; REQ-038)

Date: 2026-10-30 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). It is applied by
ADR-0181 (brief #320), and it changes `docs/specs/0006-doctor.md`, `docs/specs/0008-upgrade.md` and
`docs/specs/0031-in-flow-mode-a-build-pull-request-adds-its-changelog-line-as.md`. The number 98 is the next free one after 97
(95 is held for brief #305); it waits for the conductor's confirmation (Q-320-1).

1. **SPEC-0006 rule 3.** The reason classes gain `no-release` (the kit's repository answers 404 for its latest release) and
   `release-unreadable` (any other refusal of that read, such as a rate limit), both for `kit-behind` only.
2. **SPEC-0006 rule 5.** A new row after `kit-version`: `kit-behind` | warn | `version` in `agk.toml` is older, compared as
   numbers, than the tag (`vX.Y.Z` or `X.Y.Z`) of the newest release of the kit's repository, the `repository` of the kit's
   `.claude-plugin/plugin.json`; the message names both versions; equal, or newer (a checkout between releases), is `ok`;
   without `--kit-root` it is `cannot-check` (`no-kit-root`) | run `/agk:upgrade` with the newest kit release (SPEC-0008);
   the upgrade ends with the opt-in features the newer releases offer.
3. **SPEC-0006 rule 6.** The reads gain, only with `--kit-root`, `gh api repos/{kit o}/{kit r}/releases/latest` (`tag_name`),
   where `{kit o}/{kit r}` comes from the kit's `.claude-plugin/plugin.json` and a URL not on github.com is `not-github`; it is
   a read of the kit's repository, not of ROOT's, and `--api-dir` records it as `kit-release.json`.
4. **SPEC-0006 rule 15.** `ok/` gains `api/kit-release.json` and `kit/.claude-plugin/plugin.json`; a case `kit-behind`
   (the newest release is ahead of the installed version) reports only `kit-behind`.
5. **SPEC-0008, a new rule after rule 12: opt-in features.** After a run that wrote the upgrade (not a dry run, not
   `nothing to do`, not a conflict or a failed write), the script reads the kit's own `CHANGELOG.md` and prints, after
   everything else, one line `opt-in: <setting>: <summary>` per entry of each section `## V (<date>)` with the old version < V
   <= the new one that ends with one marker `(opt-in: <setting>)` (SPEC-0031 rule 1), newest section first and in the
   changelog's order; `## Unreleased` is not read. The summary is the entry's change up to its first `: `, at most 120
   characters cut at a word boundary. With no such entry it prints nothing more. A changelog that cannot be read prints
   `opt-in: the new features cannot be listed (path class CHANGELOG.md)` and changes no exit code. The listing writes nothing.
6. **SPEC-0008 rule 20.** "a dry run and the following real run print the same lines" gains "apart from the summary line and
   the opt-in lines that only a written run prints (the new rule after rule 12)".
7. **SPEC-0031 rule 1.** "The file holds exactly one line, `- <one-line change>`, and a newline" gains: "A change that a
   project switches on by a setting may end its line with one marker `(opt-in: <setting>)`, the setting a key of `agk.toml`
   or a dotted `table.key` (`[a-z][a-z0-9_]*` joined by dots); the release moves the line, marker included, unchanged
   (rule 3). A malformed marker fails no check; the line is not listed (brief #320, Q-320-2)."
8. **Tests.** `tests/kit/test_doctor_kit_behind.py` and the doctor case `kit-behind`; `tests/kit_dev/test_upgrade_opt_in.py`.
   Their marker is `REQ-038`.
