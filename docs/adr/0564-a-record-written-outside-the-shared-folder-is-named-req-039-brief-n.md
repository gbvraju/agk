# ADR-0564: A record written outside the shared evidence folder is named

- Status: Proposed
- Date: 2026-11-15
- Deciders: maintainers
- Related: brief #1329, brief #1269, brief #1281, ADR-0536, ADR-0542, plan #661
- Requirements: REQ-039

## Context

Brief #1329 found that `scripts/agk/prepush.py --record FILE` writes FILE wherever it is given and says nothing,
while the conductor's guard (`.claude/hooks/conductor_guard.py`, ADR-0542) lets it read a record only from the
clone's shared evidence folder (`<git common dir>/agk-evidence/`, ADR-0536) or its own scratch folder. In an
adopted project in local mode the builders wrote their records to a project folder outside the clone, and the
conductor's `evidence.py check --head` found nothing. `docs/guides/local-mode.md` let a session pass any FILE kept
outside the repository, and `docs/guides/getting-started.md` told the builder of a UI brief to run
`scripts/agk/design_compare.py`, a kit-only script no project has.

## Decision

1. When `--record FILE` names a file whose folder is not the clone's shared evidence folder, prepush still writes
   it and, after the `Evidence:` line, prints one line
   `prepush: record written outside the shared evidence folder; a conductor on this machine reads only that folder (option: --record with no FILE)`,
   naming the option, never the path. It changes no exit code, no step and no record field. With no FILE, or a FILE
   directly in the shared folder, nothing new is printed.
2. `docs/guides/local-mode.md` says a session on the conductor's machine runs `--record` with no FILE, and a
   session on another machine passes a FILE that is copied into the conductor's scratch folder or the shared
   folder before `evidence.py check <file> --head <sha>`.
3. `docs/guides/getting-started.md` names `design_compare.py` by the plugin's path
   (`${CLAUDE_PLUGIN_ROOT}/scripts/agk/design_compare.py`, or `/agk:design`), as `skills/design/SKILL.md` does,
   and says the script is kit-only and the conductor only reads the `Design match:` lines.
   `.claude/agents/conductor.md` is unchanged.

## Consequences

A record that the conductor on the same machine cannot read is named at the run that writes it. A record in the
conductor's scratch folder also gets the line, since prepush cannot know that folder; the line is advice and fails
nothing. Protected path classes changed: `scripts/agk/` (`prepush.py`) and `tests/kit/` (`test_prepush_record.py`).

## Residual

- 2026-11-15: a record copied into the conductor's scratch folder by hand still gets the line at the run that wrote
  it elsewhere; the guide says to copy it, and no check reads the line.
