# ADR-0789: An adopted Node product makes its bill of materials without a pyproject.toml (REQ-061, brief 1907)

- Status: Accepted
- Date: 2026-11-24
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1907, amendment 232 (SPEC-0054 rules 2 and 3), ADR-0370, ADR-0676, ADR-0694, ADR-0672, ADR-0742,
  test plan 3 (AD-06, #1771), plan #661
- Requirements: REQ-061, REQ-078

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

`sbom.py:build` read `pyproject.toml` first and refused a commit without one, before it read `agk.toml` or the lock.
Amendment 206 (ADR-0676) lists a `node` product's packages from its committed `package-lock.json`, and the `bom` gate
runs wherever a chosen stack has its lock, so in an adopted Node product with a committed lock and no Python build file
every run of the gates was red at `bom` (`pyproject.toml cannot be read at the commit (rule 2)`), while the same commit
with a three-line `pyproject.toml` added gave a true bill. Every Node fixture of the tests carried a `pyproject.toml`,
which hid it. The owner's word (2026-11-24 IST, the steward chat, quoted as data): "Yes, file the four test-run
briefs".

## Decision

1. **The build file is read where it is.** `build` reads `agk.toml` first (its `version` and `[kit] layout`, so a bad
   layout names its setting before any build file), then the stack chosen at the commit (`chosen_at`, the `pins.pick`
   reading that `lock_components` used, now shared by both). A `pyproject.toml` present at the commit is read as
   today: its `[project] name` names the product and its requirements are the `python` components; one that cannot be
   parsed or has no `[project] name` is refused as today (`Q-SB-3`). Absent, it is accepted only when the repository
   declares a `[delivery] work_type` and the chosen stack is `node`; the bill then has no `python` component from it.
   Absent anywhere else (no work type, a `python` stack, no stack or a record that chooses none), it is refused with
   today's line.
2. **The product's name** (`Q-SB-2`). In decision 1's one case, the `name` of `package.json` at the commit, a
   non-empty string kept as written (a scoped `@scope/name` too). Absent at the commit: `package.json cannot be read at
   the commit (rule 2)`; not UTF-8 JSON (a byte order mark included, `Q-SB-6`), not an object, or a `name` absent, not
   a string, empty or only whitespace: `package.json cannot be parsed at the commit (rule 2)`. No fall-back to the
   lock's name or the folder. `metadata.component.version` stays the `version` of `agk.toml` (`Q-SB-5`).
3. **What does not change.** The fields, order, sorting, `serialNumber`, timestamp and every class's reader;
   `gates/bom.py`, `run_gates.py`, `licences.py` and `pins.py`; `check`, `ok bom` and the one failure class `bill of
   materials`. The kit's own bill, and every bill a commit with a `pyproject.toml` gives today, are byte-identical.
4. **The class stays closed.** `sbom.NAMERS` maps each build file of `pins.STACKS` to the reader of the product's
   name from it (`pyproject.toml`, `package.json`); a test asserts every `STACKS` row has one, so a later stack joins
   by one row in its own brief and cannot fall back to `pyproject.toml` unseen.
5. **The spec.** SPEC-0054 changes only through amendment 232 (`docs/runs/proposed-spec-amendments-232.md`), applied
   on the spec approver's answer, never by this build (`Q-SB-1`).
6. **Path classes changed:** `scripts/agk/` (`sbom.py`) and `tests/kit/` (`test_product_deps.py`, `test_sbom.py`).

## Consequences

An adopted Node product's `bom` step turns from red on every run to `ok bom`, listing its lock's packages with their
licences, in hosted governance, `make governance` and `prepush.py`. A Node product that keeps a `pyproject.toml` for
tooling lists its Python requirements beside the lock's packages as before. The kit's bill is unchanged.

## Residual

- `Q-SB-4`: `personal.py floor` runs the gates on a `git archive` extract, which is no repository, so `bom` cannot
  resolve `HEAD` there for any stack; its own brief.
- `Q-SB-3`: a Node product's `pyproject.toml` holding only `[tool.*]` tables is still refused; a later brief if a run
  shows it.
