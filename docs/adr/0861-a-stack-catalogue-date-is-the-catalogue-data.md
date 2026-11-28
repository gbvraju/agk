# ADR-0861: A stack catalogue's source and reviewed dates are its data, not a literal date

- Status: Proposed
- Date: 2026-11-28
- Deciders: maintainers
- Related: ADR-0112, ADR-0804, ADR-0858, ADR-0859, SPEC-0076, SPEC-0046, REQ-083, brief #2082, brief #2069
- Requirements: REQ-083

Protected classes: `tests/kit_dev/`

## Context

The default branch went red on 27b2eec1 (governance job 140811733786, `1 failed, 19365 passed`):
`tests/kit_dev/test_no_literal_dates.py::test_no_installed_file_holds_a_literal_date` (ADR-0112) lists 61 lines of
`config/parts/node.toml`, the catalogue #2080 shipped (brief #2069, ADR-0859). SPEC-0076 rule 5 orders every stack
catalogue row to carry a `source` with its access date and a `reviewed` date, so the rows cannot drop their dates.
ADR-0112's reason for the test is a date that ages into a failure on the day it names. No check compares a catalogue
date with the day it runs: `check_parts_catalogue.py` checks only that each is a real `YYYY-MM-DD` date, and an old
`reviewed` date is not stale by any rule (ADR-0859, `Q-PB-5`). ADR-0804 met the same case for a domain pack's `as_of`
line.

## Decision

1. `test_no_literal_dates.py` accepts, beside a pack's `as_of` line (ADR-0804), a whole line
   `source = "<http or https URL> (accessed YYYY-MM-DD)"` or `reviewed = "YYYY-MM-DD"` of a stack catalogue: a
   `.toml` file directly in `config/parts/` other than `needs.toml`, which holds no dated row. The source form is the one
   `check_parts_catalogue.SOURCE` checks.
2. Any other date stays a failure: a date in another key of a catalogue (`when`, `trade_offs`), a line with anything
   after the value, a date in `needs.toml`, and a date in any other installed file. A test holds each case.
3. A test holds that the shipped catalogue has dated lines and that every one of them is a source or reviewed line, so
   the exemption is used and covers no more than the data.

## Consequences

The default branch turns green with no change to the catalogue or to `check_parts_catalogue.py`. The `python-pyproject`
catalogue (build (b2)) and every later stack catalogue are covered by the same rule without a further change. The test
of ADR-0112 is narrowed by two line forms in one folder and is otherwise unchanged (principle 11).

## Residual

A rule that makes a `reviewed` date stale by the calendar would turn this exemption into a date that can age into a
failure; such a rule must then change this test by its own ADR.
