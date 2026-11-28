# ADR-0867: The parts step holds every dependency to the record

- Status: Proposed
- Date: 2026-11-28
- Deciders: maintainers (the owner's yes on brief #2071, 2026-11-27T19:43:45Z)
- Related: ADR-0834, ADR-0858, ADR-0860, ADR-0666, ADR-0668, ADR-0672, ADR-0742, ADR-0791, ADR-0677, ADR-0812,
  SPEC-0076, REQ-083, brief #2071, plan #661
- Requirements: REQ-083

Protected classes: `scripts/agk/`, `kit/`, `tests/kit/`, `agk.toml`

## Context

SPEC-0076 (Approved, ADR-0834) rule 15 build (d) asks for rule 8's checked step and rule 3's plan hold. On main at
5170db3 a product whose `package.json` holds a library that neither `docs/parts.md` nor the stack record names prints
`ok pins` and no `parts` row, and `check_plan.py` lets a foundation brief run before the record is confirmed. Build (c)
(ADR-0860) gave the record's form (`kit/templates/parts.md`, `parts_record.COLUMNS`). The brief reserved ADR-0861,
which #2084 took when it merged; this ADR takes ADR-0867 on the conductor's note on #2071 (`Q-PD-8`).

## Decision

1. **The step.** `scripts/agk/gates/parts.py`, after `pins` in `run_gates.PRODUCT_STEPS`, files only, reads per
   runtime of `pins.runtimes_of` the record's rows (one `## <runtime>` section each by `pins.RUNTIME_NAMES` with two
   runtimes, every row with one), the build files through `pins.declared` and the lock through `pins.locked`, names
   after `pins.norm`. It finds: a direct dependency the record and the chosen option's `Parts:` do not name
   (`dependency`, held to its build file); a record part missing from its build file, or whose version differs from
   the build file's or the lock's (`record part`); a row with an empty `Why`, `Alternatives considered`, `Licence`,
   `Health (date)` or `For the business`, a second part for one need with no `Decision: <need>` line, and a health
   `read` date older than `parts.max_age_months` (`record row`); a record that is not UTF-8 or has no table of the
   nine columns (`record`). A `stdlib` part needs no dependency. Each line names `SPEC-0076 rule 8` and the class,
   never a name or a version.
2. **Not run.** In order: `no stack chosen`, `no reader for this stack`, `no parts record`, `no foundation yet`, and
   `the build files are not read` (a runtime in two folders or a build file `pins` cannot read, which `pins` fails).
3. **Required and optional.** With `[parts] record = "required"` every finding fails, but a stale health date fails
   only when `run_gates.touched` holds the record, a build file or a lock of the runtime, and warns otherwise (no base,
   no `.git`, or a base CI cannot resolve). With `optional`, or no `[parts]` table, every finding warns. A refused
   table is one failure `the [parts] table is refused (setting: parts.<key>)`.
4. **Warnings in the runner.** `run_gates.results` reads an optional module function `notes(root, playbook)`: each
   line prints `warn <id>: <line>`, and a step with notes and no failure prints `<id>: <n> warnings (setting: ...)`
   from the module's `NOTED`, never `ok <id>`; notes never change the exit code. A failure class `setting: ...` prints
   as `(setting: ...)`. No other step defines `notes`, so every other output is unchanged.
5. **The plan hold.** `check_plan.parts_problems(root)`, beside `contract_problems`: with a declared work type,
   `record = "required"` and one `Kind: foundation` brief file, while `parts.confirmed(root)` is false, one line
   `SPEC-0076 rule 3: <key>: the foundation brief before a confirmed parts record (setting: parts.record)`; a refused
   table there is the same refusal line. `parts.confirmed` is true when the record's last line is `Confirmed by:
   <name> (<YYYY-MM-DD>)`, the name not a `TODO(` mark and the date a real date. `plan_intake.py` is unchanged.
6. **Installed.** `kit/manifest.json` `verbatim` gains `scripts/agk/gates/parts.py`; a `[[testing.map]]` entry maps it.

## Consequences

Under `required` a library added without its row is red, and a plan cannot start its foundation before the record is
confirmed; under `optional` the same findings print as warnings. The kit declares no work type, so its own output is
unchanged. No workflow, ruleset, required check, `agk.mk` or `governance_map.CHECKS` changes.

## Residual

The adopted baseline and its harvest are build (g) (`Q-PD-5`, no `counts` here); the build files written from the
record are build (e).
