# ADR-0353: One live conductor at a time, by the kit's lease on plan #661 (REQ-037)

- Status: Proposed
- Date: 2026-11-08
- Deciders: maintainers
- Related: ADR-0330, ADR-0341, SPEC-0030, SPEC-0039, plan #661
- Requirements: REQ-037

Protected classes: `agk.toml`

## Context

ADR-0330 gave the kit `conductor.py lease`: one marker comment on the plan issue that `[flow] plan_issue` names, valid
50 minutes; `merge-queue` refuses while another name holds it. This repository never set `plan_issue`, so `lease --show` printed `lease: off`, and the one-conductor rule lived only
as free text in the scheduled conductor's prompt. On 2026-11-08 that text first blocked a needed takeover and was then
removed, and two conductors ran at once, which SPEC-0030 and SPEC-0039 say is not designed or detected.

## Decision

1. This repository's `agk.toml` sets `plan_issue = 661` in `[flow]`, the plan issue the conductor already reports on.
2. A conductor takes the lease (`conductor.py lease --take <name>`) before it acts, renews it while it works, and
   releases it when it ends; a run that finds another valid holder does nothing but report. The rule is the kit's
   command, not prompt text.

## Consequences

- `lease --show` reads the real holder; `merge-queue` refuses while another name holds the lease; a conductor that runs
  `lease --take` first and stops on exit 3 never works beside another.
- A takeover is one command: the holder releases, or the lease expires after 50 minutes.

## Residual

- `merge_cleared.py`, the conductor's single merge path, reads no lease; only `merge-queue` and a conductor that takes the
  lease first respect it, so two conductors that skip `lease --take` could still both merge (each merge is still pinned to
  its cleared head).

- A lease held by a session that died stays valid until it expires (at most 50 minutes); the owner can end it sooner by
  editing the marker to `Conductor: released`.
