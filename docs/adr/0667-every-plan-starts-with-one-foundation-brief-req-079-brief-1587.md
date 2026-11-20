# ADR-0667: Every plan starts with one foundation brief, and the stack record arrives with its practices (REQ-079)

- Status: Proposed
- Date: 2026-11-20
- Deciders: maintainers
- Related: SPEC-0072, SPEC-0043, SPEC-0038, SPEC-0029, brief #1587, brief #1585, plan #661, ADR-0665, ADR-0643
- Requirements: REQ-079

Protected classes this pull request changes: `config/` (`config/playbooks/`), `scripts/agk/` (`playbook_format.py`,
`check_plan.py`, `plan_intake.py`, `engines.py`, `front_door.py`), `kit/` (`kit/templates/stack-adr.md`), `skills/`
(`skills/plan-intake/SKILL.md`), `tests/kit/` (the new `test_foundation_kind.py` and the playbook and plan tests whose
kind order changes) and `tests/kit_dev/` (the stack record tests). `kit/hashes.json` is not edited by hand.

## Context

SPEC-0072 (Approved, REQ-079) rule 12 build (c) builds rule 4: every playbook's `[split] brief_order` gains
`foundation` first, `plan-intake` proposes one foundation brief that every other first-milestone brief depends on,
`check_plan.py` refuses a feature brief before it and a new project's foundation brief while no work type is set, and
`engines.py stack-write` fills the stack record's `Practices` from the composed playbook with no `TODO(architect)`. On
the default branch at 28ddd04e (2026-11-20) no `brief_order` holds `foundation` (`default.toml`'s is `[]`), the proposals
have no foundation mark, `check_plan.py` reads no `Kind:` line, `stack-write` reads only the declared playbook's own
gates (not `default.toml`'s eight enterprise gates) and the template writes `Practices: TODO(architect)` per option.
ADR-0665, the build (a) ADR, is Proposed, so no Accepted ADR covers these classes and this build writes its own.

## Decision

1. Every shipped playbook's `brief_order` starts with `foundation`: `default.toml`'s is `["foundation"]` and
   `pilot.toml`'s starts `foundation` before `intake` (`Q-S0072-11`). A project playbook drafted by `front_door.py`
   writes `["foundation"]`. In the split (`playbook_format.split`), a kind that no `depends_on` pair orders after
   another depends on `foundation` when the order holds it; the other kinds follow it through their pairs.
2. The proposals' brief takes an optional `foundation` (true or false). With `[delivery] work_type` declared,
   `plan_intake.py validate` wants exactly one foundation brief, in `M1`, named in `depends_on` by every other `M1`
   brief; with no work type a foundation brief is refused naming the setting `work_type`. `render` writes its
   `Kind: foundation` line.
3. `check_plan.py`, when `docs/plan/` exists: with a work type, the brief files hold one `Kind: foundation` brief in
   the first milestone of `docs/plan/milestones.md`, and every other brief of that milestone has a `Depends-on:` line
   naming it; with no work type a foundation brief is refused naming the setting, and nothing else is held, so the
   kit's own repository and an existing project are unchanged (`Q-S0072-17`). Each refusal names `SPEC-0072 rule 4`
   and the brief key, never a value. This is the hold of brief #1587 answer 4 until build (h) reads rule 8's
   confirmation.
4. `engines.py stack-write` writes one practice per gate of the composed playbook (`default.toml`, the modules, then
   the playbook, as `check_playbooks.composed`), so the eight enterprise gates are among them; with no declaration,
   `default.toml` alone gives them when it is present. The template's `TODO(architect)` practice bullet is gone and each
   option's `Practices:` is `{{practices}}`, which `stack-write` fills with every practice of the Practices item. The
   architect may still change any practice before the record is accepted.

## Consequences

A work-type project's plan cannot put a feature brief of the first milestone ahead of its foundation brief without
`make governance` failing, and the foundation brief of a project with no work type is held. The stack record starts
with the enterprise gates as its practices and no `TODO(architect)` in them. No workflow, ruleset or required check
changes. What the foundation build writes (the skeleton, `docs/architecture.md`, the pack configuration) comes with
builds (d) and (e), briefs #1588 and #1589.

## Residual

- 2026-11-20: a brief_order of a project's own playbook that does not start with `foundation` is not refused by the
  playbook check; `check_plan.py` holds the plan instead (due 2027-01-31, with build (h)).
