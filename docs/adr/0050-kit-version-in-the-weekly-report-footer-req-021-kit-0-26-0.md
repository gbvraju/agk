# ADR-0050: the weekly report footer names the kit version (REQ-021, SPEC-0014), kit 0.26.0

- Status: Proposed
- Date: 2026-10-20
- Deciders: maintainers
- Related: ADR-0045, ADR-0049, ADR-0036
- Requirements: REQ-021

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `kit/`, `.claude-plugin/`, `agk.toml`

## Context

PR C of the first full cycle on AGK itself (the maintainers' brief of 2026-10-19). REQ-021 was taken in by intake (ADR-0045) and SPEC-0014 was Approved with the open question ruled (no release-notes
file now). This ADR builds it, tests first: the tests for AC1 to AC3 were written and shown failing on `main` before any code (31 failed, 2 passed; the output is in the pull request body).

## Decision

1. **One reader** (rule 2): `common.installed_version(root)` returns the `version` of `agk.toml` or, when `agk.toml` is absent, the `version` of the legacy `[tool.agk]` table of `pyproject.toml`, and
   None when a file is missing or unreadable or the value is not a string (rule 3: nothing falls back to the manifest, to another file or to a constant). `facts.py` and `upgrade.py` call it.
   `upgrade.read_stamp` takes its version from it and keeps every refusal and message; the 116 tests of `upgrade.py` and the end-to-end test pass unchanged, so its outputs on the existing fixtures are the same.
2. **The facts carry it** (rule 1): the optional top-level property `kit_version` (the string, or `"unknown"`). `schema` stays 1; `kit/facts-schema.json` lists the property and does not require it.
3. **The footer line** (rule 4): the report's footer prints `kit version: <value>` directly after the `facts:` line, with no link; `unknown` when the facts carry none or a value that is not a non-empty string. The
   inbox output is unchanged (Q-K4-202, `proposed-spec-amendments-25.md`, applied here). The renderer still reads only the facts file and its imports are unchanged (rule 5).
4. **Tests**: `tests/kit/test_installed_version.py` (new, installed) for the reader; `tests/kit/test_facts.py` for the facts (a fixture repository with a version, seven that give `unknown`, a legacy stamp, and a
   check that `facts.py` does not read the version itself); `tests/kit/test_product_report.py` for the footer; `tests/kit_dev/test_upgrade.py` for the shared reader in `upgrade.py`. The eleven facts goldens gain
   `"kit_version": "unknown"` (no fixture tree has a version) and the fourteen report goldens gain the line `kit version: unknown`; the inbox goldens are byte-identical. All were regenerated and the diffs read.
5. **Kit 0.26.0**: manifest (the new installed test file), hashes, plugin version.
6. **Amendment 25** (`docs/runs/proposed-spec-amendments-25.md`) is applied to SPEC-0014 rule 5.
7. **This repository records its version** (Q-K4-201, ruled by the maintainers 2026-10-20): `agk.toml` gains `version = "0.26.0"`, the `kit_version` of `kit/manifest.json`, and a kit-only test
   (`tests/kit_dev/test_kit_manifest.py`) fails when the two differ. It was written first and failed before the line was added. **Every kit bump updates both `kit/manifest.json` and `agk.toml`
   (and `.claude-plugin/plugin.json`) from now on.** The report of this repository then prints `kit version: 0.26.0`.

## Consequences

- The next weekly report names the kit version it was rendered with, so a reader can tell which rules produced it. In a repository that does not record a version the line says `unknown`.
- A report rendered from a facts document made before this change prints `kit version: unknown`.

## Questions

| Q | Question | Reading taken (conservative) |
| --- | --- | --- |
| Q-K4-201 | This repository's own `agk.toml` has no `version` (it is the kit's source, not an install), so its report would print `kit version: unknown`, and the brief's validation (the footer names the kit version, run on this repository) would show `unknown` | ruled (maintainers, 2026-10-20): this repository records its version; decision 7 |
| Q-K4-202 | SPEC-0014 rule 5 says the inbox output "has no footer"; it has a short one (`facts:` and the dirty notice) | the line is in the report's footer only, the inbox output is unchanged; the wording is amended by `proposed-spec-amendments-25.md` Ruled as read (maintainers, 2026-10-20). |
| Q-K4-203 | The existing test `test_the_footer_names_the_commit_and_the_two_issues` asserts the end of the report | it gains the new line between `facts:` and `metrics:`, which rule 4 requires; no assertion is weakened Ruled as read (maintainers, 2026-10-20). |
| Q-K4-204 | A `kit_version` in the facts that is not a string, or is empty | the footer prints `unknown`; nothing is converted or guessed Ruled as read (maintainers, 2026-10-20). |

## Deviation

- 2026-10-20: commit `311a081` of this branch was committed and pushed after a `make test` that exited 2 (7 failed, 1451 passed, 3 skipped: two tests of `test_facts.py` and the five nested runs of the
  installed tests in the init and adopt targets), because only subsets of the tests had been run. The next commit fixed it. The standing rule, restated by the maintainers on 2026-10-20: **the full
  `make test` passes before every push, no exceptions; subsets are not enough.**

## Residual

none
