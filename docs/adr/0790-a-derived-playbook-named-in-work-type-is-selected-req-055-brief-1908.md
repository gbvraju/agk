# ADR-0790: A derived playbook named in `[delivery] work_type` is selected in both layouts (REQ-055)

- Status: Proposed
- Date: 2026-11-24
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1908, SPEC-0038 rule 5, SPEC-0048 rules 21 and 22, SPEC-0072 rules 3 and 8, ADR-0312 (the declaration),
  ADR-0697 (the resolver), ADR-0666 (the gates runner), ADR-0781 (derive-write in a clean project), amendment 233
- Requirements: REQ-055

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

In the adopt re-run of test plan 3 (AD-05, #1771) `front_door.py derive-write --slug orders` wrote
`config/playbooks/orders.toml`, but `[delivery] work_type = "orders"` was then refused by every reader
(`rule 5: ... is not one of the work types (setting: work_type)`), in the installed and the clean layout.
`playbook_format._declared` refused any value outside `WORK_TYPES` before `is_derived` was read, though `problems` and
`_architecture` already accept a derived name by `is_derived`. SPEC-0048 rule 22 (Approved) says a derived playbook is
declared by that line. Separately, `run_gates.py` alone, as `personal.py floor --approve` runs it, passed a declared
playbook that `check_playbooks.py` fails. The owner's word (2026-11-24, the steward chat, quoted as data): "Yes, file the
four test-run briefs".

## Decision

1. **The declaration.** `_declared` accepts a value outside `WORK_TYPES` exactly when `is_derived(value, root)` holds (not
   `default`, matching `DERIVED_NAME`, and `docs/research/<value>.md` a file of the project), the one test `problems`
   already uses (`Q-DP-3`). Every other value keeps today's line. No reader changes: each reads `declaration` or
   `selected`.
2. **Where it is read** (`Q-DP-2`). `folder(root, name)` returns the project's own `config/playbooks/` for a derived name
   in both layouts, so the plugin's folder never stands in for it; a missing project file gives today's missing line.
3. **A declared playbook that fails its check** (`Q-DP-4`). When a work type is declared and
   `check_playbooks.findings(root, [selected])` names a problem, `run_gates.py` prints one line
   `FAIL gates: playbook: SPEC-0038 rule 5: the declared playbook fails check_playbooks.py (setting: work_type)`, runs no
   gate and exits 1, for a derived or a shipped playbook. With no declaration nothing changes.
4. The line and its ADR stay the owner's: no session writes `[delivery] work_type` (SPEC-0048 rule 22, SPEC-0072 rule 8).
   `engines.py questions --work-type` and `steward_owner.py work-type` still take only a kit work type (`Q-DP-5`,
   `Q-DP-6`). Amendment 233 proposes the words of SPEC-0038 rule 5; the spec is not edited here (`Q-DP-1`).

## Consequences

A drafted project standard is applied by the owner's line, as SPEC-0048 rule 22 says, instead of being copied over a
shipped name. A failing declared playbook fails the personal floor and a `run_gates.py` run alone. A test asserts that
`declaration` and `problems` accept the same names for one fixture, so the check and the selection cannot disagree again
without a test change in review.

## Residual

The comment of `kit/templates/agk.toml` lists eight work types and no derived playbook (`Q-DP-9`); unchanged here, its own
brief with a changelog fragment. A research record that later fails rule 6 does not refuse the declaration (`Q-DP-7`).
Recorded 2026-11-24.
