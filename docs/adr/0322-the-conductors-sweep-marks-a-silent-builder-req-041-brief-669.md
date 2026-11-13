# ADR-0322: The conductor's sweep marks a silent builder (REQ-041, brief 669)

- Status: Accepted
- Date: 2026-11-06
- Deciders: maintainers
- Related: ADR-0308, SPEC-0034, SPEC-0030
- Requirements: REQ-041

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

On 2026-11-06 the builder b649 ended before it pushed anything, and it was noticed hours later, when
a person asked (brief #669; issue #490 asks for this). A take (`taken: <id> <date>`, SPEC-0034 rule
5) holds a brief for `claim_hours` (4 by default) whether or not its session is alive, so a dead
builder blocks the brief until the take expires. The conductor's sweep (ADR-0308) read only open
pull requests, and a builder that dies before its first push has none.

## Decision

1. **The SILENT line.** `conductor.py sweep`, after its other lines, prints `SILENT <brief>
   <session> <minutes>; re-fire: Session name: <session>. Item: brief #<brief>.` for each open
   `agk-brief` issue whose newest live take (`session.live_takes`) is more than `silent_minutes`
   minutes old, when there is no branch `claude/brief-<n>`, no open pull request that names the
   brief (its `Brief: #n` line or that branch as head), no pull request naming it created after the
   take, and no comment on the brief whose first line starts `Progress:`, `Report:` or `Question:`
   after the take.
2. **The take's time.** The minutes are counted from the take comment's `created_at`, which GitHub
   stamps to the second; the line `taken: <id> <date>` keeps its format, so `facts.py`,
   `session_plan.py` and every reader of a take are unchanged (Q-669-1).
3. **Never SILENT.** A brief with any comment whose first line is `Report: ... escalate` is never
   listed; a released or expired take is not live and is never listed.
4. **The setting.** `silent_minutes` of the `[flow]` table of agk.toml, a whole number, 1 or more,
   30 by default. This repository does not set it.
5. **It fires nothing.** The sweep stays GET only, posts nothing and starts no session; the
   conductor re-fires the session with the printed line (the payload form of a builder's scheduled
   task), as its own rules allow. The guard's allowed form of `sweep` is unchanged.
6. **Reads.** Each open `agk-brief` issue costs one GET of its comments; a brief past the threshold
   with no sign of life costs one GET of `git/matching-refs/heads/claude/brief-<n>`, and the first
   such brief one GET of every pull request (`state=all`), read once per sweep. A read that fails
   ends the sweep with `cannot be read`, never with a SILENT line.

## Consequences

A builder that dies before its first push shows within one sweep after `silent_minutes`, instead of
when a person asks or when its take expires. The sweep reads one more GET per open brief. A builder
that only asked a `Question:` on its brief is waiting there (session rule 21) and is not listed.
SPEC-0034 rule 5 gains the line by amendment 134.

## Residual

- 2026-11-06: Q-669-1, whether the take line itself must carry the time (the brief: "add the time if
  it is missing"); read as the comment's creation time, the conservative reading that changes no
  reader of a take.
- 2026-11-06: Q-669-2, a `Question:` after the take counts as a sign of life beside `Progress:` and
  `Report:`, so a waiting builder is not re-fired twice; the conservative reading.
