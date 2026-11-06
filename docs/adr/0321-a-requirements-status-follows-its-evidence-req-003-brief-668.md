# ADR-0321: A requirement's status follows its evidence (REQ-003, brief 668)

- Status: Proposed
- Date: 2026-11-06
- Deciders: maintainers
- Related: ADR-0172, SPEC-0010, SPEC-0011
- Requirements: REQ-003

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`, `agk.toml`

## Context

On the default branch on 2026-11-06, 35 of 53 requirements in `docs/requirements.md` read `planned` and 17 read `done`,
while many of the planned ones belong to Approved specs that are built. Nothing compares a status with its proof, so the
status is only as true as the last person who edited it. Brief #668 asks for a kit command that prints the requirements
whose status disagrees with the evidence, and a way to write the statuses that follow from it. The proof of a
requirement is what SPEC-0010 rule 1 already says: every criterion has a test marker.

## Decision

1. **The command.** `scripts/agk/req_status.py` (installed, verbatim) with `report` and `apply`, as proposed spec
   amendments 133 rules 26 and 27 to SPEC-0010 describe. The proof of a requirement is the set of test files holding its
   `REQ-nnn ACn` markers, one or more for every criterion; it passes when each file passes when its `[proof]` area's
   command runs it alone. Each file runs once per invocation. A timeout is `unknown`, never a pass.
2. **No proof mapped.** A requirement with no `ACn` in its acceptance line, with a criterion that has no marker, or with a
   test file that no `[proof]` area runs prints `REQ-nnn: no proof mapped`, and nothing about it changes. Without a
   `[proof]` table no requirement has a proof mapped: the whole `project_tests` command cannot say which test failed.
3. **Promotion only.** `apply` changes `planned` or `in-progress` to `done` and nothing else; a `done` whose proof fails is
   flagged (exit 1) and left for a person. It edits only `- Status:` lines and refuses when `docs/requirements.md` is
   already changed in the work tree. The conductor runs it in one pull request of its own; a builder never does.
4. **Unchanged.** The weekly report (SPEC-0011) gains no line: its sections are built from the facts document and fixed
   item kinds, so a new line would be a new item kind and needs an amendment of SPEC-0011. `check_requirements.py` is
   unchanged, so no status edit is refused by a check yet. No `- Status:` line changes in the pull request of this build.

## Consequences

The conductor can ask one command which statuses are false and write the promotions in one status-only pull request.
A run of `report` over this repository runs every test file that proves a requirement, so it is a heavy step, run under
the heavy lock where sessions share a machine.

## Residual

- 2026-11-06: a status edit that disagrees with the proof is not yet refused by a check; a check that reads results
  without running the tests is a later brief (due 2026-12-31).
- 2026-11-06: the weekly report does not list the disagreements; that needs an amendment of SPEC-0011 (due 2026-12-31).
- 2026-11-06: a `done` whose proof fails is flagged, never set back; whether `apply` should demote it is the
  maintainers' decision (due 2026-12-31).
