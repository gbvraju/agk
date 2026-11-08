# Proposed spec amendments 138 (SPEC-0034; REQ-057)

Date: 2026-11-08 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0351 (brief #751, SPEC-0050 build (c)), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0034-a-team-sets-how-many-builder-sessions-run-at-once-and-agk-ha.md`. The number 138 is the one brief #751
reserved. This amendment is not applied to the spec text in this pull request (SPEC-0050 rule 10); the owner decides it,
and it needs a person's `Approve: SPEC-0034`; no session posts it.

1. **`claim` judges overlap (rule 3).** Rule 3 gains: `session.py claim --brief N`, with and without `--build X`, applies
   the overlap of this rule in the one judgement that `next` (with and without `--take`) and `plan` share (SPEC-0050 rules
   2 and 4): a brief whose `Touches:` overlap a brief that is taken and has no builder pull request yet, or a file an open
   builder pull request changes, is refused with the same line `next` prints, `skip #<n>: waits for #<m> (both touch
   <file>)` or `skip #<n>: waits for pull request #<m> (it changes <file>)`, exit 1, and nothing is posted. A conductor's
   `Assign:` does not override it. Another build of the same brief is not a rival. The open briefs, the pull requests
   and their files are read as `next` reads them; a read that fails stops the claim and posts nothing.
2. **The shared indexes (rule 3).** Rule 3 gains: besides the shared-mechanical paths of rule 7, the shared indexes
   never count as an overlap. They are the optional `shared_indexes` of the `[flow]` table, a list of exact repository
   paths, default `["kit/manifest.json", "agk.toml", "config/rule-budget.txt", "docs/requirements.md",
   "docs/build-state.md"]`; a set list replaces the default. A value that is not a list of non-empty strings, or an
   entry with a wildcard or ending in `/`, is refused naming `setting: flow.shared_indexes`, never the value. A shared
   index still counts for the re-prove state of SPEC-0050 rule 6, which the guarded merge holds (amendment 137).
3. **Tests.** Rule 14's list gains: two briefs that both name one file, the first taken, give the same `skip` line from
   `next`, `plan` and `claim`, and `claim` posts nothing; a brief overlapping an open pull request that modifies the
   file is refused; a pull request that only adds another file does not refuse; another build of the same brief does
   not refuse; two briefs that share only a shared index both start; a set list replaces the default; each bad value of
   the setting is refused naming the setting and never the value.
