# ADR-0234: a flake ledger gives each flaky test an owner and an expiry (REQ-016, brief 435)

- Status: Proposed
- Date: 2026-10-31
- Deciders: maintainers
- Related: ADR-0181, ADR-0220, ADR-0227
- Requirements: REQ-016

Protected classes: `scripts/agk/`, `kit/`, `tests/kit/`, `tests/kit_dev/`

## Context

Brief #435 (from #289 principle 6 and #286's found-bug field note): a flaky list test was fixed inside an unrelated pull
request, because the kit has no place to record a flake. A test that is retried until it passes, or quarantined with no
record, has no owner and no end, and is forgotten. The script, the template, the manifest and the tests are protected path
classes, so this ADR names them. The tests were written first (`tests/kit/test_flakes.py`: a collection error at the first
checkpoint, no module `flakes`; 4 failed, 30 passed with the script alone, before the template, the manifest and the guide).

## Decision

1. **One ledger (answer 1).** `docs/runs/flakes.md` holds one Markdown table with the header
   `| test | owner | strikes | status | expires | issue |` and its separator line. Each row is one test: `test` is not empty
   and appears once; `owner` is one role or session id (letters, digits, `.`, `_`, `-`); `strikes` is a whole number;
   `status` is `watch` or `quarantined`; `expires` is a real `YYYY-MM-DD` date, required for a quarantine and optional for
   `watch`; `issue` is empty, `#n` or a link. The table ends at the first line that is not a row. Rows in a fenced block are
   not read. The file is installed from `kit/templates/flakes.md` by init, adopt and upgrade when it is absent and is never
   compared or overwritten (a create-only template, as the residuals register, ADR-0181; Q-435-1). The template's example
   row is invented and sits in a fenced block outside the ledger, so the installed ledger starts empty (Q-435-2).
2. **The command (answer 2).** `scripts/agk/flakes.py [--today YYYY-MM-DD] [--json]` reads the ledger at the top of the
   repository and lists, in the order of the file:
   - `expired: line <n>: <test> (owner <owner>; quarantined until <date>)`, for a quarantined entry whose `expires` is
     before today (an expiry of today is not yet past, Q-435-4);
   - `brief due: line <n>: <test> (owner <owner>; <k> strikes, no issue)`, for an entry with two strikes or more and an empty
     `issue`, whatever its status; an entry may be listed both ways;
   - `malformed: line <n>: <reason>`, for a row that is not an entry, naming the column at fault and never the value, a test
     listed twice (`test is listed already on line <m>`), a header without its separator line, a second ledger table, a row
     below the table outside a fence (`a row outside the ledger table`: a break in the table never hides a row), and a file
     without the table (line 1) (Q-435-3).

   It ends with `flakes: <k> listed (<e> expired, <b> brief due, <m> malformed) in docs/runs/flakes.md` or
   `flakes: nothing due (<k> entries) in docs/runs/flakes.md`; without a file, `flakes: no ledger at docs/runs/flakes.md;
   nothing due` (Q-435-5). `--json` prints `ledger`, `present`, `today`, `entries`, `expired`, `brief_due` and `malformed`.
   Today is `--today`, else the UTC date (`date -u`). Exit 0 when nothing is listed, 1 otherwise, 2 for a bad call, a bad
   `--today` (the message names the option) or a ledger that is not UTF-8 text. It reads one file, uses no network and
   changes nothing. It is not a governance step and blocks nothing; a project adds it to its checks if it wants to.
3. **The guide (answer 3).** `docs/guides/testing.md` gains `## The flake ledger`: the columns, how to add a strike, how to
   quarantine, that a quarantine always names its expiry, and what `flakes.py` prints. A strike is recorded in a pull request
   of its own, never in an unrelated one (session rule 34, Q-435-6).
4. **The kit.** `scripts/agk/flakes.py` is a verbatim file of `kit/manifest.json`; `docs/runs/flakes.md` is a template in
   both install modes and is create-only (`CREATE_ONLY` of `init.py`), so an uninstall leaves it as the project's file.
   Flow mode: one changelog fragment, `changelog.d/flake-ledger.md`; no version bump, and `kit/hashes.json` is not edited
   (Q-435-7).

## Consequences

- A flaky test has a row, an owner and a count; a quarantine has an end date, and a forgotten one is listed when it passes.
- A test that has failed twice without an issue is listed as a brief due, so its owner files the bug brief.
- Nothing blocks on the ledger: a project that wants a gate adds `flakes.py` to its own checks.
- A project upgraded to the next release gains an empty ledger, and an existing `docs/runs/flakes.md` is left alone.

## Residual

- Q-435-1 (2026-10-31): "installed from the template when absent" is read as a create-only template, as the residuals
  register; that needs `CREATE_ONLY` in `scripts/agk/init.py` and the uninstall test's list of left files
  (`tests/kit_dev/test_uninstall.py`), both outside the brief's `Touches`.
- Q-435-2 (2026-10-31): the template's invented example row is put in a fenced block above the ledger, so a new project's
  ledger holds no invented entry and `flakes.py` never reads one; the brief does not say where the row goes.
- Q-435-3 (2026-10-31): the brief does not define a malformed row; read narrowly as the column rules of decision 1, a test
  listed twice, a missing separator, a second table, a row after a break in the table (added on the conductor's fix list
  for head 5e4043d, finding 1) and a file without the table.
- Q-435-4 (2026-10-31): "past its expiry" is read as an `expires` date before today; on the day itself the quarantine
  still holds.
- Q-435-5 (2026-10-31): without a ledger nothing is listed, so the exit is 0 (answer 2), with one line that says so.
- Q-435-6 (2026-10-31): the brief does not say in which pull request a strike is recorded; session rule 34 keeps a
  builder's own pull request unchanged, so the guide says a pull request of its own.
- Q-435-7 (2026-10-31): the run asked to regenerate the manifest and hashes with the kit's scripts; `kit_hashes.py` checks
  the table as `ok` without `--write`, and session rule 14 says a build never edits `kit/hashes.json`, so it is unchanged.
- Q-435-8 (2026-10-31): a kit test requires every installed script to be named in `docs/guides/reference.md`, outside the
  brief's `Touches`; it gains a short `## Flake ledger` section that points to the testing guide.
