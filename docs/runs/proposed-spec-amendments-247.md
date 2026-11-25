# Proposed spec amendments 247 (SPEC-0072; REQ-079)

Date: 2026-11-25 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0800 (brief #1932), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0072-each-work-type-playbook-carries-its-architecture-a-stack-sta.md` (rule 4). Brief #1932 reserved
amendment 247. This file proposes the lines and does not edit the spec. They are applied word for word, on a person's
`Approve: SPEC-0072`; no session posts it (`Q-MR-1`).

## Why

An adopted project with Node at the root and Python in `service/` accepted a stack whose chosen option names both
runtimes; the `pins` step printed `not run: no stack chosen` and read one build file and one lock at the root (#1771,
AD-03 and AD-06).

## Items

1. **SPEC-0072 rule 4, the `pins` step.** Replace "The `pins` step (`scripts/agk/gates/pins.py`) reads the build file
   and the lock, offline," with "The `pins` step (`scripts/agk/gates/pins.py`) reads each chosen runtime's build file
   and lock, in the folder that holds it, offline (amendment 247),".

No other rule changes.
