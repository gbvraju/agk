# ADR-0399: In a sidecar the marker readers read the private test map

- Status: Proposed
- Date: 2026-11-09
- Deciders: maintainers
- Related: ADR-0267, SPEC-0041, brief #900
- Requirements: REQ-048

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

SPEC-0041 rule 16 keeps the link between a requirement and its tests in `test-map.toml` in the sidecar, so that no marker
is written into the customer's tests, and build (b) amended principle 10 to say so. The readers did not yet follow:
`common.find_markers` and `common.find_ac_markers` scanned test files whatever the root, so a sidecar could never show a
requirement as proven. Rule 2 also says the five file checks run unchanged with a sidecar as their working directory, and
no test held that. ADR-0267 decision 10 names `common.py` among the files the builds change and asks each build for its
own ADR naming its classes; this is build (e).

## Decision

1. `common.read_test_map` reads `test-map.toml` at the root of a sidecar, which is a root where `common.personal_table`
   finds a `[personal]` table. A root without that table never opens the file.
2. In a sidecar `find_markers` and `find_ac_markers` return what the map says, with the same return shape, and scan no test
   file; the directories and patterns they are given do not apply. A sidecar with no map file has no markers and no error.
3. A map entry is `"REQ-nnn ACm" = ["path::name", ...]`, with at least one test id. The file column is the part of the id
   before its first `::`, and the line column is 0, since a map entry has no line in a test file.
4. Anything else, including a repeated key and text that is not UTF-8, is refused naming `test-map.toml` and SPEC-0041 rule
   16, and never a key or a value (principle 8).
5. No check changes: `check_requirements.py`, `check_specs.py`, `check_adrs.py`, `check_numbers.py` and `check_brief.py`
   pass on a fresh sidecar and on one holding a requirement, a spec and an ADR, and the tests hold that.

## Consequences

A requirement in a sidecar can be `done` on the strength of its map entry, and the callers of the two readers keep their
shape. A repository without the table reads its markers as before, and a `test-map.toml` in one means nothing. The test
ids are opaque here: nothing yet proves that a named test exists in the product or passes.

## Residual

The one command that runs the five checks together on a sidecar comes with a later build, as `scripts/agk/personal.py` is
held by another pull request. A mapped test file that does not exist in the product is not detected by this build. A
reader that shows `line` from a sidecar shows 0.
