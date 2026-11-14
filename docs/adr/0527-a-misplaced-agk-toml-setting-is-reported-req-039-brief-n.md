# ADR-0527: A misplaced agk.toml setting is reported, never silently ignored

- Status: Accepted
- Date: 2026-11-14
- Deciders: maintainers
- Related: ADR-0190, ADR-0298, ADR-0409, ADR-0525, brief #1245, plan #661
- Requirements: REQ-039

## Context

A rehearsal of local autopilot on kit 0.64.2 (invented data) uncommented `auto_start`, `launch_adapter` and
`min_free_memory_mb` under the commented `# [flow]` line of the installed `agk.toml` template without uncommenting that line.
TOML put the keys in whatever came before them, `launch.launch_settings` read `(False, None)` and the conductor would start no
builder; neither governance nor `agk doctor` said anything. Each reader of a table reads only its own table, so a key outside
it is invisible to all of them.

## Decision

1. `scripts/agk/config.py` lists once, in `TABLE_KEYS`, the keys the kit reads from each of the tables `[flow]`, `[testing]`,
   `[capacity]`, `[plan]`, `[design]` and `[delivery]`, and `misplaced_settings(source)` returns, for an agk.toml read as TOML,
   each such key found at the top level or as a direct key of a table that does not read it, with the tables it belongs to
   (a key two tables read, such as `max_builders` of `[flow]` and `[capacity]`, is at home in either). A top-level setting of
   the kit (`DEFAULT_CONFIG`) is never one, and a key no table lists is left to the table's own refusal. A new table setting
   is covered by adding it to the list; tests hold the `[testing]` list equal to `impact.KEYS` and the `[capacity]` list to
   `config.py`'s own validator, and the repository's own agk.toml reads clean.
2. `scripts/agk/doctor.py` gains the check `misplaced-settings` (severity `warn`, as `engines-keys`, the other check of keys
   in the wrong place): `ok` with none, otherwise one `fail` line naming each key, where it is (`at the top level` or
   `in [<table>]`) and the table it belongs to, never its value.
3. `kit/templates/agk.toml` keeps the flow keys commented under a commented `# [flow]` line, and the comment block says in one
   line, right above it, that the keys belong in the `[flow]` table and that `agk doctor` reports them otherwise. The brief's
   other choice, a real empty `[flow]` table at the end of the file, was not taken: a top-level line appended to the end of
   an installed agk.toml (as `experimental_reviewer = true` is in `tests/kit_dev/test_experimental_reviewer.py`) would then
   land in `[flow]` and be ignored, the same failure in another place (Q-1245-1).

## Consequences

A key written in the wrong table, or uncommented without its table line, is named by `agk doctor` with both table names, so
local autopilot is never left off by a misplaced line without a warning. The check reads only agk.toml and changes no other
check or exit path; the doctor's `ok` count grows by one. Protected path classes changed: `scripts/agk/` (`config.py`,
`doctor.py`), `kit/` (the comment of `templates/agk.toml`), `tests/kit/` (`test_doctor_misplaced_settings.py`, new;
`test_doctor.py` and `test_delivery_declaration.py`, their counts) and `docs/adr/` (this file).

## Residual

- 2026-11-14: the list was gathered by reading the readers of each table in `scripts/agk/`; a key a future reader adds and
  this list misses is not reported until it is added.
