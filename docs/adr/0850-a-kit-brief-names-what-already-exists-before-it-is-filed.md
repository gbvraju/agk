# ADR-0850: A kit brief names what already exists before it is filed

- Status: Proposed
- Date: 2026-11-27
- Deciders: maintainers (the owner's yes on brief #2052, 2026-11-27T19:12:09Z)
- Related: ADR-0752, ADR-0756, ADR-0757, ADR-0758, ADR-0774, ADR-0828, SPEC-0030, REQ-037, brief #2052, plan #661
- Requirements: REQ-037

Protected classes: `scripts/agk/`, `skills/`, `tests/kit/`, `agk.toml`

## Context

The brief study (ADR-0752) reads documents, never code: `brief_study.candidates` searches `docs/adr`, `docs/specs`,
`docs/runs` and the open briefs for the code paths of `Touches:` and `Wiring:`. No function, setting or script that a
brief's Sentence or Answers name is looked up under `scripts/`, so a brief can propose what a script already does and
pass with only `Prior:` warnings. No study line asks what already exists. `check_brief.brief_result` is the one reading
every writer calls (ADR-0756), so a rule added to the study reaches the check, the steward's `file-brief` and
`fix-brief`, `plan_intake.py publish`, the triage and, through `brief_study.study_failures`, the plan's shape.

## Decision

1. **The line, in the kit only.** With `kit/agk-kit.mk` under the root (`brief_study.KIT_MAKE`, which
   `check_brief.KIT_MAKE` now reads), a brief has exactly one line `Existing:` before its Answers line: `Existing:`
   alone followed by items `- ...` up to the first blank line, each naming a `<path>:<line>` of a file in the tree
   (the line between 1 and the file's length) and holding `not enough: <reason>`; or `Existing: none: <text>` holding
   a backquoted command that starts `grep`, `git grep`, `rg` or `brief_study.py` and a `<n> match(es)` count. Each
   break is one `study:` problem naming the line or, for a reference, the path's folder, never the brief's text. It is
   held as the other study lines: a warning before `[flow] brief_study_fails_from`, a failure for a brief filed on or
   after it (`enforced`); the render's placeholder `Existing: none: (verify) for the person to state` is warned on
   any day and never failed; a `Priority: 0` brief is not held.
2. **The code search, warnings only.** `brief_study.code_matches(body, root)` takes the backquoted spans of the
   `Sentence:` line and the Answers items and the code paths of `Touches:` (`agk.toml` and `kit/hashes.json` are no
   term), in three classes: a script (`<name>.py` or a path ending `.py`), a function (`<module>.<name>`, `<name>(`)
   and a setting (`[<table>] <key>` or `<table>.<key>`, the table a key of `config.TABLE_KEYS`). It finds, in files
   under `scripts/**/*.py` and `.claude/hooks/*.py`, the script's file, the function's first defining line, and the
   setting's line in `agk.toml`, else the first line of `scripts/agk/config.py` that holds the key in quotes. A match is
   named when the `Existing:` section holds its path or file name; under `none:` none is. `study_result` warns
   `study: Existing leaves out <path>:<line>, which defines <term>` for at most `CODE_WARNINGS = 10` with one line
   counting the rest, on any day, never failing; `brief_study.py FILE --root DIR` prints each match as
   `code <path>:<line>: <term>`. The search is in `study_result` only, never in `study_problems`.
3. **Projects are not held (Q-P0A-1).** Without the marker the line is neither required nor read and the code is not
   searched: no project gains a warning or a failure. The template and the brief skill show the line to every writer,
   as required in the kit and optional in a project; `plan_intake.py render` writes the placeholder before the Answers.
4. **No setting is added.** `[flow] brief_study_fails_from` (Q-P0A-3) and `[flow] brief_prior_warnings` keep their
   meaning; the code warnings have their own fixed cap (Q-P0A-2). The `[[testing.map]]` entry of `brief_study.py`
   names `tests/kit/test_brief_existing.py`. `fix-brief` may not add the line: it is not a `MECHANICAL` line.

## Consequences

A kit brief that rebuilds an existing function, setting or script is warned on its draft, and from the study day one
that names nothing that exists, and no search, fails in every writer. The check reads form only: it cannot tell that a
`none:` search was run or wide enough (Q-P0A-4), so the code search still warns every match under `none:`. A brief
check in the kit reads more files; the plan's shape reads only the line.

## Residual

Extending the line to a project's briefs needs its own ADR (2026-12-31).
