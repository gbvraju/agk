# Proposed spec amendments 212 (SPEC-0039; REQ-046)

Date: 2026-11-20 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0684 (brief #1615), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0039-the-conductor-merges-a-cleared-pull-request-through-one-guarded-command.md` (rules 2, 4 and 9). Brief
#1615 reserved amendment 212. This file proposes the lines and does not edit the spec. A later pull request applies them
word for word, on a person's `Approve: SPEC-0039` on it; no session posts it.

The sentence (brief #1615): "This repository runs in solo mode, and in local mode the merger's sweep merges a cleared,
green head once the conductor's lease has been free for `[flow] conductor_lapse_minutes`, so cleared work no longer waits
for the next conductor run."

## What is on the default branch today

Read in the code by this session on main at d3b9e70 (2026-11-20): `merge_cleared.py` `github_mode` raises `Nothing` for
`execution == "local"`, `sweep_gate_main` prints `off`, and `sweep_one` prints `local mode: the conductor merges`;
`conductor.lease_holder` gives no holder `LEASE_MINUTES` (10) after the lease's last renewal.

## Items

1. **Rule 4, a new paragraph after the first.** "In local mode with `[flow] conductor_lapse_minutes` set (a whole number
   from 15 to 1440; absent is off; anything else is refused naming the setting), the merger's sweep also runs the command
   of rule 2 once the conductor's lease on the plan issue (`[flow] plan_issue`) has had no holder for that many minutes
   past its end. Such a merge needs both the verdict's `Local evidence:` with `Evidence check: agrees` for the head and
   every check of `required_checks` green on GitHub for that head; it is never made while the local-mode record issue is
   open; the command reads the lease again under its lock and holds when a conductor holds it; no plan issue, no lease
   marker or comments that cannot be read are never a lapse; and its record line of rule 7 ends `merged by the sweep
   after a conductor lapse`. The holds of rule 5 apply as before, and a release or a protected class waits for the
   owner's `--owner` merge, which the sweep's line names."
2. **Rule 2, last sentence.** After "the command runs once per clearing and ends." add: "The one other caller is the
   merger's sweep after a conductor lapse (rule 4)."
3. **Rule 9, last sentence.** After "Inbound webhooks to a local machine are out of scope (`Q-S0039-13`)." add: "In
   local mode with the lapse setting on, the merger's scheduled sweep is the retry once the conductor has lapsed (rule
   4); its workflow does not change."
