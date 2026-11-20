# ADR-0672: The stack record pins versions and licences, and the stack writes its own build and lock files (REQ-036, REQ-079)

- Status: Proposed
- Date: 2026-11-20
- Deciders: maintainers
- Related: brief #1592, SPEC-0029, SPEC-0072, SPEC-0054, amendment 200, amendment 201, ADR-0671, brief #1591, brief #1586, plan #661
- Requirements: REQ-036, REQ-079

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `kit/`, `skills/`, `agk.toml`

## Context

On the default branch at 294b9e8 (2026-11-20) the stack record (`kit/templates/stack-adr.md`) has no version or licence
field and `engines.py` `stack_problems` checks none; `init` writes `kit/templates/pyproject.toml` into every project with
`dependencies = []` and `requires = ["setuptools>=61"]`, a floor, even for a `node` web app; no lock file is required
anywhere (the kit pins only its own tools in `config/ci-tools.txt`). SPEC-0072 rule 4's foundation writes no build or lock
file. Builds of one product are therefore not repeatable, and a non-Python product gets a Python file only.

## Decision

1. SPEC-0029 rule 5 and SPEC-0072 rule 4 change only through amendments 200 and 201, which this build writes; they are
   applied on a person's approval, never by a session.
2. **Parts with versions and licences.** In a Proposed stack record each option names `Parts:`, a list of
   `<name> <exact version> <licence id>` for the runtime, the framework, the database engine and each library it names,
   placed after its trade-offs and `Why:` and before `External services:`. An exact version has two or more numeric
   fields and at most a pre-release or build tag; the licence is an SPDX id or expression, checked for form, offline.
   `stack-check` refuses a range, no version or no licence naming the rule, the option letter and the part's place,
   never a value; `(verify)` marks are allowed. An Accepted record is checked as before (principle 11; no record written
   before this change is refused). The skeleton writes `Parts: TODO(architect).` in each option.
3. **The stack's own build file.** `engines.py stack-files` writes the chosen stack's build file from
   `kit/templates/stacks/<stack>/` (`python-pyproject`: `pyproject.toml`, the build backend pinned with `==` and the
   dependencies added with `==` only; `node`: `package.json`, private, no dependencies yet). The chosen option's part
   named `python` or `node` selects the folder. It writes over the file `init` wrote only while that file is untouched,
   and keeps any other build file, so an adopted project's file is never rewritten (`mode = "adopt"` always keeps it).
   `init` keeps writing its `pyproject.toml` until a stack is chosen, and a `node` project keeps it beside
   `package.json` (brief Q-1).
4. **The lock.** The lock is made by the stack's own tool on the builder's machine and committed: `requirements.lock`
   with `--hash` lines for Python (brief Q-2), `package-lock.json` for `node`. No check makes or fetches one.
5. **The `pins` step.** `scripts/agk/gates/pins.py`, installed and importing only installed modules, reads the chosen
   stack's build file and lock, offline, line ends normalised, and fails on a direct dependency not pinned exactly or not
   in the lock, on a missing lock, and on a part of the Accepted record whose version differs from the lock's; each line
   names the rule and the component class (`dependency`, `lock file`, `build file`, `stack part`), never a name or a
   version (principle 8, as SPEC-0054 rule 4 does). With no `[delivery] work_type`, no Accepted stack record or no part
   it knows, it prints `pins: not run: no stack chosen`. It carries the interface of the runner of brief #1586 (`RULE`,
   `check(root, playbook)`); the playbook rows that run it as a check gate inside `governance` follow once that runner
   merges, by a mechanical brief, so this build does not stack on pull request #1609.

## Consequences

A stack record names what each option installs and under which licence; the foundation writes the chosen stack's own
build file; a pinned, locked product passes `pins` and an unpinned one is red. Hosted, local and personal modes run the
same step once the runner calls it; customer projects' locks hold only public package names and versions.

## Residual

- The `pins` gate rows in `config/playbooks/` and the call from `run_gates.py` come after pull request #1609 merges
  (due 2026-12-15).
- An adopted project's `pins` findings are baselined by brief #1600's baseline once it is built (due 2027-01-31).
- The Python lock's `--hash` lines are not yet required by the step, and other stacks get their template folder with
  their standards pack (due 2027-03-31).
