# Testing: which tests guard which code

A one-line change should not have to run every test of the project, and it should never run too few. The optional
`[testing]` table of `agk.toml` says, by rule, which tests guard which code, and the test plan shows, before anything runs,
the regression tests that a change selects and the rule that chose each. The rules belong to the project, not to the agent:
`agk.toml` is a protected path, so a change of a rule comes with an ADR in the same pull request, and an agent cannot loosen
the rules to pass a gate.

Nothing runs the selection yet. Proof, the pre-push run and CI are unchanged: governance still runs every project test on
every ready push. The plan shows what the selection would be, so a project can check its rules before later work uses them.

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

Every key is optional; an empty `[testing]` table takes the defaults. A bad entry is refused, and the message names the setting
(for example `setting: testing.map[2].tests`), never its value.

A glob is a path from the top of the repository. `*` and `?` stay inside one folder, `**` crosses folders, and a glob that ends
in `/` means everything below that folder. A glob uses `/` between folders, never `\`, and may not start with `/` or hold a `..` part.

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

The decision is ADR-0220 (brief #373).
