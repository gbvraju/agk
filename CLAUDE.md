# CLAUDE.md — agent operating rules (agk)

`constitution/principles.md` is authoritative (twelve numbered rules). Read it first. These are the operating
rules in short form:

1. You implement; you never decide. Decisions are ADRs or requirement statuses written by the reviewers. Where a
   brief leaves something open, record it as a `Q-…` question and choose the most conservative reading.
2. One PR per item, branched from the default branch (`origin/<default branch>`), never stacked; one open PR at a
   time. Push and stop; never poll CI; never merge; never enable auto-merge.
3. Protected paths (`config/protected-paths.txt`) change only with an ADR in the same PR that names each changed
   path class.
4. Tests first. Every check ships with tests of the check (`tests/kit/`). You never mark anything done.
5. No secrets anywhere, ever; no network calls in checks; no new ignore entries for scanners.
6. Dates from `date -u`. Refusal messages name the setting or path class, never a value.
7. PR body: `Advances: REQ-…`, `Build-state row:` (you never edit `docs/build-state.md` in a feature PR),
   `Decisions taken:`, `Questions:`, `Verified:` (commands and verbatim counts).
8. No token listed in config/neutrality.txt appears in tracked files (check_neutrality.py); refusals name the
   setting, never the value.
9. Unsure of a Claude Code fact: mark it `(verify)` in the file and in the PR body; an unconfirmed fact is a
   question, not a guess.

## Compaction recovery

After compaction or a new session, re-read CLAUDE.md, the current brief, `docs/runs/decisions-log.md` and the
open PR body before acting.
