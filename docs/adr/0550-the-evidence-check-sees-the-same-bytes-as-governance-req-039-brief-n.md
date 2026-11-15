# ADR-0550: The evidence check sees the same bytes as governance

- Status: Accepted
- Date: 2026-11-14
- Deciders: maintainers
- Related: ADR-0233, ADR-0257, ADR-0449, ADR-0536, ADR-0542, SPEC-0037, brief #1291, plan #661
- Requirements: REQ-039

## Context

In a project in local mode on a Windows cloud PC (Git for Windows), `python3 scripts/agk/evidence.py check <record>
--head <sha>` reported `differs` on two pull requests whose `make governance` the conductor had just run green on the same
head: in the evidence check's own worktree `check_design.py` failed rule 5 (the runtime's hash), rule 9 (a signed-off
version's digest) and rule 15 (imported files against `manifest.json`). Measured on Linux (brief #1291 answer 1, posted on
the pull request before any change): a worktree added with `core.autocrlf=true` in the person's git configuration
(Git for Windows' default), which `evidence.py` inherits, checks the text files out with CRLF line ends and reproduces
exactly those three rules; `core.autocrlf=false`, `core.eol=crlf` alone and a 150-character temporary path do not. The
conductor's run, `git worktree add` and then `env -i PATH="$PATH" HOME=<scratch> AGK_BASE=<base> make ... agk-governance`
(`docs/guides/local-mode.md`), saw the committed LF bytes. The digests of rules 5, 9 and 15 are of the bytes on disk.

## Decision

1. `scripts/agk/evidence.py` adds its worktree with `git -c core.autocrlf=false -c core.eol=lf worktree add`, so that the
   worktree holds the committed bytes whatever the person's git configuration says; a project's own `.gitattributes`
   still applies, as in CI.
2. It runs governance with the conductor's environment: `PATH`, a scratch `HOME` made inside its temporary folder and
   removed with it, and `AGK_BASE` set to the record's `base`; on Windows also `SYSTEMROOT`, `WINDIR`, `COMSPEC` and
   `PATHEXT`, which Python and the shell need to start, `USERPROFILE` as that `HOME`, and the long temporary folder in
   `TEMP`, `TMP` and `TMPDIR` (ADR-0257). The person's own `HOME`, git configuration and tokens no longer reach it. The
   re-run of the sampled steps keeps the environment the record was made in (`run_env`), since it compares exit codes
   with that run.
3. The digests of rules 9 and 15 read a file's committed bytes when the checkout changed only its line ends:
   `common.committed_bytes(root, files)` replaces the bytes on disk of a file that holds a CRLF by its index blob when that
   blob equals those bytes with every CRLF turned to LF, read with `git ls-files -s` and `git cat-file --batch` (read only,
   no network, nothing written). `design_signoff.digest` (rule 9, which `design.py signoff` writes and `check_design.py`
   compares) and `design_import`'s reading of an imported version's files for its check (rule 15) use it. This is the
   brief's "read the blob from git": `design_signoff.py` and `design_import.py` write their digests from the bytes they
   read with no normalisation, so the committed bytes are what both took on an LF checkout. A file with no CRLF on disk
   is read from disk and runs no git, so an LF checkout (CI, the conductor's, Linux and macOS) gives the result it gave
   before; a file committed with CRLF, an untracked file, a change beyond the line ends and a folder outside git keep the
   bytes on disk. `design.py import` still records the bytes it copies.
4. The path length of the temporary folder is not changed: it was not the cause measured.

No workflow file, ruleset, `constitution/` file or spec changes.

## Consequences

In local mode a correct record agrees with the conductor's governance run on the same head, also on Windows with
`core.autocrlf=true`; a really changed signed-off file still fails rule 9 in both runs. In CI mode no evidence record is
used and the design checks give the same result as before on an LF checkout. In personal mode there are no pull requests;
a person's own CRLF checkout now gives the rule 9 and rule 15 results of CI. Tests: `tests/kit/test_evidence_matches_governance.py`.
Protected path classes changed: `scripts/agk/` (`scripts/agk/evidence.py`, `scripts/agk/common.py`,
`scripts/agk/design_signoff.py`, `scripts/agk/design_import.py`) and `tests/kit/`
(`tests/kit/test_evidence_matches_governance.py`); `kit_hashes.py` leaves `kit/hashes.json` unchanged.

## Residual

- 2026-11-14: rule 5's runtime hash (`design_prototype_check.py`) still reads the bytes on disk, so a person's own CRLF
  checkout of a prototype version fails rule 5 there, as it did before; the evidence check no longer does (Q-1291-1).
- 2026-11-14: `doctor.py`'s reading of an imported version still reads the bytes on disk (Q-1291-1).
- 2026-11-14: an import made on Windows with `core.autocrlf=true` from a source with CRLF files records CRLF digests,
  while git commits LF: the manifest then fails rule 15 in CI and now also locally, as it already did in CI (Q-1291-2).
