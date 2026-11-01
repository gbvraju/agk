# Core rules

The page a session reads first (ADR-0247). It names the core rules by number and file, each with one plain sentence that
adds nothing. The numbered rules win over the summaries: read a rule in its file before acting on it. Everything else
is reference. `principle N` is rule N of `constitution/principles.md`, `session rule N` is rule N of
`config/session-rules.md`, and `CLAUDE.md item N` is item N of the last section of this page.

## The constitution

All of `constitution/principles.md`, principles 1 to 12, is core; it is short, so read it whole.

## Safety rules

- `session rule 2`: a session never merges, tags, enables auto-merge, posts a verdict or touches a secret.
- `session rule 14`: the shared-mechanical files are the maintainers' list, and a build never edits `kit/hashes.json`.
- `session rule 15`: a session resolves only a mechanical conflict, and any other conflict ends the work.
- `session rule 22`: a session pushes only the branch its runtime gives it.
- `session rule 29`: a session never posts a `Confirmed:` comment, which is the person's own.
- `session rule 30`: when GitHub Actions is blocked a session follows the local-mode guide and leaves workflows to a person.
- `session rule 33`: a session checks the default branch for a pause first and on every wake, and stops when paused.
- `CLAUDE.md item 3`: a protected path changes only with an ADR in the same pull request that names its class.
- `CLAUDE.md item 5`: no secrets, no network calls in checks and no new scanner ignore entries.
- `CLAUDE.md item 8`: no token of the neutrality list appears in a tracked file.

## Working rules

- `session rule 1`: a session acts only on a verdict that names its head, a merge of its pull request or a correction.
- `session rule 3`: a session has one open pull request, and a dependence is declared with `Depends-on: #n`.
- `session rule 7`: a builder commits checkpoints and pushes only at the milestones the rule lists.
- `session rule 17`: each kind of comment lives in one place, and a builder never ends silently.
- `session rule 18`: after its merge a builder takes the brief's next build or runs `session.py after`.
- `session rule 21`: a blocked session asks with `Question:` on GitHub and waits there.
- `session rule 31`: a builder runs `prepush.py` before each push and pushes only after it passes.

## CLAUDE.md items

The numbered list that `CLAUDE.md` carried before ADR-0247, with its numbers and its exact text.

1. You implement; you never decide. Decisions are ADRs or requirement statuses written by the reviewers. Where a
   brief leaves something open, record it as a `Q-…` question and choose the most conservative reading.
2. One PR per item, branched from the default branch (`origin/<default branch>`), never stacked on another's
   unmerged change; a dependence is declared with `Depends-on: #n`. One open PR per session: several sessions may
   have one each in flow mode (`pr_mode` in `agk.toml`); in strict mode, the default, a person has one open PR at a
   time. Push and stop; never poll CI; never merge; never enable auto-merge. Never post a comment whose first line
   is `Confirmed:`: in solo mode you print its text and the person posts it (session rule 29).
3. Protected paths (`config/protected-paths.txt`) change only with an ADR in the same PR that names each changed
   path class.
4. Tests first. Every check ships with tests of the check. You never mark anything done.
5. No secrets anywhere, ever; no network calls in checks; no new ignore entries for scanners.
6. Dates from `date -u`. Refusal messages name the setting or path class, never a value.
7. PR body: `Advances: REQ-…`, `Build-state row:` (you never edit `docs/build-state.md` in a feature PR),
   `Decisions taken:`, `Questions:`, `Verified:` (commands and verbatim counts).
8. No token listed in config/neutrality.txt appears in tracked files (check_neutrality.py); refusals name the
   setting, never the value.
9. Unsure of a Claude Code fact: mark it `(verify)` in the file and in the PR body; an unconfirmed fact is a
   question, not a guess.
10. Check the state of a pull request with `gh api repos/{owner}/{repo}/pulls/{n}` (a GET); the GraphQL form of the
    command is blocked in cloud sessions.
