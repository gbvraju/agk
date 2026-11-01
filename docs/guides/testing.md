# Testing: which tests guard which code

A one-line change should not have to run every test of the project, and it should never run too few. The optional
`[testing]` table of `agk.toml` says, by rule, which tests guard which code, and the test plan shows, before anything runs,
the regression tests that a change selects and the rule that chose each. The rules belong to the project, not to the agent:
`agk.toml` is a protected path, so a change of a rule comes with an ADR in the same pull request, and an agent cannot loosen
the rules to pass a gate.

The pre-push gate (`prepush.py`) runs the selection before a push, as described [below](#the-pre-push-gate). Proof also
runs the selected tests on the head, only with `proof_regression = true` in the `[testing]` table, off by default. By default
governance still runs every project test on every ready push; with `pr_tests = "selected"` a pull request runs only the selected
tests, while the default branch and every release pull request run them all (see the project CI guide).

## The table

```toml
[testing]
profile = "balanced"
always_full = ["app/auth/**", "migrations/**"]
map = [
  { code = "app/billing/**", tests = ["tests/billing/**"] },
  { code = "app/shop/*.py", tests = ["tests/shop/test_*.py", "tests/test_smoke.py"] },
]
budget_seconds = 300
```

- `profile`: how cautious the selection is.
  - `fast`: a changed file that no entry covers is only listed.
  - `balanced` (the default): a changed file that no entry covers selects the full suite. When unsure, run more.
  - `thorough`: every change selects the full suite.
- `always_full`: path globs. A changed file that matches one selects the full suite, whatever the profile. Use it for the code
  that every test depends on, such as authentication or the database schema.
- `map`: a list of entries. Each names a `code` glob and the `tests` globs of the tests that guard that code.
- `budget_seconds`: the target time of the full project suite, 300 seconds if unset. The metrics read it later.
- `excluded`: a list of `"<tag>: <reason>"` texts, the tests that the project's own command leaves out (brief #425, ADR-0230).
  Nothing in the selection interprets them; proof lists them in its manifest.
- `proof_regression`: a boolean, false by default; with true and a `[proof]` table, proof also runs the selection on the head
  (brief #442, ADR-0238, off until a person approves the spec change).
- `pr_tests`: `full` (the default) or `selected`. With `selected`, the CI step `Project tests` of a pull request runs only the
  selection, and a push and a release pull request run the full suite (brief #453, ADR-0242; `docs/guides/project-ci.md`,
  "Selected tests on pull requests"). Any other value is refused with `setting: pr_tests`.

Every key is optional; an empty `[testing]` table takes the defaults. A bad entry is refused, and the message names the setting
(for example `setting: testing.map[2].tests`), never its value.

A glob is a path from the top of the repository. `*` and `?` stay inside one folder, `**` crosses folders, and a glob that ends
in `/` means everything below that folder. A glob uses `/` between folders, never `\`, and may not start with `/` or hold a `..` part.

A new project's first values come from its stack ADR: the pull request that accepts the stack copies the `[testing]` profile
and the `always_full` paths that the chosen option's `test selection` practice names into this table, by a second ordinary
commit (`/agk:stack`, ADR-0228); after the second commit, `stack-check` prints whether the copy matches, in one information
line that names the setting and never fails it (`engines.py stack-check`, ADR-0241).

## What a change selects

For a change, the selection is worked out from git and files only, with no network:

- **Selected tests.** For each changed file, every entry whose `code` glob matches it selects the test files of the head that its
  `tests` globs match. Only test files count: files under `test_dirs` whose names match `test_patterns`, as for proof. Each
  selected file is shown with the changed file and the entry that chose it.
- **Full suite.** The selection is the full suite, with its reason, when a changed file matches `always_full`, when the profile
  is `thorough`, or, under `balanced`, when a changed file is unmapped.
- **Unmapped files.** A changed file that no entry covers, or whose entries select no existing test file (a typo in `tests`,
  a renamed folder), is unmapped, and it is always listed. Only the change's own test files and documentation are never
  unmapped; a helper such as `tests/conftest.py` is. A change is never silently given fewer tests than it needs.
- **Documentation.** A change of only `*.md` files and files under `docs/` selects nothing, under every profile, unless one of
  them matches `always_full`. Such a file is never unmapped.
- **No table.** Without a `[testing]` table the selection is the full suite, which is what governance runs today.

## The plan

```
python3 scripts/agk/test_plan.py [--base REF] [--head REF] [--json] [ROOT]
```

After the tests that proof runs, the plan prints a `regression` section, here for a change under the `fast` profile:

```
regression: 2 test files selected
  file: tests/billing/test_pay.py (app/billing/pay.py matches code app/billing/**, tests tests/billing/**)
  file: tests/test_smoke.py (app/shop/cart.py matches code app/shop/*.py, tests tests/shop/test_*.py, tests/test_smoke.py)
unmapped (no [testing] map entry covers it): app/other.py
```

or `regression: full (<reason>)`, for example `regression: full (always_full app/auth/** matches app/auth/login.py)`,
`regression: full (profile balanced: 1 unmapped file)` or `regression: full (no [testing] table)`, followed by the unmapped
files. With `--json` the same section is the `regression` object: `table`, `profile`, `full`, `reason`, `selected` (each with
`file`, `changed`, `code` and `tests`) and `unmapped`.

## The pre-push gate

```
python3 scripts/agk/prepush.py [--body FILE] [--base REF] [--quick] [--no-lock] [--record FILE]
```

With a `[testing]` table, the `tests` step of the pre-push gate first runs the pull request's own test files, as proof plans
them, and then the regression set of the change:

- **Full.** When the selection is full, `project_tests` runs once, in the top folder.
- **Selected files.** Otherwise each selected file runs through the command of the `[proof]` area it lies in, with `{files}`
  filled in as proof fills it, in the area's folder: one run per area.
- **No area.** A selected file that lies in no `[proof]` area is listed as `not run (in no [proof] area)`, never dropped, and
  the run ends `prepush: passed; not run: tests`. Without a `[proof]` table no area can take single files, so `project_tests`
  runs once instead.
- **Nothing selected.** A change that selects nothing says so, for example
  `regression: nothing selected (only documentation changed)`; an unmapped file is listed as in the plan.

Each run prints one line with the rule that chose it:

```
prepush: tests kit ok (0.4s): the pull request's own test files (the proof plan)
prepush: tests kit ok (2.1s): app/billing/pay.py matches code app/billing/**, tests tests/billing/**
prepush: tests full FAIL (41.0s): profile balanced: 1 unmapped file
```

The gate stops at the first run that fails, with its output, as before. Each run keeps proof's time limit (`proof_timeout`)
and is listed in the `--record` file with its `set` (`proof` or `regression`) and its `reason`.

**The heavy-step lock.** Two gates that run the tests at once on one machine slow each other down and can collide. The `tests`
step holds the machine's heavy-step lock (`lock.py`, name `heavy`) for as long as it runs, and prints lock.py's own lines while
it waits, `lock heavy: waiting; held by <session> ...` and `lock heavy: taken`. The lock is released when the step ends, also
when a test fails. A gate started under the lock already, as session rule 31 runs it
(`python3 scripts/agk/lock.py run --name heavy --session ID -- python3 scripts/agk/prepush.py`), does not take it again and
says `lock heavy: held by this run's caller (lock.py run); not taken again`. `--no-lock` leaves the lock out, for CI, where a
runner runs one job.

`--quick` still skips every test and takes no lock. Without a `[testing]` table the `tests` step runs exactly as before: proof's
plan alone, with no regression set and no lock.

## The flake ledger

A flaky test passes and fails on the same code. Retrying it until it passes, or skipping it quietly, hides it: nobody owns it
and nobody fixes it. The kit records each one in `docs/runs/flakes.md`, which init, adopt and upgrade install from the kit's
template when the file is absent and never overwrite. The file holds one table:

```
| test | owner | strikes | status | expires | issue |
| --- | --- | --- | --- | --- | --- |
```

- `test`: the test's id, as the test runner names it; one row per test.
- `owner`: one role or session id (`conductor`, a builder's session id), who looks after the entry.
- `strikes`: a whole number, how many flaky failures have been seen.
- `status`: `watch`, the test still runs, or `quarantined`, the test is set aside until its expiry.
- `expires`: the date the quarantine ends, `YYYY-MM-DD`. A quarantine always names its expiry; a `watch` row leaves it empty.
- `issue`: the issue that fixes the flake, `#n` or a link, empty until there is one.

**To add a strike**, when a test fails and then passes on the same code: find its row and add one to `strikes`, or, for a test
not yet in the ledger, add a row with `strikes` 1, status `watch`, an owner and empty `expires` and `issue`. The change goes in
a pull request of its own, never into an unrelated one: session rule 34 keeps a builder's own pull request unchanged when it
finds a flake, and a fix of the test belongs in its own pull request too.

**To quarantine** a test that blocks work: set its status to `quarantined` and its `expires` to the date the quarantine ends,
and name the issue that fixes it. A quarantine without an expiry is malformed. When the date passes, the entry is listed
`expired`, and its owner fixes the test, ends the quarantine or sets a new date in a pull request that says why.

```
python3 scripts/agk/flakes.py [--today YYYY-MM-DD] [--json]
```

`flakes.py` reads the ledger and lists, in the order of the file:

```
expired: line 9: tests/test_upload.py::test_retries (owner conductor; quarantined until <date>)
brief due: line 10: tests/test_list.py::test_order (owner builder-x1; 2 strikes, no issue)
malformed: line 11: strikes is not a whole number
flakes: 3 listed (1 expired, 1 brief due, 1 malformed) in docs/runs/flakes.md
```

- `expired`: a quarantined entry whose `expires` date is before today (today is `--today`, else the UTC date).
- `brief due`: an entry with two strikes or more and no issue. Its owner files a bug brief (session rule 34) and writes its
  number in `issue`.
- `malformed`: a row that is not an entry, with its line number and the column at fault, never the value; a test listed twice;
  a file without the ledger table, or with a second one; and a row below the table, after a blank line or prose
  (`a row outside the ledger table`), so a row is never skipped. Rows inside a fenced block, such as the template's invented
  example, are not read.

It exits 0 when nothing is listed, also when there is no ledger (`flakes: no ledger at docs/runs/flakes.md; nothing due`), and
1 otherwise. `--json` prints the same lists as an object: `ledger`, `present`, `today`, `entries`, `expired`, `brief_due`
and `malformed`. `flakes.py` is not a governance step and blocks nothing; adding it to a project's checks is the project's
choice.

## Mutation testing in the weekly audit

Coverage says which lines ran; it does not say whether a test would notice a wrong line. A mutation-testing tool injects
small faults into the code and counts how many of them the tests catch. The optional `mutation` setting of `agk.toml`,
empty (off) by default, is a shell command of the project's own; the kit ships, chooses and installs none. When it is set,
the weekly drift audit runs it once a week beside `unused_code` and `coverage`, with `AGK_CHANGED_FILES` naming a file
that lists, one path per line, the code files changed on the default branch in the last 7 days (not documentation, not
test files; at most 20, the first by name, so a run can be repeated). The command prints the score, the share of injected
faults killed, as a number on its last line, with or without `%`. An invented example, where the script is the project's
own:

```toml
mutation = "sh scripts/mutation-score.sh \"$AGK_CHANGED_FILES\""
```

The audit lists it under D9 as `mutation | killed <n>% of injected faults in <k> files`, with the change since the
previous audit, as it does for coverage. A command that fails, runs longer than `proof_timeout` or prints no number reads
`unknown`; with no changed code file the command is not run, and the line says so. The line is listed, never blocking: a
low score is a question for the next brief, not a failure.

The decisions are ADR-0220 (brief #373), ADR-0227 (brief #417), ADR-0234 (brief #435) and ADR-0240 (brief #449).
