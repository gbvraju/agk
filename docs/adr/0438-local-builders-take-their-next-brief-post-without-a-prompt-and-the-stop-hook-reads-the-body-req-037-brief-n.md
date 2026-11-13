# ADR-0438: Local builders take their next brief, post without a prompt, and the stop hook reads the body

- Status: Accepted
- Date: 2026-11-11
- Deciders: maintainers
- Related: brief #1029, plan #661, session rule 18, ADR-0271 (brief #545), ADR-0417, ADR-0402
- Requirements: REQ-037

Protected classes: `agk.toml`, `.claude/`, `tests/kit/`, `tests/kit_dev/`, `kit/`

## Context

On 2026-11-11 the work moved to the owner's laptop: a conductor and builders lap1 and lap2, each in its own worktree.
Read on main c6294d0, three causes cost owner touches and tokens that night. `[flow] assign = "conductor"` made
`session.py after --session lap1` print `ask the conductor on #204`, so each brief cost a `Request:`, a conductor wake
and an `Assign:` round trip. `.claude/settings.json` allowed no `gh api` call, so every `Request:`, `Report:`,
`Question:` and ready mark stopped for the owner as an outside write; the owner's own `.claude/settings.local.json`
then turned governance red, because the untracked-file check lists it and `.gitignore` did not name it. And
`.claude/hooks/stop_check.py` ran governance without `AGK_PR_BODY`, so `check_protected_changes.py` never saw a
pull request's `Covered-by:` line: on #994 (`Covered-by: ADR-0265`) the hook printed `FAIL protected-changes` at
every stop. The owner's word (2026-11-11 02:56 IST): "file it both 1 and 2, launcher item as well".

## Decision

1. This repository sets `[flow] assign = "next"` by the owner's direction of 2026-11-11: a finished builder's
   `session.py after` takes the next ready brief (session rule 18). `builder_start = "assign"` is unchanged, so the
   slots `s<n>` of the cloud pool keep starting from their scheduled runs and acting on `Assign:` lines.
2. `.claude/settings.json` allows, without a prompt, the REST comment posts on issues and pull requests, the ready
   mark (`gh api --method POST repos/*/pulls/*/ccr/ready_for_review` and `gh pr ready *`), `gh pr view *`,
   `git fetch`, `git switch`, `git checkout`, `git merge origin/*` and `git push origin claude/*`. It denies
   `gh api *merge*`, `gh api *-X PUT*` and `gh api *--method PUT*`, so no allow line opens a merge outside
   `merge_cleared.py`. The allow lines name no repository. No other entry changes.
3. `.gitignore` names `.claude/settings.local.json`, a person's own permissions, with a comment saying so. The line
   is in the kit's block, so it is in `kit/templates/gitignore` too: the kit's own `.gitignore` is that block
   exactly (ADR-0164), and every installing project gets the line.
4. When `AGK_PR_BODY` is unset, the stop hook finds the open pull request whose head is the checkout's branch with
   one GET, `gh api "repos/<owner>/<repo>/pulls?head=<owner>:<branch>&state=open"` (owner and repository read from
   the `origin` remote), writes its body to a temporary file, runs governance with `AGK_PR_BODY` naming it and
   removes the file afterwards. On any failure to read (no `gh`, no network, no pull request, a detached head, no
   `origin`, an answer that is not a list of pull requests) it runs governance exactly as before. A set
   `AGK_PR_BODY` is used as it is.

## Consequences

Local builders run without the owner or the conductor in the loop between briefs. With `assign = "next"` the
auto-pilot of SPEC-0048 rule 3, which needs `[flow] assign = "conductor"`, is off in this repository until the
setting is turned back by an ADR. Merges stay with `merge_cleared.py` and the merger job: the deny lines win over the
allow lines, and a comment post whose text holds `merge` (a `Report: <head> merge of main`) is denied too unless its
body is passed from a file (`-F body=@file`), so builders post from a file. The two comment allow lines let a session
post any comment, on any pull request or issue, without the owner seeing it first; sessions and the owner share one
account, so a builder's `Verdict:`, `Approve:`, `Confirmed:` or `Maintainer answer:` line is then held only by
session rules 2 and 29. The stop hook makes one network read per stop on a branch, bounded by a timeout, and never
writes to GitHub. Every installing project gets the same allow lines and hook; `assign` is this repository's own
setting.

## Residual

- 2026-11-11: the after-measure is the brief's: on the laptop `session.py after --session lap1` takes the next ready
  brief and the stop hook is green on a branch whose body has `Covered-by:`; it is measured on the laptop, not in a
  cloud session.
- 2026-11-11: the comment allow lines leave a session's posts unprompted, and the owner's own lines held only by
  session rules 2 and 29, until sessions post under their own identity.
