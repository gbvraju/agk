# ADR-0876: A reader of the parts record takes its path from the one writer

- Status: Proposed
- Date: 2026-11-28
- Deciders: maintainers
- Related: ADR-0862, ADR-0867, ADR-0860, SPEC-0076, SPEC-0046, REQ-083, brief #2102, brief #2072, #2092
- Requirements: REQ-083

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

After #2092 (brief #2072, SPEC-0076 build (e)) merged, the default branch went red at 1067308c: governance's full run
46120055692 printed `1 failed, 19612 passed`. The failing test,
`tests/kit/test_parts_record.py::test_only_parts_record_writes_the_record_and_it_imports_no_network_module`, keeps
SPEC-0076 rule 6 ("one writer of `docs/parts.md`") by listing the kit scripts that spell the record's path as a
literal, and expects only `parts_record.py`. `engines.py` only reads the record (`record_parts`), but it defined its
own `PARTS_RECORD = "docs/parts.md"`. The other reader, `gates/parts.py` (build (d), ADR-0867), already imports
`RECORD` from `parts_record`.

## Decision

1. `engines.py` takes the record's path with `from parts_record import RECORD as PARTS_RECORD`, as `gates/parts.py`
   does, and drops its own literal. What it reads, writes and prints is unchanged.
2. The test of rule 6 is not changed (principle 11). A new test,
   `test_a_reader_of_the_record_takes_its_path_from_the_one_writer`, holds `engines.PARTS_RECORD is
   parts_record.RECORD`.

## Consequences

The default branch turns green again with this one fix. A future reader of the record follows the same form, or
the rule 6 test names it.

## Residual

None.
