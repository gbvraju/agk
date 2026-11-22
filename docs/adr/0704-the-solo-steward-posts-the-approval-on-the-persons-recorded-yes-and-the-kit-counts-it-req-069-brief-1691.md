# ADR-0704: The solo steward posts the approval on the person's recorded yes, and the kit counts it

- Status: Proposed
- Date: 2026-11-22
- Deciders: maintainers
- Related: brief #1691, brief #1690, ADR-0661, ADR-0703, ADR-0179, ADR-0546, SPEC-0062, amendment 194, Q-1691-1, Q-1691-2, Q-1691-3, plan #661
- Requirements: REQ-069

Protected classes this decision changes: `.claude/`, `scripts/agk/`, `config/`, `CLAUDE.md` and `tests/kit/`.

## Context

ADR-0661 decisions 6 to 8 name build (b): the guard's allowed forms, the readers' `Who:` reading and the session rule 29
sentence. Build (a) (brief #1690, ADR-0703) writes the `Approve:` and `Confirmed:` bodies but only prints them, because
`.claude/hooks/steward_guard.py` denies those first lines in every mode and no reader drops the `Who:` line.

## Decision

1. **The post.** In solo mode (`review_mode = "solo"`, one person listed), `steward_owner.py approve` posts the
   `Approve:` and `Confirmed:` bodies it writes with `-F body=@<file>`, the same way as the `Maintainer answer:` forms.
   In team mode it refuses them, naming `review_mode`, until the kept login of SPEC-0063 rule 4 is built (Q-1691-1).
2. **The read-back.** Right after the post, `approve` reads the comment it posted: when GitHub marks it with an app of
   `agent_apps`, it prints `this approval does not count: it was posted through an agent app (setting: agent_apps)`
   and the exact body to paste, and records that in the `Decision:` note; nothing is deleted. In a session with
   `common.REMOTE_RUNTIME` set it still prints the body and posts nothing, as SPEC-0062 rule 13 says (Q-1691-3).
3. **The guard.** `steward_guard.py` allows a first line `Approve:` and, in solo mode, `Confirmed:` only in a body read
   from a file whose last line is `Who: ProductOwner` and which holds one `Owner said (<UTC>): "…"` and one
   `Asked (<UTC>): "…"` line; a typed body, a body missing one of them, team mode, solo mode with nobody or two people
   listed, and `AGK_STEWARD_START=conductor` stay denied, each naming the setting. `Verdict:`, `Final:`, `Correction:`
   and `Merge:` as a first line stay denied in every mode. The conductor's guard is unchanged.
4. **The readers.** `reviewers.py` reads each comment as posted without the runtime's footer and its last `Who:`
   line (`common.without_who`), with CRLF read as LF. A comment with no `Who:` line counts as today. One with a `Who:`
   line counts only when it is `Who: ProductOwner` and holds both quote lines; any other `Who:` line, `Who: AGK…`
   among them, approves nothing. The quote lines are not part of a confirmation's verdict. `via_agent` is unchanged.
   This changes ADR-0546 decision 4 for approvals only, as SPEC-0062 rule 13 says.
5. **The rules.** Session rule 29 gains the sentence of ADR-0661 decision 6 with `approve` for `confirm`; its summary
   in `config/core-rules.md` and `CLAUDE.md` item 2 gain "(the solo steward's recorded yes aside, session rule 29)"
   (Q-1691-2). Amendment 194 items 5, 6 and 9 are applied to SPEC-0062 on the owner's `Approve: SPEC-0062`.

## Consequences

- A person in solo mode approves by answering one plain question on their own computer; the comment counts.
- A post made through an agent app never counts, and the person gets the body to paste.
- A comment the steward posts with `Who: AGK steward` never approves, even if its first line is an approval.

## Residual

- (due 2026-12-20) With ADR-0661's residual: count the approvals `approve` posted, the read-backs that did not count
  and the guard's approval denials by kind, and propose a change only from that count.
- The team side (SPEC-0063 rule 7) waits for the kept login of SPEC-0063 rule 4 (Q-1691-1).
