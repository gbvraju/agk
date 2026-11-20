# Proposed spec amendments 201 (SPEC-0072; REQ-079)

Date: 2026-11-20 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0672 (brief #1592), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0072-each-work-type-playbook-carries-its-architecture-a-stack-sta.md` (rule 4, the `## Tests` section and
the `## Contexts` section). Brief #1592 reserved amendment 201. This file proposes the lines and does not edit the spec.
They are applied word for word, on a person's `Approve: SPEC-0072`; no session posts it.

## Why

On the default branch at 294b9e8 (2026-11-20) `init` writes `kit/templates/pyproject.toml` into every project with
`dependencies = []` and `requires = ["setuptools>=61"]`, a floor and not a pin, even for a `node` web app; no lock file is
required anywhere, and rule 4's foundation writes no build or lock file (gaps G16 and G21, brief #1592).

## Items

1. **Rule 4, two sentences added at its end.** "The foundation build also writes the chosen stack's build file from
   `kit/templates/stacks/<stack>/` with `engines.py stack-files` (Python: `pyproject.toml`, its dependencies added with
   exact `==` pins only; `node`: `package.json` with exact versions), over the untouched file `init` wrote of the same name
   only and never over a project's own, and commits the lock file that the stack's own tool makes on the builder's
   machine (Python: a hash-pinned `requirements.lock`; `node`: `package-lock.json`); `init` keeps writing its
   `pyproject.toml` until a stack is chosen. The `pins` step (`scripts/agk/gates/pins.py`) reads the build file and the
   lock, offline, and fails on a direct dependency not pinned exactly or not in the lock, on a missing lock and on a
   part of the Accepted stack record whose version differs from the lock's, naming the rule and the component class,
   never a name or a version; with no `[delivery] work_type` or no Accepted stack record it prints `not run: no stack
   chosen`." (answers 2 to 4)
2. **The `## Tests` section, one line added after the rule 4 line.** "- Rule 4, the pins: a sample with an unpinned
   dependency, a missing lock or a lock out of step with the record is red, a pinned sample and one with Windows line
   ends are green, a `node` sample gets `package.json` and no `pyproject.toml` from the foundation, and an adopted
   sample's build file is untouched; REQ-079 AC3 and AC4."
3. **The `## Contexts` section, its `stacks` line becomes:** "- stacks: each stack's lint, format and type step and its
   configuration come from its standards pack, Python first; its build file comes from `kit/templates/stacks/`, Python
   and `node` first, and its lock from its own tool; no stack's test or build step changes."
4. **Unchanged:** rules 1 to 3 and 5 to 13, the Proof, the Residual and the Open questions.

## Questions (brief #1592), each with the reading this proposal takes

- Q-1592-3 (the brief's Q-1): should `init` stop writing `pyproject.toml`? Reading: not in this build; the foundation
  replaces it only when it is the untouched `init` file and the stack is Python, and a `node` project keeps it beside
  `package.json`, as the kit's test settings may read it `(verify)`. A later brief drops it from `init`.
- Q-1592-4 (the brief's Q-2): which Python lock? Reading: `requirements.lock` with `--hash` lines, made by the stack's own
  tool on the builder's machine; the check reads its `name==version` lines and does not yet require the hashes.
- Q-1592-5: the runner of brief #1586 (pull request #1609) is not on the default branch. Reading: the step carries the
  runner's interface (`RULE`, `check(root, playbook)`) and runs by itself now; the playbook rows that name `pins` as a
  check gate are added by a mechanical follow-up once #1609 merges, so this build does not stack on it.
