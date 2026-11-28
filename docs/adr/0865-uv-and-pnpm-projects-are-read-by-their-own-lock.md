# ADR-0865: uv and pnpm projects are read by their own lock

- Status: Proposed
- Date: 2026-11-28
- Deciders: maintainers (the owner's yes on brief #2075, 2026-11-27T19:44:01Z)
- Related: ADR-0834, ADR-0867, ADR-0672, ADR-0742, ADR-0748, ADR-0768, ADR-0800, SPEC-0076, SPEC-0072, REQ-083,
  brief #2075, plan #661
- Requirements: REQ-083

Protected classes: `scripts/agk/`, `tests/kit/`, `agk.toml`

## Context

SPEC-0076 (Approved, ADR-0834) rule 15 build (h) asks for the `uv` and `pnpm` readers, then Maven and Gradle (rule 11),
each feeding `licences.py` and the bill. `pins.STACKS` holds one row per runtime, so on main at 9b6ab96a a
`pyproject.toml` with only `uv.lock`, or a `package.json` with only `pnpm-lock.yaml`, fails `pins` with `the lock file
is missing (component class: lock file)`. This ADR is build (h1), uv and pnpm, by the brief's `Q-PH-1`; Maven and
Gradle are builds (h2) and (h3).

## Decision

1. **The lock picks the reader.** `pins.LOCKS` lists per runtime key its lock files in order with their readers:
   `python`: `requirements.lock` (`requirements`), `uv.lock` (`uv`); `node`: `package-lock.json` (`npm`),
   `pnpm-lock.yaml` (`pnpm`). `pins.runtimes` reads the file list for every runtime and puts on each `Runtime` the row
   of the first lock present in its folder; with none, the `STACKS` row, so a missing lock still fails naming
   `lock file`. Two locks of one runtime in one folder read the first, today's lock. A later reader needs the
   runtime's own build file (`pyproject.toml` for uv). `STACKS` and `pins.chosen` are unchanged. No setting is added.
2. **The uv reader.** `pyproject.toml` alone: `[project] dependencies`, `optional-dependencies`, each string of
   `[dependency-groups]` (an `include-group` table is skipped) and `[tool.uv] dev-dependencies`, each exact (`==`) or
   `UNPINNED`. The lock: `uv.lock` by `tomllib`, each `[[package]]`'s name and version; not TOML or no `package` list
   is `the lock file is unreadable`.
3. **The pnpm reader.** `package.json` as npm's (a range, `workspace:` or `catalog:` spec is `UNPINNED`). The lock: a
   standard-library line reader of `lockfileVersion: '9.0'` (`(verify)`: the version pnpm 9 and 10 write): each key
   two spaces in under the top-level `packages:`, `<name>@<version>:`, quotes and a peer suffix from `(` removed, split
   at the last `@` after the first character. Another version, or no `packages:`, is unreadable.
4. **Licences, the bill and the parts step.** `licences.CLASSES` gains `uv` to `python` and `pnpm` to `node`; neither
   lock states a licence (`(verify)`), so each package takes the record part's licence or is `unknown`. The bill's purl
   follows the class, unchanged. `parts.py` reads the new rows through `pins`; its runtime key is found by the row's
   template folder, so any lock of a runtime finds its key.

## Consequences

A uv or pnpm project is checked for pins, licences, the bill and the parts list. Every existing project reads the same
lock as before. An adopted project's baseline counts per lock path, so an old `lock file is missing` count on
`requirements.lock` drops and a new finding on `uv.lock` ratchets. No workflow, ruleset, required check, `agk.mk`,
label or `governance_map.CHECKS` changes.

## Residual

Maven and Gradle (builds (h2) and (h3)); a warning on two locks of one runtime and a pnpm wording of `node_pack.INSTALL`
are later briefs on the owner's word. The pnpm lock version and the uv groups installed by default stay `(verify)`.
