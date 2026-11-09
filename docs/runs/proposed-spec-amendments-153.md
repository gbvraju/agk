# Proposed spec amendments 153 (SPEC-0055; REQ-051, REQ-062)

Date: 2026-11-09 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). ADR-0393 and
brief #878 name this route; it changes `docs/specs/0055-the-right-tests-for-each-stack-run-at-the-right-time-by-a-map-that-learns.md`
once the owner's `Approve:` line approves it, and no Approved spec is edited in this pull request.

1. **SPEC-0055 rule 6, what `always_full` holds.** After "The `thorough` profile and `always_full` are unchanged." add:
   "`always_full` names only test infrastructure: the files that change how tests are found or run (test configuration,
   shared fixtures, the build and CI files, the test runner's own code). Any other entry needs an adjacent `# full: <reason>`
   comment, and `check_kit_tests.py` in AGK itself and `doctor.py` in a project refuse an entry without one, naming this
   rule and the entry's place, never its value."
2. **SPEC-0055 rule 6, a changed code file.** After that sentence add: "For a changed code file `impact.py` selects the
   tests its map entries name and the tests of every file that imports it, one level, and prints
   `selected: <file> -> <k> tests (<j> by importers)`. This only adds tests, so it is no narrowing of rule 2."
3. **SPEC-0055 rule 14, the full suite's budget.** After "full runs by reason (`always_full`, `unmapped`, `thorough`,
   `level not on pull requests`)." add: "It also gives the median selected and full test minutes of pull request runs, the
   reason of each full run (`always_full <entry>`, `unmapped`, `thorough`), and the full suite's median on the default
   branch against `[testing] budget_seconds` with the slowest ten test files and the workers' balance. The budget is a
   report and never fails a run; over it the conductor files one brief to split or speed up the slowest files, never to
   remove a test."
