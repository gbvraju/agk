# ADR-0711: Every merge path counts only a listed author's verdict and holds outside pull requests (REQ-046)

- Status: Proposed
- Date: 2026-11-22
- Deciders: maintainers
- Related: ADR-0261, ADR-0263, ADR-0277, ADR-0684, SPEC-0021, SPEC-0025, SPEC-0039, brief #1709, plan #661
- Requirements: REQ-046

Protected classes this pull request changes: `scripts/agk/` (`merge_cleared.py`, `reviewers.py`, `conductor.py`) and
`tests/kit/`. `docs/specs/` and `docs/requirements.md` are not edited: amendment 214
(`docs/runs/proposed-spec-amendments-214.md`) proposes the lines of SPEC-0039 rules 3 and 5 and of REQ-046 AC2, applied
by a later pull request on a person's `Approve: SPEC-0039`. `kit/hashes.json` is not edited by hand.

## Context

SPEC-0039 rule 3 lets any account's `Verdict:` comment clear a head when `conductor_accounts` is unset, because "trust
rests on who can run the guarded command (rule 8), not on who posted the comment". That held while only the conductor
ran the command on a pull request it chose. It no longer holds: the merger workflow starts on any comment whose first
line starts `Verdict:`, and the sweep (in local mode after a conductor lapse, ADR-0684) walks every open pull request.
The repository is public, so any GitHub account can post `Verdict: cleared <head>` on a green head, or a later
`Verdict: rejected` that hides a listed author's clearing verdict, or open a pull request from a fork. Measured on main
at f1d2f05: `merge_cleared.judge` returns `('cleared', '')` for a stranger's verdict with `conductor_accounts` unset.
The conductor's own queue (`conductor.queued`) and the lease read already count only listed verdict authors.

## Decision

1. **One trusted list.** `reviewers.trusted_verdict_authors(data, pull_author)` returns `conductor_accounts` when it
   lists a login, else the listed verdict authors (`authors_of`: `verdict_authors`, else the `maintainers` user handle)
   with the pull request's own author dropped when two or more are listed (SPEC-0025 rule 4, as `conductor.queued`).
   It never reads an empty list as "anyone". It is read from `config/reviewers.yaml` at the fetched default branch.
2. **Unlisted verdicts are not verdicts.** `merge_cleared.judge` and every reader of the latest verdict in a merge path
   (`holds`, `verdict_state`, the merger event, the sweep, the merge queue, `conductor.cleared_open`) ignore a comment
   whose first line starts `Verdict:` by a login that is not on the list, so it neither clears nor hides a listed one.
   A covered fix list counts the same way. An empty list holds every head with `no listed verdict author (rule 3;
   setting: verdict_authors in config/reviewers.yaml)`.
3. **Outside pull requests wait for the owner.** `hold_list` holds, as `outside author (rule 5)`, a pull request whose
   head repository is not the base repository (a fork, or a deleted one) or whose author's permission, read with one
   GET of `repos/{o}/{r}/collaborators/{login}/permission`, is not `write`, `maintain` or `admin`; an answer that cannot
   be read is held the same way. It is an owner-only hold (`OWNER_HOLDS`), lifted only by `merge_cleared.py --pr <n>
   --owner` after the owner reads the change, in every path (Q-1709-1).
4. **`execution` is read strictly.** `ruled` refuses any `execution` other than `hosted`, `hybrid`, `pool` and `local`
   (setting: execution in agk.toml), and `github_mode` reads only those, so a malformed value never moves merging to
   the workflow.
5. **Settings.** The trust and the hold are the same in every `pr_mode`, `review_mode` (solo: the one listed login, the
   sessions' own), `execution`, with `merge_queue` on or off and with `conductor_lapse_minutes` set or absent. Personal
   mode has no forge merge and is unchanged. No new `agk.toml` or `config/reviewers.yaml` key.

## Consequences

A comment on a public repository can no longer clear, or hide, a head in any merge path, and a fork or non-collaborator
pull request merges only on the owner's `--owner` run. A project whose `maintainers` handle is a team and that lists no
`verdict_authors` now holds every head, naming the setting, where it merged on any verdict before; the guide says to
list the verdict authors. One more GET per merge attempt reads the author's permission.

## Residual

- 2026-11-22: amendment 214 applies the text to SPEC-0039 and REQ-046 on a person's `Approve: SPEC-0039` (Q-1709-4).
- 2026-11-22: reading `[personal] forge` in `github_mode` is left to a later brief (Q-1709-3).
