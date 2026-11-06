# Proposed spec amendments 134 (SPEC-0034; REQ-041)

Date: 2026-11-06 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0322 (brief #669), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0034-a-team-sets-how-many-builder-sessions-run-at-once-and-agk-ha.md`. The number 134 is the one reserved for
brief #669 in the brief. This amendment is applied to the spec text in the same pull request. It needs a person's
`Approve: SPEC-0034` on the pull request; no session posts it.

1. **SPEC-0034 rule 5 (the claim).** The time of a take is its comment's creation time; the `taken:` line keeps its
   format. `conductor.py sweep` lists a brief whose newest live take is older than `[flow] silent_minutes` (30 by
   default), with no branch `claude/brief-<n>`, no pull request naming it open or created after the take, and no
   `Progress:`, `Report:` or `Question:` comment after the take, as `SILENT <brief> <session> <minutes>` with the line to
   re-fire it. A brief with a `Report: ... escalate` comment is never listed. The sweep fires nothing.
2. **Tests.** The Tests line of rule 5 gains: a silent take is listed, and a fresh take, a branch, a pull request, a
   post after the take, an escalation and a release are not.
