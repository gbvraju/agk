# ADR-0726: Two steward runs never act at once and a run's work survives the next start (REQ-066)

- Status: Proposed
- Date: 2026-11-22
- Deciders: maintainers
- Related: ADR-0557, ADR-0708, SPEC-0059, brief #1741, plan #661
- Requirements: REQ-066

Protected classes this pull request changes: `scripts/agk/` (`steward.py`), `.claude/` (`agents/steward.md`) and
`tests/kit/` (`test_steward_memory.py`). `kit/hashes.json` is not edited by hand.

## Context

On 2026-11-22 the scheduled steward and the owner's chat steward acted at once under one session name (brief #1741).
`live_start` skipped a run of the starting name, counted 60 minutes from the `Started:` time only (a scheduled run lasts
up to 110 minutes), and a chat that resumed after an `Ended:` wrote with no `Started:` of its own. The notes, owner lists
and draft briefs the runs wrote were not memory kinds, so the next start named 51 comments by id and read none of them.

## Decision

1. Any live run refuses a start, whatever its name, the starting one included: `steward already running: <session>
   since <UTC time>; this start writes nothing` (exit 1, nothing written). A start with `AGK_STEWARD_START=conductor`
   also prints `stuck: steward <session> not started (steward already running: <other>)` (SPEC-0059 rule 2).
2. A run is live while the newer of its start and its beat is within 60 minutes. `refresh`, and `record` from the
   command line, edit the run's own `Started:` comment in place (one PATCH, no new comment) to `Started: steward
   <session> <start> beat <now>`; in personal mode the same line of the sidecar memory file. A malformed beat time is
   read as the start time alone. A start after a run whose last beat is older prints `previous run <session> ended
   without Ended (last beat <UTC time>)` and starts. A later `Started:` closes every earlier run, since a start is
   only written when no run is live. This changes ADR-0708's three GET calls of `refresh` to three GET calls and the
   beat's one PATCH, which is not printed as a change.
3. `steward.py record` and `steward.py end` refuse (exit 2, no call) naming `steward.py start` when this clone's cache
   holds no start of a run that has not ended. The scripts that call `record` as a function (`steward_owner.py`,
   `steward_voice.py`) are unchanged. The agent file says a chat runs `start` again at each resume and ends with
   `end`, within its word budget (`config/rule-budget.txt` unchanged).
4. `KINDS` gains `Note`, `Owner list`, `Morning list for the owner`, `Draft brief` and `Filed`, and the first-word
   pattern reads those multi-word kinds. The start's summary prints the newest owner list's and morning list's first
   line, every line of the newest `Note:`, and every line of each `Draft brief:` that no later `Filed:` names, from the
   comments it already read (SPEC-0059 rule 18: no new read).
5. A `Draft brief:` starts with its id (`F-<session>-<n>`), and its full text is the entry. A `Triage:` that says
   `draft for the owner` and names no recorded `Draft brief:` id is refused, naming the kind. A roll-over at 500
   comments carries every unfiled `Draft brief:` to the new memory issue, one comment each, beside the open owner
   questions.
6. `[steward] auto_file`, `review_mode`, `pr_mode` and `execution` are not read; no `agk.toml` key is added.

## Consequences

A chat and a scheduled run of the steward can no longer act at once, and a chat that resumes starts again first. A
long run stays live while it refreshes or records. What a run writes as a note, a list or a draft reaches the next
start without reading raw comments.

## Residual

- 2026-11-22: the owner taking over from a live scheduled run is not in this decision (Q-1741-2): the owner ends the
  run, or waits 60 minutes after its last beat.
