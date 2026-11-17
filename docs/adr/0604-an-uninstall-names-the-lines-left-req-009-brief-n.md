# ADR-0604: An uninstall names the lines left

- Status: Proposed
- Date: 2026-11-17
- Deciders: maintainers
- Related: brief #1443, ADR-0196, ADR-0203, ADR-0481
- Requirements: REQ-009

Protected classes: `scripts/agk/`, `tests/kit_dev/`

## Context

The uninstall rule (ADR-0196, built by ADR-0203) deletes every kit file and never edits the project's own work. On a
clean-repository probe of tag v0.64.8 it left 0 kit files, but 8 lines of the project's own files still named a removed
kit path: 2 settings lines in `config/reviewers.yaml` and 6 record lines under `docs/adr/` and `docs/runs/`. The report
did not mention them, so the person found them only by searching.

## Decision

1. After the kit files, the report of `uninstall.py` (a dry run and `--write` alike) prints
   `Left in your files: <n> lines name removed kit paths`, then each line as `path:line: <text>`, at most 40, and
   `and <k> more` after; with none it prints `Left in your files: none`. `--pause` removes nothing and prints no section.
2. Lines in settings (`config/`, `.github/`, `agk.toml`) come first under `tidy by hand:`, then the lines of any other
   file that is not a record; lines in records (`docs/adr/`, `docs/runs/`, `CHANGELOG.md`) come last under
   `records, keep as written:`. Within each, by path and line.
3. A line counts when one of its path-like words names, as whole segments, a removed file, a directory the removal
   empties, or a path inside a directory that held a removed file; a leading `./` and a trailing `.`, `,`, `:`, `;` or
   `/` are ignored. So `scripts/agkx/` and `src/scripts/agk/` do not count.
4. The removed files and `.git/` are never read; a file the plan edits is read as the plan leaves it, so both runs give
   the same section. A named pipe or a device file is never opened. Binary files (a NUL byte in the first 8 KiB, or
   not UTF-8), files over 1 MB and files the account cannot read are skipped and counted on one line
   `skipped: <n> binary, large or unreadable files`.
5. The section is read only: the uninstall edits none of these lines and gains no flag to do so; `--remove-docs` keeps
   its meaning. This adds to the uninstall rule of ADR-0196 and changes none of its decisions.

## Consequences

The person sees the leftovers in the same report and finishes the clean-up by hand, knowing nothing else names the kit.
A sidecar in personal mode has no project files to search and reads `none`.

## Residual

- None.
