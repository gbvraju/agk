# ADR-0594: A kit defect is reported in one labelled form, and a steward that loses its GitHub reads says so once

- Status: Accepted
- Date: 2026-11-16
- Deciders: maintainers
- Related: brief #1411, brief #1410, ADR-0593, ADR-0561, ADR-0557, plan #661
- Requirements: REQ-050

## Context

Brief #1411 is part 2 of the report from a project adopted in local mode on Windows (part 1 is #1410, ADR-0593). A builder
found a defect of the kit itself, a guard refusing a seed run it should judge, and filed it as a plain issue among the
project's own work, because no brief, guide or skill names a channel for kit defects. The same day the project's steward
lost its read-only `gh api` calls after a change made through the runtime's `/doctor`, and only a restart brought them back
`(verify)`. On main at 476d4a7 the steward's guard allows those reads (they are GETs), so the loss was the session's
permission mode, not the kit's guard.

## Decision

1. A defect of the kit itself is one issue in the project's own repository labelled `agk-kit-defect`, never `agk-brief`.
   `python3 scripts/agk/steward_owner.py defect --title TEXT --file FILE [--refusals N] [--post]` drafts it: the title, the
   kit version (`version` of `agk.toml`), the operating system and shell, the reason codes and the newest N (5) lines of
   the refusal log of ADR-0593, each field redacted again by `guard_logs.redact`, what should happen instead (FILE) and
   `Who: AGK steward`. The outbound data guard (`steward_outbound.check`, ADR-0561) checks the title and body first and
   refuses, fail closed, with exit 2 and nothing posted. Without `--post` it prints the draft; with it, on the owner's
   word, it opens the issue. In personal mode it prints the draft and posts nothing. Nothing goes to the kit's repository
   by itself: the owner decides whether to pass a report on.
2. The plan never offers a kit defect: `session_plan.plan_briefs` leaves every issue labelled `agk-kit-defect` out of the
   open briefs it reads, even one that also carries `agk-brief`.
3. `steward_owner.py defects` prints one line per open kit defect, `kit defect #<n>: <title> (opened <date>)`, or
   `kit defects: none open`; a list it cannot read exits 4 and never says `none open`. The steward runs it at start.
4. The steward's guard allows the label `agk-kit-defect` on a new issue (`gh issue create --label` and a POST to
   `/issues`), and still denies it on an existing issue and denies `agk-brief`.
5. At start, and after any `/doctor` or settings change in the session, the steward checks one read,
   `gh api rate_limit`. `steward_owner.py reads [--session ID] [--refused]` prints `reads: ok`, or one line
   `reads: gh api refused (setting: <setting>); restore: <step>; meanwhile the steward reads through the kit's scripts`
   with exit 1, once per session (a marker beside the refusal log, never tracked). The setting is `gh on PATH`, `gh auth`
   or the token's access when `gh` itself fails; with `--refused` (the runtime refused the steward's own call) it is the
   `permissions.deny` or `permissions.ask` entry of `.claude/settings.local.json` or `.claude/settings.json` that names
   `gh`, else the session's permission mode `(verify)`, and the step is to restart the steward session. It names the
   setting, never the entry's value.
6. `doctor.py` writes nothing and never changes a session's permission mode or a `.claude/settings*.json` file; its
   docstring says so and a test reads its source and runs it against a project's settings files.

## Consequences

A builder or steward has one named place for a kit defect, kept apart from product work, and the owner sees the open
ones in one line each. A steward that loses its reads says why once and goes on through the kit's scripts. Protected
path classes changed: `.claude/` (`agents/steward.md`, `hooks/steward_guard.py`), `scripts/agk/` (`steward_owner.py`,
`session_plan.py`, `doctor.py`), `tests/kit/` (`test_kit_defect_report.py`) and `agk.toml` (the test map names the
new test file).

## Residual

- 2026-11-16: that a `/doctor` change in a session alters the permission mode it applies to later calls, and that a
  restart restores it, is the adopted project's report `(verify)`; the kit cannot read a session's permission mode.
- 2026-11-16: a builder that finds a kit defect drafts it with the same `defect` command (the local-mode guide says so);
  session rule 34, which sends a builder's unrelated bug to a `found-bug` issue, is the maintainers' text and is not
  changed here (Q-1411-1).
- 2026-11-16: in CI mode the refusal log belongs to the runner, so a defect drafted there has no refusal lines.
