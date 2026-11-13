# ADR-0386: The survey reads a codebase and never runs it

- Status: Accepted
- Date: 2026-11-09
- Deciders: maintainers
- Related: SPEC-0041 rules 10 to 12 and 30 (f), ADR-0267, SPEC-0002 rule 3, Q-S0041-13, brief #852
- Requirements: REQ-048

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`, `agk.toml`

## Context

SPEC-0041 build (f) adds `scripts/agk/survey.py`, the part of personal mode that reads a codebase before any decision is
drafted from it. ADR-0267 decision 10 names `scripts/agk/`, `kit/` and `tests/kit/` for the builds and requires each build
to add an ADR naming the classes it changes. SPEC-0057 build (d) and SPEC-0055 build (i) wait for this script.

## Decision

This is build (f) of SPEC-0041 rule 30, and it changes no decision of the spec or of ADR-0267.

1. `scripts/agk/survey.py` is new and installed (`kit/manifest.json`, verbatim), and `agk.toml` gains its `[[testing.map]]`
   entry. Nothing else in the kit calls it yet.
2. It reads each blob from git's object store, from the list `git ls-files --stage` gives and `git cat-file` serves, and
   never opens the work tree. An untracked file is out of reach and a symlink is not followed, by construction. Modes
   `120000` and `160000` are listed, not read. A blob over 1 000 000 bytes is listed from its size, and is not fetched.
3. The inventory lives in `cache/inventory.json` of the sidecar, and the ledger is its `ledger` map, so losing `cache/`
   loses the ledger, as the spec's residual says. A ledger that cannot be read is refused, never emptied.
4. `<total>` of the coverage line counts the text files the survey measured; a binary, a symlink, a submodule or a file
   over the limit is listed under `skipped` and counted in neither number.
5. `personal_state.py` is not installed in a project (`config/kit-only.txt`), so `survey.py` imports it only when no
   `--sidecar` is given, and an installed copy without it refuses, naming the option.

## Consequences

A person in personal mode can list a codebase without running a line of it, spending a budget of reads and seeing the
coverage. An inventory describes the index, so a change that is not staged is not seen until it is.

## Residual

The import patterns are line patterns: a name that matches a tracked file by chance adds to its fan-in, and only the
ordering of the reading list depends on it. Review by 2027-01-31 with `Q-852-2`.
