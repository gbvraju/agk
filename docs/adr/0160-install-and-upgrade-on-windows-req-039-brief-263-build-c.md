# ADR-0160: install and upgrade on Windows (REQ-039, brief 263 build c)

- Status: Proposed
- Date: 2026-10-26
- Deciders: maintainers
- Related: ADR-0108, ADR-0159
- Requirements: REQ-039

Protected classes: `.claude/`, `kit/`, `scripts/agk/`, `skills/`, `tests/kit/`, `tests/kit_dev/`

## Context

Brief #263 lists the gaps the first organisation project met (Windows 11, a private repository of an organisation on GitHub
Free, kit 0.56.0 then 0.57.0). Build (c) is items 7 to 10: line endings, install from a release, an invalid configuration that
names the key, and text encoding (the conductor's answer to Q-263c-1 on #268). Each cause was reproduced first, with a fixture,
on the unchanged tree:

- item 7: an init target whose kit files are checked out with CRLF, as Git for Windows does with `core.autocrlf=true`, is refused
  by `upgrade.py` ("differs from every released copy" on every file);
- item 8: `init.py` run from a kit whose files differ from the release row of its `kit_version` installs them and stamps that
  version (exit 0);
- item 9: `spec_approvers` indented under `teams:` gives `config/reviewers.yaml is invalid; run --check` with
  `--codeowners` and `--check-codeowners`, and `--check` names a wrong cause (`team 'spec_approvers': github_team must be ...`);
- item 10: under an ASCII locale with Python's UTF-8 mode off, `common.show` (`git show`) fails to decode a line with an em dash
  that the working copy, read as UTF-8, holds.

The tests were written first and were red on the unchanged tree: 12 of the first checkpoint (items 7 and 9), 4 of
`tests/kit_dev/test_install_from_release.py` (item 8), and 2 of `tests/kit/test_windows_install.py` (item 10).

## Decision

1. **Line endings (item 7).** `common.lf` turns CRLF into LF and leaves a file with a NUL byte as it is. `upgrade.py` compares
   a target's kit file, a removed file and a template with the release rows after `lf`, and reads the kit's own files through it,
   so a CRLF plugin cache writes LF copies whose digests match the rows. `init.py` and `adopt.py` read the kit's files through it
   (`init.kit_bytes`) and compare an existing file ignoring CRLF and LF. `doctor.py` compares the same way with its own copy of the
   rule, because it imports no other kit script. A CRLF copy whose text is current is reported `unchanged` and never rewritten; a
   changed line is still a conflict. The installed `.gitattributes` (`kit/templates/gitattributes`, the template of init and the
   block of adopt) gains `text eol=lf` for `scripts/agk/**` and for each other path the kit installs, and nothing for the
   project's own files. A test pins the list to the manifest, and the block sits before the `linguist-generated` line, which stays
   last. An existing init install keeps its `.gitattributes` (created once, never compared); its upgrade relies on the comparison
   above.
2. **Install from a release (item 8, the reading the conductor accepted in Q-263c-2).** `init.py` compares every kit file it
   installs, and every template it renders, with the release row of `kit_version` in `kit/hashes.json`, ignoring CRLF and LF.
   When one differs, or the row is missing, it refuses before it writes anything, the dry run included:
   `refused: the plugin's kit files are not those of release <version> (path class kit/hashes.json); install the plugin at that
   release's tag: the ref of the agk marketplace entry, as printed below; nothing was written`. It then prints the plugin
   settings entries, which carry that `ref`. `--unreleased` installs a checkout between releases as it is, with a notice; the
   kit's own tests use it, and the reference guide says to run init from a release tag. The digests are computed in `init.py`
   over the paths of `kit_hashes.snapshot_of`, because init imports no module that starts a process. The commit-stamp fallback of
   the brief is not built (residual).
3. **Invalid configuration names the key (item 9).** `reviewers.py` finds a top-level key (`version`, `classes`, `teams`,
   `verdict_authors`, `spec_approvers`) indented under `classes` or `teams`, takes it out of that mapping and reports
   `<key> is indented under <section>: it is a top-level key, so write it at the start of its line`. Any invalid file now
   refuses with `config/reviewers.yaml is invalid: <each problem>`, naming keys and reasons, never a handle.
4. **UTF-8 (item 10).** Every subprocess call of the kit's scripts and hooks that reads text passes `encoding="utf-8"` with
   `text=True`. This covers `git show`, `git diff` and `gh api` output. Standard input is read as `sys.stdin.buffer` decoded
   as UTF-8. Every `read_text`, `write_text` and text `open` already named UTF-8. A test walks the syntax tree of every kit
   script and hook, and a second runs `common.show` under an ASCII locale with UTF-8 mode off.
5. **Tests.** `tests/kit_dev/test_windows_line_endings.py`, `tests/kit_dev/test_install_from_release.py` and
   `tests/kit/test_windows_install.py`. The brief's `Touches:` names `tests/kit/test_pilot_gaps.py`; that file is left to builds
   (a) and (b), so that the three builds never edit one test file. The upgrade and init tests are in `tests/kit_dev/`, because
   those scripts are never installed. Flow mode: fragment `changelog.d/windows-install.md`, no version bump.

## Consequences

- On Windows, an untouched install upgrades, the doctor reports no false difference, and kit copies stay LF.
- `/agk:init` from a plugin that follows the default branch between releases refuses and says where to pin the release, instead
  of stamping a version whose files it does not have.
- A misplaced key in `config/reviewers.yaml` is named with its cause.
- Kit scripts read `git`, `gh` and standard input as UTF-8 whatever the platform's code page.
- `adopt.py` does not check the release row, so an adopt from a kit between releases still stamps the last release (residual).

## Residual

- 2026-10-26: the commit-stamp fallback of item 8 (record the exact commit when installing from a tag cannot be done, and let
  `upgrade.py` and `doctor.py` read it) is not built: upgrade would need the files of a commit that has no release row, which its
  contract (no git, no network) excludes (Q-263c-2, due 2026-12-31).
- 2026-10-26: `adopt.py` installs from a kit between releases without the check of item 8 (due 2026-12-31).
- 2026-10-26: whether the plugin cache on Windows is unpacked with CRLF, and whether it is a git checkout with tags, is taken
  from the brief, not confirmed by this session (verify) (due 2026-12-31).
- 2026-10-26: the after measurement of the brief (the same Windows sequence with no workaround) is to be taken on the project's
  machine; this session has no Windows (due 2026-12-31).
