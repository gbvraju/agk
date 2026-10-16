# ADR-0017: agk doctor: the build of SPEC-0006

- Status: Proposed
- Date: 2026-10-15
- Deciders: maintainers
- Related: ADR-0001, ADR-0003, ADR-0015, ADR-0016
- Requirements: REQ-002

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `kit/`

## Context

SPEC-0006 (Approved on 2026-10-15) defines `agk doctor` for K3 criterion b of ADR-0015: a read-only report of the
GitHub settings and local files that ADR-0001 decision 3, ADR-0003 and SPEC-0001 left to "`agk doctor` documents and
verifies" (REQ-002 AC1). Building it adds a vendored script and its tests (`scripts/agk/`, `tests/kit/`), a kit-only wiring
test (`tests/kit_dev/`) and manifest entries with a version bump (`kit/`).

## Decision

1. **`scripts/agk/doctor.py` is built as SPEC-0006 specifies**: standard library only; twenty checks, each with an
   id, a severity and a printed fix; `ok`, `fail` and `cannot-check` as the only statuses, `cannot-check` never `ok`;
   a text report and `--json` rendered from one structure; exit 0, 1, 4, 2 and 3 as in rule 12. It runs `gh api` with
   GET on four paths and `git` only to read; it holds no credential and is not run by `make governance` or by any
   workflow.
2. **The ruleset elements of ADR-0001 decision 3 are a minimum** (ruling Q-K3-12): stricter is `ok`; merge methods fail only
   when `merge` is allowed. Several rulesets that target the default branch are read together, and only active ones protect: `ruleset-enforcement` fails when no candidate is active, `ruleset-bypass` and every element check read the active candidates only (a rule on a disabled ruleset does not count; a bypass actor on a disabled ruleset is not a bypass), and with no active candidate those checks fail. A ruleset targets the default branch when its `include` has `~DEFAULT_BRANCH`, `~ALL` or the default branch's ref and its `exclude` has none of them. When no ruleset targets
   the default branch, the other ruleset checks are `cannot-check` with the reason `no-ruleset`, so that only
   `ruleset-missing` or `ruleset-target` fails.
3. **It is vendored**: init and adopt install `scripts/agk/doctor.py`, `tests/kit/test_doctor.py` and the files of
   `tests/kit/fixtures/doctor/` (listed in `kit/manifest.json` one by one, see ADR-0016's residual). The fixtures are a base
   case `ok` and per-case overlays, not a full tree per case, to keep the file count low.
4. **A fresh install is compared with this kit in a kit-only test** (`tests/kit_dev/test_doctor_wiring.py`): no vendored
   difference, the placeholder team reported (SPEC-0001's residual), an edited, deleted or weakened file reported.
5. **Kit version 0.8.0** (the next minor, one bump for this item).
6. **Deviations** from the Approved text are in `docs/runs/proposed-spec-amendments-11.md`, not applied.

## Consequences

- A repository without the plugin runs `python3 scripts/agk/doctor.py`; without `--kit-root` the three kit checks are
  `cannot-check` (`no-kit-root`), so such a run never exits 0.
- The live proof on the sandbox (`docs/runs/doctor-live-proof.md`) is the maintainers' step; criterion b stays open until it
  is recorded.
- `skills/doctor/SKILL.md` and `/agk:doctor` belong to the plugin item (SPEC-0005) and are not built here.

## Residual

- 2026-10-15: whether `allowed_merge_methods` is omitted when all methods are allowed is `(verify)`; the script treats an
  omitted key as all methods allowed, which fails `ruleset-pull-request` (due 2026-11-30).
- 2026-10-15: a non-admin may see an empty ruleset list; the script reports `cannot-check` (`no-admin`) only when the
  repository read says `permissions.admin` is false (due 2026-11-30).
