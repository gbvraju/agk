# ADR-0208: a local check run leaves a record of what ran (REQ-039, brief 374)

- Status: Proposed
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0186
- Requirements: REQ-039

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

Brief #374 (priority 1, split from #288 part 3). In local mode (#322) a builder pastes its result into the pull request body
by hand, and nothing ties that text to a head, a command or an output. `prepush.py` (#326, ADR-0186) already runs the right
steps in order. The tests were written first (`tests/kit/test_prepush_record.py`).

## Decision

1. **The record (answer 1).** `prepush.py --record FILE` writes one JSON object with `schema: 1`, `head` and `base` (full
   shas; `base` is the commit of the resolved base ref), `started` (UTC, `YYYY-MM-DDTHH:MM:SSZ`), `tree_clean` (from
   `git status --porcelain`, read before any step runs), `versions` (python3, and git, make and gitleaks where found; a tool
   that is installed but prints no version line is `unknown`, a missing one is left out), `steps`, `not_run` and `result`
   (`passed` or `failed`). Each step that ran, skipped ones included, has `name`, `outcome`, `not_run`, `argv`, `cwd`,
   `exit` (`null` for a step that ran nothing), `seconds`, `output_sha256` and `output_bytes` (of the step's whole output
   as UTF-8). The tests step adds `runs`: for each run the test plan selected, its `name`, `command` (the project's own
   command from `agk.toml`), `cwd`, `exit` (`null` on a timeout), `seconds` and its output digest.
2. **Nothing that can carry a secret (answer 1).** The record holds no output text and no environment variable. An argument
   that is a path outside the repository is written `<outside>/<file name>`, a kit script `scripts/agk/<name>`, the running
   interpreter `python3`; a folder is relative to the repository root.
3. **The evidence line (answer 2).** With `--record`, prepush prints
   `Evidence: prepush schema 1, head <sha12>, <n> steps ok, record <first 12 hex of the file's sha256>` after writing it.
   The file is written as sorted, indented JSON with a final newline, so the digest is of the exact bytes on disk.
4. **Unchanged without `--record` (answer 3).** A failed step still writes the record and the evidence line, and the exit
   stays 1. A record file whose folder does not exist, or that cannot be written, exits 2 with
   `prepush: the record file cannot be written (option: --record)`, naming the option, never the value.
5. **Not in this decision (answer 4).** The record is not signed (a person's decision); the local-mode guide and the check of
   the record come with brief #28804. Flow mode: fragment `changelog.d/prepush-record.md`; no version bump.

## Consequences

- A conductor or a person can compare the evidence line to the record file and the record's `head` to the pull request
  head; the digests show that a step ran and what it printed, without the text.
- The interpreter's own version is read from the running Python; the others by `<tool> --version` (`gitleaks version`),
  which runs only with `--record`.

## Residual

- 2026-10-30: the record is plain JSON and anyone can write one by hand until signing is decided (answer 4; due 2026-12-31).
