# ADR-0775: The reference guide is a shared index of this repository, so a clean merge that only meets it takes the light re-prove (REQ-057)

- Status: Proposed
- Date: 2026-11-24
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1873, ADR-0495 (amendment 171, the light re-prove), ADR-0718 (amendment 216, the one-merge carry),
  ADR-0351 (the shared indexes never make an overlap), ADR-0320 (the pre-merge tests), ADR-0650 (the whole tests),
  ADR-0725 (the router's light and full labels), ADR-0626 (this repository runs in local mode), plan #661
- Requirements: REQ-057

Protected classes: `agk.toml`, `tests/kit/`, `tests/kit_dev/`

## Context

Three re-prove rounds in one run (#1866, #1867 and #1870, on 2026-11-23) had one cause: `docs/guides/reference.md`
changed on the default branch and on the pull request, with a clean merge each time. Its file is not one of the five
shared indexes of SPEC-0050 rule 3 (`session_plan.SHARED_INDEXES`), so `session_plan.reprove_kind` gave `full` and each
round cost a builder round and a second review. With the reference added to the list it gives `light` for all three heads
(the brief's `Measured:` line, reproduced). The guide is 65 sections, one section or table row per command or setting, and
builds append or edit their own rows, so a clean merge keeps each side's lines; what it can break is a rule over the whole
file. Of the tests that read it, `tests/kit_dev/test_reference_commands.py` (every installed script named) reads it whole
and was neither a pre-merge nor a whole test. The owner's word (2026-11-24, the steward chat, quoted as data): "Yes, file
the reference light re-prove brief".

## Decision

1. This repository's `agk.toml` `[flow]` sets `shared_indexes` to the five defaults of `session_plan.SHARED_INDEXES`, in
   their order, then `docs/guides/reference.md`. A set list replaces the default (rule 3, `Q-RL-2`), so all five stay
   listed. No code changes: `session_plan.shared_indexes`, `conductor.reprove`, `merge_cleared.shared_of`,
   `route.reprove_settings` and `session.carried_check` read the setting already; the merger and the router read it from
   the default branch once it merges.
2. `[testing] pre_merge_tests` gains `tests/kit_dev/test_reference_commands.py`, so `merge_cleared.py` runs the
   reference's whole-file command test on every would-be merge, light or full (`Q-RL-3`).
   `tests/kit/test_merge_cleared_pre_tests.py`, which pins this repository's list, names it as the fourth entry and
   keeps the other three (the conductor's ruling of 2026-11-24 on #1875).
3. `tests/kit_dev/test_shared_index_reference.py` guards the list: it holds every default and the reference and passes
   `session_plan.shared_indexes`; each entry is a tracked file, not under `docs/specs/` or `docs/adr/`, with no wildcard;
   and `pre_merge_tests` names the reference test. It is listed in the map entry of `scripts/agk/session_plan.py`.
4. The kit default and SPEC-0050 stay as they are (`Q-RL-1`): the kit installs no `docs/guides/reference.md`, and a
   project's own file of that name may not merge by line. A project may set its own list the same way.
5. A shared index also carries an owner's answer over a light merge (brief #1616) and never makes an overlap; both hold
   for the reference (`Q-RL-4`). Its overlap was already exempt as prose under `[flow] reprove_paths`.

## Consequences

A pull request whose only file in common with a newer merge is the reference guide is brought up to date by the
conductor's update-branch and keeps its verdict over that one clean merge, with the required checks on the new head; in
local mode the new head still needs its own local evidence (SPEC-0039 rule 4). A conflict, or a code file beside the
reference, keeps the full re-prove. Each merge runs one more pre-merge test (about 0.1 s). A later file that joins the
list does so by one line and an ADR in its own brief, and the guard test fails if a default is dropped.

## Residual

- 2026-11-24: the testing map named in the same steward run (challenge 1) is not listed here; its own brief decides it
  (`Q-RL-6`).
- 2026-11-24: a kit default that includes the reference would need an amendment of SPEC-0050 rule 3 (`Q-RL-1`); none is
  proposed.
