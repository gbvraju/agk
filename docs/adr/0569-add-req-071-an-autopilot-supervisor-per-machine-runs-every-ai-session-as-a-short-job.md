# ADR-0569: Add REQ-071: An autopilot supervisor per machine runs every AI session as a short job

- Status: Proposed
- Date: 2026-11-15
- Deciders: maintainers
- Related: SPEC-0064, SPEC-0058, SPEC-0059, SPEC-0062, SPEC-0063, SPEC-0041, ADR-0525, ADR-0554, ADR-0568, brief #1355, brief #1310, brief #1357, plan #661
- Requirements: REQ-071

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-15:

> Intake for AGK autopilot: one supervisor script per machine starts and stops every session, every AI session is a short job that ends, and one setting turns it on, the same in local, CI and personal mode, solo or team.

The brief is issue #1357, under plan #661. On the default branch at 5f22808, five actors can start a session (the
conductor's review pass through `launch.py`, the cloud launcher tasks, `conductor.py watchdog`, the steward's and the
conductor's starts of SPEC-0059 rule 2, and the person), builders keep their session for the life of their pull request and
wait inside it (`kit/templates/runtime/builder.txt`, session rules 10 and 18), the Windows adapter opens a terminal tab per
session, and each mode has its own mechanism. Brief #1355 (ADR-0568) added a process record per session and the watchdog's
builder checks. SPEC-0058 (Approved, unbuilt) describes a long-running dispatcher with short jobs per item.

## Decision

1. REQ-071 is added to `docs/requirements.md` as `planned`, and SPEC-0064 as `Draft`. Merging this pull request approves
   the requirement as a proposal; the spec stays `Draft` until a spec approver's own `Approve:` line approves it.
2. One supervisor per machine, a script with no model (`conductor.py watchdog --pass`, grown), run by the machine's
   scheduler or, in CI mode, by the cloud launcher task, is the only starter and stopper of session processes, apart from
   the steward a person opens; the conductor decides and the supervisor does it.
3. Every AI session is a short job that ends: a review pass, a builder job from take to ready and then one per fix list,
   a steward answer pass. No session waits on GitHub; the supervisor starts the next job on its event.
4. One setting, `[autopilot] mode = "off" | "assist" | "on"`, read in place of `auto_start`, `launch_adapter`, `[capacity]`
   and the watchdog's task after one release; a daily budget that is relaxed by default; crash-loop back-off; health
   figures in the user's temp folder; stop rules said once; the same rules in local, CI and personal mode, solo or team.
5. SPEC-0064 does not edit SPEC-0058: it reuses that spec's job kinds and per-kind limits, and whether SPEC-0058's unbuilt
   builds are withdrawn is left to the maintainers (SPEC-0064's fifth open question).
6. This ADR names the protected classes of this intake only. Builds (b), (c) and (d) change decisions held elsewhere
   (`.claude/agents/conductor.md`, session rules 10 and 18 in `config/`, `builder.txt` in `kit/`, the `[autopilot]` table in
   `agk.toml`), so each writes its own ADR. Builds (a), (e) and (f) will change `scripts/agk/`, `tests/kit/`,
   `tests/kit_dev/` and `kit/`; each may cite this ADR with `Covered-by: ADR-0569` once it is Accepted only if it changes
   no other class and no decision named here (session rule 36). No build changes a workflow file (`.github/`), the ruleset
   or `config/reviewers.yaml`; `kit/hashes.json` and the version stay the release's (session rule 14).

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval. Nothing that runs changes in this pull
request: the supervisor, the job record and the setting are built by SPEC-0064's builds (a) to (f).

## Residual

None beyond SPEC-0064's residual. The intake checks cannot tell whether the rules are the right ones; that is the review
of this pull request.
