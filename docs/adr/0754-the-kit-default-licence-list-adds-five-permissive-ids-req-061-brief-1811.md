# ADR-0754: The kit's default allowed-licence list adds five permissive ids (REQ-061)

- Status: Accepted
- Date: 2026-11-23
- Deciders: maintainers
- Related: SPEC-0054 rule 4, ADR-0748, ADR-0676, ADR-0743, amendment 206, brief #1811, brief #1785, brief #1596, plan #661
- Requirements: REQ-061

Protected classes this pull request changes: `scripts/agk/` (`gates/licences.py`), `kit/` (`templates/licences.toml`),
`tests/kit/` (`test_product_deps.py`) and `tests/kit_dev/` (`test_engines_stack.py`).
`kit/hashes.json` is not edited by hand.

## Context

On main at 695061a5 (2026-11-23) the kit's default list, `DEFAULT` in `scripts/agk/gates/licences.py` and `allowed` of
`kit/templates/licences.toml`, held the six ids of `Q-1596-1`'s reading (amendment 206): `MIT`, `Apache-2.0`,
`BSD-2-Clause`, `BSD-3-Clause`, `ISC` and `PSF-2.0`. A project choosing SQLite (`blessing`) or a part under `Zlib`,
`BSL-1.0`, `0BSD` or `Unlicense` got the off-list note at `stack-check` (ADR-0748) and then failed the `licences`
gate until it wrote its own ADR. ADR-0748's `## Residual` left the wider default open as `Q-F2-1`; the owner answered
yes in the steward chat on 2026-11-23 (brief #1811, quoted there as data).

## Decision

1. `DEFAULT` and the template hold the same eleven ids: the six of `Q-1596-1` and `blessing`, `0BSD`, `Unlicense`,
   `Zlib` and `BSL-1.0`, in their SPDX case (checked at build against the SPDX licence list data, not fetched by any
   check). Each is permissive, with no copyleft. `BSL-1.0` is the Boost Software License 1.0, not `BUSL-1.1`.
2. `CC0-1.0` is not added (`Q-1811-1`, the brief's `Q-F9-1`, the conservative reading): a dedication whose clause 4(a)
   grants no patent licence (verify: the CC0 1.0 legal code). `(MIT OR CC0-1.0)` passes on `MIT` as before; a project
   that wants `CC0-1.0` adds it by its own ADR.
3. A project's own `config/licences.toml`, when it is a file, is read exactly as before, whatever it holds (the old six
   copied by `stack-files` included); nothing rewrites, merges or notes it (`Q-1811-2`). The wider default decides
   only before the foundation and for a project with no file.
4. This supersedes `Q-1596-1`'s reading (amendment 206 line 47) for the default list only. ADR-0748 and amendment 206
   are records and are not edited. No spec amendment: SPEC-0054's proposed rule 4 names the file, not its ids.
5. The guard is a test: `test_the_template_is_the_built_in_list` pins the eleven ids and the template's equality with
   `DEFAULT`; each added id, in its SPDX case and folded, passes the gate with no project list and prints no off-list
   note at `stack-check`; ids that stay off (`BUSL-1.1`, `zlib-acknowledgement`, `CC0-1.0`, `CC-BY-4.0`, `MPL-2.0`,
   `LGPL-2.1-only`, `BlueOak-1.0.0`) still fail. A later id is added by the same two lines and its test row.

## Consequences

A new project using SQLite or a `Zlib`, Boost, `0BSD` or `Unlicense` part passes the `licences` step with no project
ADR. No copyleft, source-available or patent-silent licence passes by default. A project that already has a
`config/licences.toml` gets the same result as before until it widens its own list. GitHub, local (`prepush.py`) and
personal modes run the same readers; no workflow, setting or required check changes.

## Residual

- 2026-11-23: `Q-1811-1`: `CC0-1.0` in the default stays with the owner.
- 2026-11-23: `Q-1811-3`: other permissive ids common in locks (`BlueOak-1.0.0`, `Python-2.0`) are not added here.
