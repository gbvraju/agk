# ADR-0842: An engine or a playbook may name a skill of a pinned pack in use

- Status: Proposed
- Date: 2026-11-27
- Deciders: maintainers (the owner's yes on brief #2035, 2026-11-27T07:25:55Z; amendment 261 approved on #2023)
- Related: ADR-0837, ADR-0838, ADR-0840, SPEC-0077, SPEC-0029, SPEC-0048, REQ-084, brief #2035, plan #661
- Requirements: REQ-084

Protected classes: `scripts/agk/`, `tests/kit/`, `agk.toml`

## Context

SPEC-0077 (Approved, ADR-0837) rule 14 build (e) asks that an `[engines]` value and a playbook's `skills` may name a
skill of a pack in use (rule 12), with amendment 261 to SPEC-0029 rules 1 and 2. Before it, `doctor.engine_results`
read any `<prefix>:<skill>` but `agk:` as `cannot-check plugin-unreadable`, and `doctor.skill_lines` read only the
project's, the user's and the plugin's skills. Build (c) (ADR-0840) pins every file of a pack in `config/packs.lock`
and `packs.verify` checks it offline.

## Decision

1. **Engines from a pack.** `doctor.pack_skill(root, pid, name)` reads a pack only when `pid` is in `[packs] use`:
   `present` when the lock holds `skills/<name>/SKILL.md` of that pack, `check_packs.problems` passes on its folder
   and `packs.verify` gives no line for it; otherwise `missing`, the line ` (missing: packs)` naming the reason class
   and never a value. A prefix that names no pack in use, or a refused `[packs]` table, keeps today's
   `cannot-check plugin-unreadable`; unprefixed and `agk:` names are unchanged, except that a pack named `agk` in use
   and in the lock is read as a pack (answer 5).
2. **Playbook skills.** `doctor.skill_lines` counts an unprefixed name as `present` also when a pack in use holds it
   in its lock and passes the same checks.
3. **A failing verify is missing (`Q-PE-1`).** A changed, unlocked or removed file of the pack, or a refusal of its
   own checks (where `[packs] trust` and build (d)'s scan land), reads `missing`, never `present`: only the lock's
   verified folder counts, so an unlocked copy is never used silently.
4. **The amendment.** Amendment 261's two items are applied to SPEC-0029 rules 1 and 2 word for word and the file is
   marked applied; no other rule changes. `agk.toml`'s `[[testing.map]]` entry of `doctor.py` names
   `tests/kit/test_engine_packs.py`.

## Consequences

A project can pin an outside drafting skill and see it reported as present or missing. Doctor reads one lock and the
pack's files offline; no workflow, ruleset, required check, label, `agk.mk` or `governance_map.CHECKS` changes.

## Residual

`[packs] trust` refusing a pack and the instruction scan are build (d); this build reads them through
`check_packs.problems` once they land.
