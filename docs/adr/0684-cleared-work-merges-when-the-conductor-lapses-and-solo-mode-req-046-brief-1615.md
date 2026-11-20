# ADR-0684: Cleared work merges when the conductor lapses, and this repository runs in solo mode (REQ-046, REQ-069)

- Status: Proposed
- Date: 2026-11-20
- Deciders: maintainers
- Related: SPEC-0039 (amendment 212), ADR-0266, ADR-0330, ADR-0368, ADR-0373, ADR-0570, ADR-0654, brief #1615, plan #661
- Requirements: REQ-046, REQ-069

Protected classes this pull request changes: `agk.toml` (`review_mode = "solo"` and `[flow] conductor_lapse_minutes =
30`), `scripts/agk/` (`merge_cleared.py`, `config.py`) and `tests/kit/` (the new `test_merger_lapse.py` and one case of
`test_merger_sweep.py`). No workflow, ruleset, `constitution/` or `config/reviewers.yaml` change. `kit/hashes.json` is not
edited by hand: `kit_hashes.py` reports it current.

## Context

On main at d3b9e70 (2026-11-20) `agk.toml` reads `review_mode = "team"`, `execution = "local"`, `[flow] auto_merge =
true` and `plan_issue = 661`. In local mode `merge_cleared.py` `github_mode` raises `Nothing`, so `--sweep-gate` prints
`off`, `sweep_allows` returns False and `sweep_one` prints only `local mode: the conductor merges`: a cleared head waits
for the next conductor run. The conductor's lease on the plan issue lapses `LEASE_MINUTES` (10) after its last renewal
(`conductor.lease_holder`). On 2026-11-20 two owner-answered pull requests (#1579, #1576) stayed unmerged for four hours
after the 12-hour conductor run ended. SPEC-0039 rules 2 and 4 say that in local mode the conductor merges; the merger
job is not a session (session rule 30 binds sessions), so the change is an amendment of the spec (amendment 212).

## Decision

1. **The setting.** `[flow] conductor_lapse_minutes` (`config.TABLE_KEYS`): absent is off, today's behaviour; a whole
   number from 15 to 1440 is the wait; anything else is refused with `conductor_lapse_minutes of the flow table must be a
   whole number from 15 to 1440`, naming the setting and never the value (`merge_cleared.lapse_setting`, also read by
   `ruled`, so the guarded command refuses a malformed value too).
2. **The lapse.** `lapsed(data, repo, now, authors)` reads the plan issue's comments and is True only when
   `conductor.lease_holder` finds no holder and the newest `Conductor:` marker by a listed verdict author ended at least
   the setting's minutes ago (an active lease ends `LEASE_MINUTES` after its stamp, a released one at its stamp). No
   setting, no plan issue, no marker, a bad stamp or comments that cannot be read are never a lapse. A held but stalled
   lease (`lease_stall`) is held, so it is not a lapse.
3. **The sweep.** In local mode with the setting on, auto-merge on and not personal mode, `--sweep-gate` prints `on`;
   the sweep reads the open issues and the lease and, only when the local-mode record issue is closed and the lease has
   lapsed, runs the guarded command with the lapse flag on each cleared head (`sweep_allows` returns True). Otherwise it
   prints `local mode: the conductor merges` as today.
4. **The guarded command under a lapse.** Under `merge_lock` it reads the lease again and holds with `the conductor's
   lease is not free (setting: flow.conductor_lapse_minutes)` when a conductor came back. It holds while the local-mode
   record issue is open. It needs both kinds of evidence of rule 4 (`lapse_evidence`): the verdict's `Local evidence:`
   with `Evidence check: agrees` for the head (`local_evidence`) and every `required_checks` name green on GitHub for that
   head (`ci_evidence`, so a pending check holds as `checks pending`, rule 10). Every other hold of rules 3 to 7 applies
   as before. Its record line ends ` merged by the sweep after a conductor lapse`.
5. **Owner-only holds stay.** A release or a protected class (`OWNER_HOLDS`) is still lifted only by
   `merge_cleared.py --pr <n> --owner`; the sweep's `UNMERGED` line for such a hold ends `; the owner merges with
   python3 scripts/agk/merge_cleared.py --pr <n> --owner`.
6. **`AGK_MERGER`.** `merger_variable_line` no longer offers `AGK_MERGER = off` while the lapse rule is on, since the
   scheduled jobs carry the lapse sweep.
7. **This repository.** `agk.toml` gets `review_mode = "solo"` (the owner's word of 2026-11-20 on brief #1615) and
   `[flow] conductor_lapse_minutes = 30`. Solo mode adds the one person's `Confirmed:` path
   (`reviewers.confirmed_comments`); the conductor's verdicts still count, and `reviewers.solo_problems` finds nothing to
   refuse (one person in `spec_approvers`).

## Consequences

- Hosted, hybrid and pool execution: no change; the merger already merges and the setting is read but changes nothing.
- Local mode: the sweep merges a cleared, green head after a lapse. Personal mode (`forge = "files"`): nothing merges.
  Solo and team read the same rule; strict and flow are unchanged.
- The gate job holds no token, so it cannot read the lease: with the setting on in local mode the sweep job starts on
  every scheduled run and reports only while a conductor holds the lease (one billed minute each).
- GitHub drops some scheduled runs (three merger runs in 24 hours were observed), so a lapse merge may come hours late.
- A project using AGK gets the setting off (absent) through `/agk:upgrade`; turning it on is an ADR, as for every key of
  `agk.toml`.

## Residual

- 2026-11-20: amendment 212 of SPEC-0039 (`docs/runs/proposed-spec-amendments-212.md`) writes the rule into the spec on
  the owner's `Approve: SPEC-0039`; until then this ADR is the decision (`Q-1615-1`).
