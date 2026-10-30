# Proposed spec amendments 102 (SPEC-0002, SPEC-0001; REQ-039)

Date: 2026-10-30 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). It is applied by
ADR-0200 (brief #263 build (c)), which stays `Proposed` for the maintainers' decision, and it changes
`docs/specs/0002-agk-adopt.md` and `docs/specs/0001-agk-init.md`. The number 102 is the next free one after 101 (Q-263-C3).

1. **SPEC-0002 rule 1, the command.** `python3 scripts/agk/adopt.py TARGET [--dry-run]` reads `python3 scripts/agk/adopt.py TARGET
   [--dry-run] [--unreleased]`, and a sentence is added: "Adopt installs only the files of a release: when any kit file or
   template it would install is not in the release row of `kit_version` in `kit/hashes.json` (compared ignoring CRLF and LF), it
   refuses (exit 1), dry run included, naming the release, the path class `kit/hashes.json` and the plugin's `ref` as the remedy,
   as init does (ADR-0160); `--unreleased` installs the checkout as it is, with a notice, for the kit's own tests."
2. **SPEC-0002 rule 15, the refusals.** "and an unknown default branch each refuse before any write" reads "an unknown default
   branch and kit files that are not those of a release each refuse before any write".
3. **SPEC-0001 and SPEC-0002, what a release is.** A sentence is added where each names the release check: "The files compared
   are the kit files installed verbatim, the templates rendered, and the sources of the marked blocks, hashed as `kit/hashes.json`
   lists them under `blocks` (the text without trailing newlines, then one newline)."
