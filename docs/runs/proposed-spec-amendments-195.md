# Proposed spec amendments 195 (SPEC-0063; REQ-070)

Date: 2026-11-20 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0661 (brief #1577), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0063-in-team-mode-every-listed-reviewer-may-run-a-steward-first-come-first-served.md` (rule 7 and the
`## Tests` section). This session took 195, the next free number after 194 (Q-1577-3). This file proposes the lines and
does not edit the spec. Build (b) applies them word for word, on a person's `Approve: SPEC-0063` on its pull request; no
session posts it. Amendment 194 carries the solo side and the ask and confirm commands (SPEC-0062 rules 13, 14 and 16).

The sentence (brief #1577): "A person approves in their own words: the steward shows a short summary with its link, asks
one plain question, and only on a clear yes posts the exact line the kit needs, from that person's own login, quoting
their words."

## What is on the default branch today

Read on main at 7f6f33a8 (2026-11-20): SPEC-0063 rule 7 lets the steward post `Approve:` in team mode on its own
reviewer's plain yes, only for the signed-in login kept at the start (rule 4) and only when that login is in
`spec_approvers`; none of it is built (`steward_guard.py` `RESERVED`, line 39, denies `Approve:` in every mode).
`config/reviewers.yaml` holds only `teams` and `spec_approvers`; it has no architect or design-lead list (brief #1381,
open). `Confirmed:` stays denied in team mode (`Q-S0063-6`), and a steward the conductor started relays and approves
nothing (`Q-S0063-3`).

## Items

1. **Rule 7, the ask and the confirm, one sentence added after its first sentence.** "The question, the pending ask,
   the head pin and the reply are those of SPEC-0062 rules 13 and 14 (amendment 194): one decision about one target,
   recorded with `steward_owner.py ask --target`, and the line posted only by `steward_owner.py confirm` on a yes, with
   the `Owner said` and `Asked` lines and a last line `Who: <login>` equal to the login kept at the start. A
   `Maintainer answer:` form of that command (the evidence accept, an owner question, an amendment) is posted the same
   way and only when the kept login is in `spec_approvers`. The product owner, the architect and the design lead each
   run their own steward on their own machine and login; a steward never posts for another login." (answers 4 and 6)
2. **Rule 7, the guard bullet, the words "with the quote line and a `Who:` line that equals the kept login" replaced
   by:** "in a body written by `steward_owner.py confirm` and posted with `-F body=@<file>`, with the `Owner said` and
   `Asked` lines and a `Who:` line that equals the kept login"; and the last sentence gains `Merge:` beside `Verdict:`,
   `Final:` and `Correction:` as a first line that stays denied in every mode. (answer 7)
3. **Rule 7, the readers bullet, the words "the quote line is present" replaced by:** "the `Owner said` and `Asked`
   lines are present". (answer 8)
4. **Rule 7, the yes bullet, one sentence added at the end.** "'Shall I merge it?' maps to what holds the head as
   SPEC-0062 rule 13 holds (amendment 194 item 4); no steward posts or relays a `Merge:` line." (answer 9)
5. **The `## Tests` section, one line added.** "- Rule 7, the natural confirm in team mode: a `confirm` body whose
   `Who:` differs from the kept login is denied; a login outside `spec_approvers` gets no `Approve:` and no
   `Maintainer answer:`; `Confirmed:` is denied; a conductor-started steward is refused; a `Merge:` first line is
   denied; a comment marked by an agent app approves nothing; REQ-070 AC5." (answer 13)
6. **Unchanged:** rules 1 to 6 and 8 onward, the Proof, the Residual and the Contexts. Role lists for the architect and
   the design lead stay brief #1381's; until they exist, a role's line is given only by a login in `spec_approvers`.

## The builds (this spec's side)

- (b) of brief #1577 (amendment 194's build (b)): the guard's team-mode form, the readers' `Who:` reading (this spec's
  build (c), after SPEC-0062's build (d), `Q-S0063-8`) and items 1 to 5 applied word for word on the owner's
  `Approve: SPEC-0063`. `Depends-on` build (a).

## Questions

- Q-1577-3 (the amendment numbers): see amendment 194.
