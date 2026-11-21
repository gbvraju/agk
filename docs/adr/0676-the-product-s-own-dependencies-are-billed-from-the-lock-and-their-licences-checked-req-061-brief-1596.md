# ADR-0676: The product's own dependencies are billed from its lock, and their licences are checked (REQ-061, REQ-079)

- Status: Proposed
- Date: 2026-11-21
- Deciders: maintainers
- Related: brief #1596, SPEC-0054, SPEC-0072, amendment 206, ADR-0349, ADR-0672, ADR-0666, brief #1592, brief #1586, brief #1600, plan #661
- Requirements: REQ-061, REQ-079

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`, `agk.toml`

## Context

On the default branch at 11fa8bc (2026-11-21) SPEC-0054 rule 2's bill reads `pyproject.toml`, `config/ci-tools.txt`, the
workflows and the kit's files, and never a lock file; rule 4 says no governance step runs `sbom.py check`; no rule or check
reads a dependency's licence (gap G18). Brief #1592 (ADR-0672) gave a chosen stack its committed lock and its record's
`Parts:` licences, and brief #1586 (ADR-0666) the gate runner. A product with a dependency under a licence outside any list
passes every check.

## Decision

1. SPEC-0054 rules 2, 4 and 6 change only through amendment 206, which this build writes for the maintainers' approval;
   the code below follows its text and stays inert in a repository with no chosen stack, the kit's own included.
2. **The product's bill.** With a `[delivery] work_type` and one Accepted stack record, `sbom.py make` also lists each
   package of the chosen stack's committed lock at the commit, class `python` (`requirements.lock`) or `node`
   (`package-lock.json`), with its exact version, its package URL (`pkg:pypi`, `pkg:npm`) and its licence as one CycloneDX
   `licenses` expression: the lock's `license` where it states one, else the record's `Parts:` entry of that name. A lock
   entry replaces a `pyproject.toml` entry of the same reference. `sbom.py check` compares the licence as it compares a pin.
3. **The `licences` step** (`scripts/agk/gates/licences.py`) fails on a package licence outside `allowed` of
   `config/licences.toml` and on a package with no readable licence (`unknown`, never clean); an SPDX expression passes
   when one `OR` side has every `AND` id on the list. Lines name the rule and the component class, never a name, version
   or id; a list of another form is refused naming the setting. Absent, the list is `kit/templates/licences.toml`'s,
   which `engines.py stack-files` writes once into the project. Widening it is a project ADR (principle 11).
4. **The `bom` step** (`scripts/agk/gates/bom.py`) makes the bill of `HEAD` in memory and checks it with `sbom.py`'s own
   check; nothing is written.
5. **Where they run.** `run_gates.py` runs both steps after the gates, as it runs `layers`, only where a stack is chosen and
   its lock is read, so they run in the project's `governance` and `prepush.py` with no workflow change, and a project
   without a stack (the kit's own) prints what it printed before. They are not new `[[gates]]` rows of
   `config/playbooks/default.toml`: that changes SPEC-0072 rule 2's and SPEC-0048 rule 21's fixed gate lists, which
   amendment 206 does not reach (Q-1596-4). With no stack or no lock the step's own command prints `not run: no lock`.
6. **Adopted projects.** With `mode = "adopt"` the licence findings are held until brief #1600's baseline, as ADR-0673
   holds the secret findings.
7. **Not built here.** The weekly scan stays SPEC-0054 rule 6's workflow step on the owner's yes (build (d)); the local
   scheduled scan waits for the owner's answer to Q-1596-2; `sbom.py findings` already reads the `node` components.

## Consequences

A product's bill lists what its lock installs with each licence; a forbidden or unreadable licence turns `governance` red
naming the rule and the component class; the kit's own output and checks are unchanged. The template's list is a policy,
not legal advice.

## Residual

- 2026-11-21: the local scheduled scan job of SPEC-0064 and the personal-mode sidecar result wait for Q-1596-2 (due
  2027-01-31).
- 2026-11-21: the adopt-mode baseline of licence findings follows brief #1600 (due 2027-01-31).
- 2026-11-21: a Python lock records no licence, so each Python package's licence comes from the record's `Parts:` and an
  unnamed transitive package is `unknown`; further stacks follow with their packs (due 2027-03-31).
