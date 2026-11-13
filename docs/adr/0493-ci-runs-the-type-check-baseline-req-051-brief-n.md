# ADR-0493: CI runs the type check baseline

- Status: Proposed
- Date: 2026-11-13
- Deciders: maintainers
- Related: ADR-0307, ADR-0328, ADR-0494, issue #986, brief #1158, plan #661
- Requirements: REQ-051

## Context

ADR-0307 (brief #633) keeps `config/mypy-baseline.txt`; `tests/kit/test_scanner_hygiene.py` runs the pinned mypy on
`scripts/agk` and fails when a file has more or fewer errors of a code than its line. CI installs only the tools of
`config/ci-tools.txt` (ADR-0328), which had no mypy, so the test skipped there and added errors went unseen (issue
#986). ADR-0494 (brief #1157, part 1) fixed three files; on 2026-11-13, with mypy 2.3.1, `prepush.py`,
`product_report.py` and `route.py` still had 3 errors over their lines (brief #1158's `Measured:` line).

## Decision

1. `config/ci-tools.txt` pins `mypy==2.3.1`, in name order: the version the baseline's mypy line pins. The governance
   workflow's `Install tooling` step already installs that file, so the workflow does not change. A test checks that
   the pin and the baseline's mypy line name the same version, so the baseline test never skips in CI.
2. Part 2 fixes the added errors type-only, as ADR-0494 decision 1 says: `prepush.py` returns early when `root` is
   `None` (then `tools` already is); `route.py` tests `newest is None` beside `reason is None` (the reason is `None`
   whenever `newest` is); `product_report.py` tests `isinstance(..., list)`, the body of its own `is_list`, at the
   `briefs` loop and in `verdict_count`, which mypy narrows on (the renderer may import nothing more, so no
   `typing.TypeGuard`). No `# type: ignore`, no line raised.
3. The baseline lowers where the files got cleaner: `product_report.py` `index` 2 to 1 and `union-attr` 2 to 1, and
   its `misc` line, now 0, leaves.

Protected path classes changed: `scripts/agk/` (`prepush.py`, `product_report.py`, `route.py`), `config/`
(`config/ci-tools.txt`, `config/mypy-baseline.txt`).

## Consequences

The baseline test passes under mypy 2.3.1 and runs on every governance run (a few seconds); an added type error now
fails CI. A mypy update changes the pin file and the baseline's mypy line in the same pull request. A project's CI
installs the same tool list. If the pin cannot be installed the workflow's per-tool check, which names pytest, ruff
and bandit only, does not stop the run, and the test skips (verify: a workflow change is a person's).

## Residual

- 2026-11-13: closes #986 with ADR-0494.
