# CLAUDE.md — agent operating rules (agk)

`constitution/principles.md` is authoritative (twelve numbered rules). Read it first, then `config/core-rules.md`: the
one page that names the core rules by number and holds the numbered operating rules this file listed before, each
cited as `CLAUDE.md item N`. Items 2 and 10 stay here with their numbers:

2. One PR per item, branched from the default branch (`origin/<default branch>`), never stacked on another's
   unmerged change; a dependence is declared with `Depends-on: #n`. One open PR per session: several sessions may
   have one each in flow mode (`pr_mode` in `agk.toml`); in strict mode, the default, a person has one open PR at a
   time. Push and stop; never poll CI; never merge; never enable auto-merge. Never post a comment whose first line
   is `Confirmed:`: in solo mode you print its text and the person posts it (session rule 29).

And:

10. Check the state of a pull request with `gh api repos/{owner}/{repo}/pulls/{n}` (a GET); the GraphQL form of the
    command is blocked in cloud sessions.

The working rule of a session (what it acts on, what it never does, how it finds its next item) is in `config/session-rules.md`.

## Compaction recovery

After compaction or a new session, re-read CLAUDE.md, the current brief, `docs/runs/decisions-log.md` and the
open PR body before acting.
