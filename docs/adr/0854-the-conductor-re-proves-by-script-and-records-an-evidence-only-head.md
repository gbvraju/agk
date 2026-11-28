# ADR-0854: The conductor re-proves by script and records an evidence-only head

- Status: Proposed
- Date: 2026-11-27
- Deciders: maintainers
- Related: SPEC-0050, SPEC-0039, ADR-0495, ADR-0818, ADR-0554, ADR-0585, ADR-0725, ADR-0631, ADR-0607, ADR-0327,
  amendment 171, brief #1163, brief #1969, brief #2056, plan #661
- Requirements: REQ-057

Protected classes: `.claude/`, `scripts/agk/`, `tests/kit/`, `agk.toml`

## Context

The light re-prove of SPEC-0050 rule 7a (`conductor.py reprove`, ADR-0495) and its local-mode record (ADR-0818) are
built, but the conductor's guard denies the command (`Q-1163-1`) and no pass calls it, so a light re-prove or a head
that lacks only its evidence record became a fix list for a builder: 26 of 115 verdicts on 32 kit pull requests from
2026-11-25 to 2026-11-27 asked only for that re-run (brief #2056's measurement). The owner said yes on
2026-11-27T19:12:25Z (brief #2056).

## Decision

1. **The guard admits the form (answers `Q-1163-1`).** `conductor_guard.routine_form` admits exactly
   `conductor.py reprove --pr <n>` with nothing, `--apply`, `--record` or `--record --apply` after it, through
   `own_script` (the plugin form of ADR-0631 included). The update-branch `PUT` stays the script's own call; no
   `gh api` `PUT` is admitted to the session and the `deny` entries of `.claude/settings.json` stay. Shadow mode admits
   none of them. No `prepush.py` form is admitted to the conductor's session.
2. **The supervisor runs it.** `watchdog_pass`, holding the lease, with no stop reason, the kit not paused and no
   `The default branch is red` issue open, calls `reprove(root, n, apply=True)` once per pull request and head for each
   `re-prove: #<n> ... light` line of the sweep, keeps `{n: head}` of its last try in the pass state, and prints
   `watchdog: reprove #<n>: <its last line>`. It starts no model. An exit 3 is left to the re-prove handover
   (ADR-0725); an exit 1 is printed and the pass goes on.
3. **The record counts.** `merge_cleared.local_evidence` is unchanged; a verdict that carries the `Local evidence:`
   and `Evidence check: agrees` lines of the conductor's Report for the head passes SPEC-0039 rule 4.
4. **The evidence-only record.** `reprove --pr <n> --record [--apply]` runs only in local mode, on a head not in the
   re-prove state, with no agreeing `Local evidence:` line for that head, and only when (a) the pull request's author
   posted an `Evidence:` line naming that head, or (b) the head's tree equals the tree of an earlier head of the same
   pull request that has an agreeing `Local evidence:` line. With `--apply` it runs ADR-0818's record on the head
   itself, with no update-branch, and posts `Report: <head> evidence record (the conductor's evidence record)` with
   the `Evidence:` line, `Local evidence: <head> <check line> (the conductor's evidence record)` and the record. With
   neither (a) nor (b) it prints `the builder records it (rule 4)` and exits 3 (`Q-RP-1`): new code is first proved by
   its author. In hosted mode `--record` is refused naming `execution`; an evidenced head prints `nothing to record`.
5. **The role file.** `.claude/agents/conductor.md` runs `reprove --pr <n> --apply` on a light `re-prove:` line and,
   in local mode, `reprove --pr <n> --record --apply` on a head whose record alone is missing, before any fix list
   that would ask only for that.
6. **The class stays closed.** Every conductor-made record comes from `reprove_record` and carries one of the two
   notes. No new key in `agk.toml`; its `[[testing.map]]` entries gain the new tests.

## Consequences

A light re-prove or an evidence-only head reaches the merger without a builder round trip, at the cost of one quick
prepush and one evidence check on the conductor's machine per case. In hosted mode only the update-branch and its
Report are made. This pull request changes the conductor's own guard, so it is not cleared by the conductor alone and
merges only on the owner's recorded yes (`Q-RP-2`). No workflow, label, ruleset or required check changes.

## Residual

- 2026-11-27: widening the evidence-only record to a head its author never recorded waits for the owner (`Q-RP-1`).
- 2026-11-27: ADR-0818's residual on `env -i` (the same user can still read that user's files) holds here too.
