# ADR-0361: Every brief and spec states its contexts, and the owner can hold a brief

- Status: Proposed
- Date: 2026-11-09
- Deciders: maintainers
- Related: amendment 142, brief #775, SPEC-0030, SPEC-0021
- Requirements: REQ-037

## Context

Brief #773 was written for AGK's own repository only, and the owner had to ask how the same work runs for projects with
front end, back end and mobile tests. Nothing in AGK asks that question, so it depends on someone remembering it. The same
day the owner said "Wait, keep a note" about #773, and AGK had no way to hold a brief: `session.py plan` still offered it,
and only a comment stood between it and a builder (owner direction quoted as data in brief #775, 2026-11-08).

This build changes the protected path classes `scripts/agk/`, `tests/kit/`, `tests/kit_dev/` and `.claude/` (the
conductor's report and review lines).

## Decision

1. A brief has exactly one line `Contexts:` stating every context of `kit`, `github`, `local`, `personal` and `stacks`,
   each with how the change works there or `not applicable: <reason>`. Entries are `<names> (<how>)` or `<names>: <how>`,
   separated by top-level semicolons, and names may be grouped (`github, local and personal`). `check_brief.py` refuses a
   brief without the line or with a context missing, naming the rule and the fixed context name, never the text. The
   router's red-branch brief (SPEC-0032 rule 7) is a fixed repair and needs none.
2. `check_specs.py` does the same for a `## Contexts` section, on a new spec, a spec whose status changes and an amended
   Approved spec. A spec Approved before this rule and left unchanged is not refused.
3. The conductor's review answers the line against the diff: a change of behaviour in a context marked `not applicable`
   is a fix list item citing SPEC-0030 rule 4 (`.claude/agents/conductor.md`). A numbered item, it is never a covered fix
   list (SPEC-0021 rule 1).
4. A comment on a brief by a person in `spec_approvers` whose first line is `Hold: #<brief> <reason>` makes `session.py
   plan`, `next` and `claim` skip the brief with `held by the owner: <reason>`; a later `Release: #<brief>` by an approver
   ends it. The latest such line by an approver decides. A held brief is never freed by a stale take.
5. `session.py plan` prints one `HELD:` line for each held brief and one `HOLD IGNORED:` line for each `Hold:` by someone
   not listed, which names the login; the conductor's report carries both. The JSON has `held` and `ignored_holds`.

## Consequences

Every open brief needs a `Contexts:` line once this merges, so the repair of brief #775 answer 4 goes first. A new spec is
refused until it has its section; `docs/specs/TEMPLATE.md` and `docs/briefs/TEMPLATE.md` are unchanged (`Q-775-2`). The
hold is one more read of comments the plan already fetches, so it adds no request. The hold is read only by the three
`session.py` commands.

## Residual

- 2026-11-09: a brief the plan does not read comments for (stale, parked or malformed) is not listed as held until it is
  otherwise skippable; such a brief is not offered anyway.
- 2026-11-09: `next` still offers a stalled pull request of a held brief for takeover (`offer_stalled`); the hold stops a
  new take only (due 2026-12-31).
- 2026-11-09: a session posts under the owner's account, so GitHub cannot tell a `Hold:` it posted from the owner's own,
  as with `Confirmed:` (session rule 29). No session rule yet forbids it (the rule budget does not allow one here); the
  builder of this brief posted none (due 2026-12-31).
- 2026-11-09: personal mode has no `plan`, `next` or `claim`, since `session.py` reads only GitHub, so no brief-file hold
  is built (`Q-775-1`).
