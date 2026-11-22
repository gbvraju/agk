# Proposed spec amendments 214 (SPEC-0039; REQ-046)

Date: 2026-11-22 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0711 (brief #1709), which stays `Proposed` for the maintainers' decision. The paths:
`docs/specs/0039-the-conductor-merges-a-cleared-pull-request-through-one-guarded-command.md` (rules 3 and 5) and
`docs/requirements.md` (REQ-046 AC2). Brief #1709 reserved amendment 214 (comment of 2026-11-22). This file proposes the
lines and does not edit the spec. A later pull request applies them word for word, on a person's `Approve: SPEC-0039`
on it; no session posts it.

## Why

Rule 3 trusts any account's verdict while `conductor_accounts` is unset, because only the conductor ran the command.
The merger's comment event and its sweep now run it on a pull request they did not choose, and the repository is
public, so a stranger's `Verdict:` comment could clear a green head or hide a listed author's verdict.

## Items

1. **Rule 3, the sentences from "A `Verdict:` comment on its own merges nothing" to "so it can only hold a pull
   request."** Replace them with: "Only a verdict by a trusted author counts: `conductor_accounts` when it lists a
   login, else the listed verdict authors of SPEC-0021 rule 5 (`verdict_authors`, else the `maintainers` user handle),
   without the pull request's own author when two or more are listed. A `Verdict:` comment by any other account is not
   a verdict: it neither clears nor hides one by a trusted author. With no trusted author every head is held, naming
   `verdict_authors`. The list is read from `config/reviewers.yaml` on the default branch as last fetched."
2. **Rule 3, the sentence "One account is the default (`Q-S0039-1`)."** Becomes: "One listed account is the default
   (`Q-S0039-1`)."
3. **Rule 5, a new item after the protected-class item:** "- one whose head is not a branch of the base repository (a
   fork, or a deleted one), or whose author has no `write`, `maintain` or `admin` permission on it, read with one GET,
   an unreadable answer counting as none (`outside author`); like a release or a protected class it waits for the
   owner's `--owner` merge;"
4. **REQ-046 AC2,** in `docs/requirements.md`: "with it absent one account suffices" becomes "with it absent the
   verdict's author must be a listed verdict author".

No other rule changes.
