# ADR-0086: declared dependence and the pull-request mode (REQ-032 part c, Depends-on and pr_mode, SPEC-0025 rules 5 to 7), kit 0.49.0

- Status: Accepted
- Date: 2026-10-24
- Deciders: maintainers
- Related: ADR-0082, ADR-0085
- Requirements: REQ-032

Protected classes: `.claude-plugin/`, `.github/`, `agk.mk`, `agk.toml`, `docs/requirements.md`, `kit/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`

## Context

SPEC-0025 part (c) was split in two (ADR-0085). The first half, the author rule, is merged. This is the second: a pull request body may declare `Depends-on: #n`, a check fails while the named pull request is not merged,
and each repository chooses `strict` or `flow` for how many pull requests a person may have open. The tests were written first.

## Decision

1. **`scripts/agk/check_pr_mode.py`** (installed verbatim; the twelfth governance step, `pr-mode`): reads `pr_mode` (`strict` by default; any other value is refused naming the setting), the body file, and two files
   the workflow fetches. A `Depends-on: #n` line fails in strict mode (`rule 6`); in flow mode it fails while a named pull request is not merged in the states file (`rule 5`, naming the number) and prints
   `skipped (no states file)` without the file. In strict mode a pull request whose author has an older open pull request in the open-pull-requests file fails (`rule 6`, naming the older number); without the file it prints
   `skipped (no open pull requests file)`. In flow mode both pass. `--list-depends --body FILE` prints the numbers, for the workflow. No network call.
2. **`pr_mode`** in `common.py` (`DEFAULT_CONFIG`, `pr_mode(root)`), in the `agk.toml` templates of `init` and `adopt` and in this repository's `agk.toml` (`strict`: this repository does not switch to flow here; rule 8 says that is a
   separate pull request). `common.json_records` reads a file written by `gh api` (an array, pages or one object a line).
3. **The workflow** `governance.yml` gains one step before the checks that fetches, with `gh api --method GET` only, the state of each named pull request and the open pull requests of the author into files in the
   runner's temporary directory, and the `check_pr_mode` step. The permissions stay `contents`, `pull-requests` and `issues`, each `read`. A named pull request that cannot be read counts as not merged.
4. **The doctor** gains the local check `pr-mode` (warn), whose `ok` message states the mode; the getting-started guide describes the mode and the `pr-mode` failure.
5. Amendment 45 (`docs/runs/proposed-spec-amendments-45.md`) is applied to SPEC-0001, SPEC-0002, SPEC-0006 and SPEC-0007.
6. **REQ-032 is `done`**: parts (a) (#141), (b) (#143), (c) first half (#144) and this second half are built; every criterion AC1 to AC8 has its `REQ-032 ACn` test marker (AC3 on the union test in `tests/kit_dev/test_kit_manifest.py`).
7. **Kit 0.49.0**: the manifest `kit_version` and the new verbatim file, the hashes, the plugin version and `version` in this repository's `agk.toml`.

## Consequences

- With the check installed here, this repository stays strict: a second open pull request by the same author fails `pr-mode`. The maintainers' docs-only exception (SPEC-0025 residual) lapses; the switch to flow is its own pull request.
- A project that upgrades gets `pr_mode = "strict"` by default; nothing changes for a team that already works one pull request at a time.

## Residual

None.
