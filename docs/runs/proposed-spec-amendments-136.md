# Proposed spec amendments 136 (SPEC-0039; REQ-046)

Date: 2026-11-08 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). The path:
`docs/specs/0039-the-conductor-merges-a-cleared-pull-request-through-one-guarded-command.md`. It is applied to the spec text in the same pull request, as amendments 127, 130 and 131 were. It
needs the owner's `Approve: <head> SPEC-0039` on the pull request; no session posts it.

1. **Rule 8 and Q-S0039-15 (who can run `merge_cleared.py`).** The project settings put every form of the command on
   `ask`, so it held builders back; it also held back every scheduled conductor session, which cannot answer an `ask` `(verify)`
   (2026-11-08: the merge runs for #715 and #734 were refused, as they reported: "#734 not merged: this session's permission check blocked the merge script" (03:12Z); "#715 refused (this session's permission check stopped the guarded merge command before it ran; nothing was merged)" (03:41Z); an attended session merged them). The
   owner rules (2026-11-08, this conversation and plan #661): exactly `python3 scripts/agk/merge_cleared.py` moves to
   `allow` in `.claude/settings.json`; every other form of it, and `conductor.py merge-queue`, stays on `ask`; nothing is
   denied. Builders stay blocked from any merge by session rule 2 and their launch prompt, and the script's own
   re-checks are the gate: a cleared verdict on the exact head, green required checks, the owner's approvals; whether the move to `allow` lets an unattended conductor run the command is `(verify)` until the first scheduled merge after this lands.
