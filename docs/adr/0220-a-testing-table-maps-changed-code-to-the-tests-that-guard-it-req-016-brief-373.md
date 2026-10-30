# ADR-0220: a [testing] table maps changed code to the tests that guard it, and the test plan shows the selection (REQ-016, brief 373)

- Status: Accepted
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0185, ADR-0172
- Requirements: REQ-016

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`

## Context

Brief #373 (priority 1, split from #289 parts 1 and 2): `test_plan.py` (ADR-0185) shows only the pull request's own test
files, and governance runs every project test on every ready push, so a one-line change runs either too little (proof) or
everything (governance). The selection of regression tests must belong to the kit: by rule, repeatable and protected, never
chosen by the agent. The new script, the test plan, the kit manifest and templates and the tests are protected path classes,
so this ADR names them. The tests were written first (`tests/kit/test_impact.py`: a collection error at the first
checkpoint of the pull request, as `impact.py` did not exist).

## Decision

1. **The table (answer 1).** `agk.toml` gains an optional `[testing]` table: `profile` (`fast`, `balanced` the default, or
   `thorough`), `always_full` (path globs), `map` (a list of `{ code = "<glob>", tests = ["<glob>", ...] }`) and
   `budget_seconds` (a whole number above 0, 300 by default, read later by the metrics). Any other key, a bad profile, a
   glob that is empty, absolute, holds a `\` or holds a `..` part, a map entry without both keys or with an empty `tests`, or a budget
   that is not a whole number above 0 is refused, naming the setting (`testing`, `testing.profile`, `testing.always_full`,
   `testing.map`, `testing.map[<n>]`, `testing.map[<n>].code`, `testing.map[<n>].tests`, `testing.budget_seconds`). The
   table is read from `agk.toml` of the root, as `[proof]` is (ADR-0172). `agk.toml` is a protected path, so changing a
   rule needs an ADR.
2. **The selection (answer 2).** `scripts/agk/impact.py` (git and files only, no network) gives, for base..head:
   - the selected test files: each test file of the head (under `test_dirs`, its name matching `test_patterns`, as proof
     reads them) that a `tests` glob matches, in an entry whose `code` glob matches a changed file, with the first such
     changed file (in path order) and its entry;
   - `full`, with its reason, when a changed file matches `always_full` (`always_full <glob> matches <file>`), else when
     the profile is `thorough` (`profile thorough`), else under `balanced` when a file is unmapped
     (`profile balanced: <n> unmapped file(s)`);
   - `unmapped`: the changed files that are not test files (`test_dirs` and `test_patterns`, as above), not `*.md` and
     not under `docs/`, that no `code` glob matches, or whose matching entries select no test file of the head (a typo
     in `tests`, a renamed folder). A change is never silently given fewer tests than it needs.
   A non-empty change of only `*.md` files and files under `docs/` selects nothing, under every profile, unless a changed
   file matches `always_full`, which then makes the selection full. An empty change is not read as documentation. A
   glob keeps `*` and `?` in one folder, `**` crosses folders and `dir/` is `dir/**`, as in the session plan.
3. **The plan (answer 3).** `test_plan.py` prints, after its existing lines, a `regression` section: `regression: full
   (<reason>)`, or `regression: <n> test file(s) selected` with one `  file: <test> (<changed> matches code <glob>, tests
   <globs>)` line each, or `regression: nothing selected` (with `(only documentation changed)` for a docs-only change);
   then one `unmapped (no [testing] map entry covers it): <path>` line per unmapped file. `--json` adds the object
   `regression` with `table`, `profile`, `full`, `reason`, `selected` and `unmapped`. Without the table it prints
   `regression: full (no [testing] table)`. A refused setting exits 2, as a refused `[proof]` setting does.
4. **Nothing runs it (answer 4).** Proof, prepush and CI are unchanged.
5. **Kit files.** `impact.py` is listed in the manifest's verbatim scripts; both `agk.toml` templates gain the table as a
   commented example; `docs/guides/testing.md` describes the table and the plan (answer 5).

## Consequences

- A project can state, in one protected table, which tests guard which code, and see the selection of each change before
  later briefs run it.
- A project without the table sees `regression: full (no [testing] table)`, which is what governance runs today.
- `impact.py` is a library of `test_plan.py`, not a command of its own, so the reference guide is unchanged.
- The tests step of `prepush.py` runs the test plan, so a malformed `[testing]` table makes that step fail, which refuses
  the bad setting before a push.

## Log

- 2026-10-30: verdict `fix list` on e258a97. Item 1: a changed file whose covering entries select no test file is
  unmapped, and a `\` in any glob is refused. Item 2: only a real test file (not any file under `test_dirs`, and not
  everything with `test_dirs = ["."]`) is left out of `unmapped` (Q-373-4). Item 3: an empty change is not docs-only.
  Q-373-1 answered: the conservative reading, `always_full` wins over the docs-only rule. Q-373-2 and Q-373-3 accepted
  as read.

## Residual

- Q-373-1 (2026-10-30): answered on e258a97 (see the log): `always_full` wins over the docs-only rule.
- Q-373-2 (2026-10-30, accepted as read on e258a97): in a change that also touches code, a `*.md` file or a file under `docs/` is never counted as
  unmapped, so a changelog fragment alone does not make `balanced` full; the brief states the docs rule only for a change
  of only such files.
- Q-373-3 (2026-10-30, accepted as read on e258a97): a `tests` glob selects only test files (`test_dirs` and `test_patterns`), not helper files such as
  `conftest.py` under the same folder; the brief says "each existing test file".
- Q-373-4 (2026-10-30): a helper under the test folders (such as `tests/conftest.py`) is unmapped, so it makes
  `balanced` full; with `test_dirs = ["."]` only real test files are left out of `unmapped`. The conservative reading of
  the verdict on e258a97, item 2.
