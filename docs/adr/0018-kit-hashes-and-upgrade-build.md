# ADR-0018: kit/hashes.json and agk upgrade: the build of SPEC-0008

- Status: Proposed
- Date: 2026-10-16
- Deciders: maintainers
- Related: ADR-0001, ADR-0015, ADR-0016, ADR-0017
- Requirements: REQ-009, REQ-010

Protected classes: `scripts/agk/`, `kit/`, `tests/kit_dev/`

## Context

SPEC-0008 (Approved on 2026-10-15) defines `agk upgrade` for K3 criterion c of ADR-0015. The target keeps no lock file
(SPEC-0005 rule 3), so what a file was at the installed version X has to come from the kit. Building it adds two kit-only
scripts (`scripts/agk/upgrade.py`, `scripts/agk/kit_hashes.py`), the table `kit/hashes.json`, kit-only tests
(`tests/kit_dev/`) and a kit version bump (`kit/manifest.json`).

## Decision

1. **`kit/hashes.json` is a committed generated file and an exception to principle 5**, accepted by the ruling on
   Q-K3-50. It is acceptable where a lock file in the target was not because it is one file, in the kit only, never written
   into targets, and fully regenerable from git history. It holds, per released version, the SHA-256 of every verbatim file,
   marked-block body and template source an installer writes.
2. **The table cannot drift.** `scripts/agk/kit_hashes.py` regenerates every row from the first-parent history up to the merge
   base with the default branch, plus the working tree as the current version, and compares it with the committed file:
   hashes of every row, the commit list of every past row, and a row for `kit_version`. `kit_hashes.py --write` regenerates the
   file. A shallow clone fails the check, so the kit-dev tests need `fetch-depth: 0`, which `governance.yml` already sets and
   a test asserts.
3. **The bump rule** (SPEC-0008 rule 25, ruling Q-K3-55) is enforced by the same regeneration: a version other than 0.1.0 with
   a second hash for a path fails, that is, a change to an installed path without a `kit_version` bump. 0.1.0 is the one
   recorded exception (its second commit changed `Makefile`).
4. **`scripts/agk/upgrade.py` is built as SPEC-0008 specifies**: standard library only, no `git`, no network, `--dry-run`,
   exit 0 / 1 / 2 / 3; a locally edited file stops the whole run and lists every edited path; only the `version = "..."` line of
   `agk.toml` is rewritten, as the last write; templates and new `agk.toml` keys are printed, not merged; the target's
   protected classes and an ADR skeleton are printed, and no ADR is written. Neither script nor table is installed.
5. **An install stamped only in `pyproject.toml [tool.agk]` is refused** (kits 0.1.0 and 0.2.0 wrote no `agk.toml`; SPEC-0008
   rule 5). Criterion c names the 0.1.0 sandbox, so it cannot be met until the maintainers rule on Q-K3-71
   (`docs/runs/proposed-spec-amendments-12.md`). Every kit from 0.3.0 upgrades with no conflict in the tests.
6. **Kit version 0.9.0** (the next minor, one bump for this item). No installed file changes in this item.
7. **Deviations** from the Approved text are in `docs/runs/proposed-spec-amendments-12.md`, not applied.

## Consequences

- Every kit version change needs `python3 scripts/agk/kit_hashes.py --write` in the same pull request; the kit-dev test says so.
- The row of the current version names no commits until the next bump fills them in from history.
- The repository's git history is part of the kit's tests; a squash-merge workflow keeps one snapshot per version.
- The sandbox proof (`docs/runs/upgrade-live-proof.md`) is the maintainers' step.

## Residual

- 2026-10-16: kits 0.1.0 and 0.2.0 targets cannot be upgraded until Q-K3-71 is ruled (due 2026-11-15).
- 2026-10-16: `kit/hashes.json` is about 170 KB and grows by one row per release; a compact form is a later option
  (due 2026-12-31).
