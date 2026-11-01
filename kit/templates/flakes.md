# Flake ledger

A flaky test is one that passes and fails on the same code. It is recorded here, with an owner, and is never retried away or
skipped without a row. `python3 scripts/agk/flakes.py` lists each quarantine past its expiry (`expired`), each test with two
strikes or more and no issue (`brief due`) and each malformed row; `docs/guides/testing.md` says how to add a strike and how
to quarantine.

One row per test, in the table under `## Ledger`:

- `test`: the test's id, as the test runner names it.
- `owner`: one role or session id, who looks after the entry.
- `strikes`: a whole number, one more for each flaky failure seen.
- `status`: `watch` (it still runs) or `quarantined` (it is set aside until its expiry).
- `expires`: the date a quarantine ends, `YYYY-MM-DD`; a quarantine always names one. Empty for `watch`.
- `issue`: the issue that fixes it, `#n` or a link; empty until there is one.

An example row, invented, outside the ledger (rows in a fenced block are not read):

```text
| test | owner | strikes | status | expires | issue |
| --- | --- | --- | --- | --- | --- |
| tests/test_example.py::test_upload_retries | builder-x1 | 1 | watch |  |  |
```

## Ledger

| test | owner | strikes | status | expires | issue |
| --- | --- | --- | --- | --- | --- |
