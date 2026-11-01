# Proposed spec amendments 106 (SPEC-0004; REQ-011)

Date: 2026-11-01 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for ADR-0240
(brief #449), which stays `Proposed` for the maintainers' decision. The path: `docs/specs/0004-drift-audit.md`. The number 106 is
the next free one. It needs a person's `Approve: SPEC-0004`; no session posts it. It names in the spec the third command of rule 25
that `drift_audit.py` runs since brief #449; no other rule changes with it.

1. **SPEC-0004 rule 25, D9 the project's own commands**, gains, after "two settings, `unused_code` and `coverage`": "and a third,
   `mutation`", and gains, at its end: "For `mutation` the report run first lists the code files changed on the default branch in
   the audit's window (added or modified by its first-parent commits, still present, not documentation and not a test file),
   sorted by name and cut at 20, in a file outside the checkout that `AGK_CHANGED_FILES` names and that is removed after the run;
   it reads the number on the last line as for `coverage` and writes `killed <n>% of injected faults in <k> files` with its change
   since the previous audit, read from the `D9 mutation` line of `--previous FILE`. A command that runs too long, fails or prints
   no readable number reads `unknown`; with no changed code file the command is not run and the line reads
   `not run: no code file changed on the default branch in the last 7 days`. It never blocks."
2. **SPEC-0004 rule 3**, "the two commands of rule 25", reads "the three commands of rule 25". The cases are those of
   `tests/kit/test_drift_mutation.py`, which builds them in `tmp_path` from the drift fixtures: a score, no number, a failing
   command, no changed file and the setting unset.
