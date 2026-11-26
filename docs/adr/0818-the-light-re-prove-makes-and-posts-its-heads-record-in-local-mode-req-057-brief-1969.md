# ADR-0818: In local mode the light re-prove makes and posts the record of the head it makes

- Status: Proposed
- Date: 2026-11-26
- Deciders: maintainers
- Related: SPEC-0050, SPEC-0039, ADR-0495, ADR-0713, ADR-0725, ADR-0542, ADR-0629, ADR-0528, ADR-0684, ADR-0327, amendment 171, amendment 216, amendment 253, brief #1969, plan #661
- Requirements: REQ-057

Protected classes: `scripts/agk/`, `.claude/`, `tests/kit/`

## Context

In local mode (`execution = "local"` on the default branch, or the open `Local mode since` issue) the merger needs the
latest verdict to name `Local evidence: <head>` and `Evidence check: agrees, head <sha12>` (SPEC-0039 rule 4). The
light re-prove of SPEC-0050 rule 7a (`conductor.py reprove --apply`) makes a new head with `update-branch` but no
record, so every first verdict on it was a fix list or a builder restart that only asked for one: 0 of 32 light merges
from 2026-11-18 to 2026-11-26, median 24 minutes each (brief #1969's measurement).

## Decision

1. **The record step.** In local mode, as `merge_cleared.local_mode` reads the default branch as last fetched and the
   open issues, `reprove --apply`, after it reads the new head, fetches it, adds a detached scratch worktree at it under
   `<git dir>/agk/reprove-<n>`, writes the pull request body to a file beside (not inside) it, and runs the head's own
   `prepush.py --quick --record --body <file>` there under `env -i` with only `PATH` and a scratch `HOME` beside the
   worktree, as the bounded governance run does, so the head's code never sees the conductor's credentials (the record
   goes to the clone's shared evidence folder; prepush holds the heavy lock itself). Then the conductor's own
   `evidence.py check --head <new> --body <file>` (`kit_root.kit_dir` of its checkout of the default branch, ADR-0542)
   checks it, and its `record` digest must equal the `Evidence:` line's. The worktree, the body file and the scratch
   `HOME` are removed in every case.
2. **The Report carries it.** On a passing run whose check agrees, the one `Report: <new head> merge of main (light
   re-prove, SPEC-0050 amendment 171)` comment gains the `Evidence:` line, one line `Local evidence: <new head>
   <the Evidence check line> (the conductor's light re-prove record)` and the record byte for byte in one fenced `json`
   block, the builders' form (ADR-0713). The command prints the same `Local evidence:` line. Nothing is posted before
   both runs end.
3. **The verdict reads it.** `.claude/agents/conductor.md` says that on a head the conductor's light re-prove made, the
   `Local evidence:` line of that `Report:` stands for the builder's line. `merge_cleared.local_evidence` is unchanged.
4. **A failure goes back to a builder.** A failed prepush step, no gitleaks, a body line `Secret-scan: deferred to CI`
   (Q-1713-2), `Evidence check: differs` or a different digest, or any failure after the update (the git folder,
   the worktree, a write or the kit's resolution): the Report is posted with one line
   `Local evidence: none (<step or reason>)` and no record, and the command exits 3 so the sweep's re-prove handover
   (ADR-0725) restarts a builder. The reason names a step or a setting, never a value or an output.
5. **Settings.** `hosted`, `hybrid` or `pool` with no record issue: today's Report, no prepush. Another `execution`
   value: refused before the update with `merge_cleared.EXECUTION`. `paused = true` on the default branch: `reprove:
   agk paused; nothing updated`. `forge = "files"` (personal mode, top level or `[personal]` of the checkout): refused
   naming `forge` before any GitHub read. `[flow] shared_indexes` still decides light against full. No new key.
6. **Edge cases.** The head moves again before the post: nothing is posted, the line says `head moved`, exit 3. Two
   light merges in a row each make their own record. The notes ref is not pushed (ADR-0629: the conductor reads its
   own shared folder).

## Consequences

In hosted mode nothing changes. In local mode the conductor-made head has its record and evidence check before any
verdict, the same gate as a builder's head, at the cost of one quick prepush and one evidence check on the conductor's
machine per light merge. No workflow, label, ruleset or required check changes.

## Residual

- 2026-11-26: the rule text of SPEC-0050 rule 7a changes only by amendment 253, applied by the maintainers.
- 2026-11-26: refusing a builder's local-mode ready `Report:` with no record is not done here (`Q-LR-4`).
