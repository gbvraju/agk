# ADR-0756: Every writer of a brief runs the one brief check with its study (REQ-037)

- Status: Proposed
- Date: 2026-11-23
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1813, brief #1800 (ADR-0752, Q-1800-1), ADR-0102, ADR-0120, ADR-0170, ADR-0361, SPEC-0043 rules 7
  and 25, amendment 169, SPEC-0059 rules 6, 7 and 12, ADR-0714, plan #661
- Requirements: REQ-037

Protected classes: `scripts/agk/`, `.claude/`, `kit/`, `tests/kit/`

## Context

Brief #1800 (ADR-0752) added the study lines (`Impact:`, `Wiring:`, `Prior:`, `Class:`), read by
`brief_study.study_result`, which only `check_brief.check` and `check_brief.event_result` called. Four other entry
points read a brief with parts of `check_brief.py` and never the study: `plan_intake.brief_check` (`publish`, GitHub
and the personal files forge), `steward_owner.brief_refusal` (the steward's `file_brief` and `fix_brief`),
`steward_evidence.triage` and the conductor guard's `brief_checked`, which called `brief_problems`,
`absent_requirements` and `screens_problems` one by one. The plan's renderer and the brief template wrote no study
line in the form the check reads, so `STUDY_FAILS_FROM` could not be set without failing the kit's own writers
(35 tests in 16 files, PR #1804). The owner's word (2026-11-23, the steward chat, quoted as data): "Yes, brief the
study refuse day".

## Decision

1. `check_brief.brief_result(body, root, waves=None, opened=None) -> (failures, warnings)` is the one reading of a
   brief: `body_problems`, then, when it passes, `brief_study.study_result`, with the protected-path warnings.
   `check` and `event_result` call it and print or return what they did before.
2. `plan_intake.brief_check`, `steward_owner.brief_refusal`, `steward_evidence.triage` and the conductor guard's
   `brief_checked` call `brief_result` instead of its parts. A failure refuses as each refused before; the warnings
   are printed as `warning: study: ...` after the steward's own lines and before `publish`'s output (`briefs <key>:
   warning: ...`); the guard prints nothing. `triage` passes the root for a kit brief only when the root holds
   `kit/manifest.json` (the kit itself), and `None` otherwise, as before (Q-1813-1). The guard now refuses what
   `check_brief.py --root <project>` refuses, a missing `Contexts:` line and the root's touch and name rules included.
3. `plan_intake.brief_text` (`render`) writes after `Contexts:` the line `Impact:`, its five lines, `Wiring:`,
   `Prior:` and `Class:`, each with the placeholder `(verify) for the person to state` in the form the check reads;
   `publish` carries them through `issue_body` unchanged.
4. `brief_study.study_result` warns, on any day and never as a failure, for each study line that holds that
   placeholder: `study: the <name> line is the render's placeholder` (Q-1813-2).
5. `docs/briefs/TEMPLATE.md` lists the study lines in that form, with one example each in a comment below them.
6. `STUDY_FAILS_FROM` stays `None`; no setting is added. `review_mode`, `pr_mode`, `execution`, `[steward]
   auto_file` and `fix_briefs`, `[flow] plan_issue` and `brief_code_paths` and personal mode read as before.
7. `tests/kit/test_brief_writers.py` fails a change that reads a brief with `body_problems`, `brief_problems`,
   `absent_requirements`, `screens_problems` or `touch_problems` outside `check_brief.py`, in `scripts/agk/*.py` and
   `.claude/hooks/*.py` (an `ast` scan), and runs every writer's body through `brief_result` with the day in the past.
8. Not changed, and file nothing: `plan_ceremony`'s printed candidate briefs and `personal.py export` (the target's
   own check judges what it prints); `route.red_body` stays held to none (brief #1800).

Path classes changed: `scripts/agk/` (`check_brief.py`, `brief_study.py`, `plan_intake.py`, `steward_owner.py`,
`steward_evidence.py`), `.claude/` (`hooks/conductor_guard.py`), `kit/` (`kit/hashes.json`, regenerated), `tests/kit/`
(the new test file, the study lines in the writers' fixtures and the guard's fixture as a real git repository, now
that the guard lists the tree).

## Consequences

The plan's briefs, a sidecar's briefs, the steward's briefs and the conductor's briefs meet the same check as a brief
filed on GitHub, so a later brief can set the refuse day without failing the kit's own writers. A rendered brief has
nine more lines, each warned until the person fills it.

## Residual

The refuse day is unset; until it is named the study only warns. A plan rendered before this change keeps no study
lines; `publish` warns for each until the person adds them.
