# Core overlap 1: rules that say the same thing

This page is evidence for #278, not a decision: it lists, for each session rule and each spec named in the rows of the
decision table of ADR-0212, the other rules that state the same thing. It changes no rule, no spec and no check; a person
decides each row of ADR-0212.

How it was made (brief #382, answer 2), on 2026-10-31 (the date from `date -u`):

- The rules are named by number only and never restated: `session rule N` is rule N of `config/session-rules.md`,
  `SPEC-NNNN rule N` is rule N of the `## Rules` section of that spec, and `CLAUDE.md item N` is item N of `CLAUDE.md`.
- The number in brackets after each rule is the audit's count for it: the `Verdict:` comments by a listed author that cite
  the rule, from `docs/runs/core-audit-2026-10-31.md` (`python3 scripts/agk/core_audit.py --write`, the whole history,
  286 pull requests). `SPEC-0034 rule 7` is counted by its parts as the audit counts them (`7`, `7b`, `7c`). The audit does
  not count `CLAUDE.md` items, so they carry `(not counted)`.
- A count is how often a verdict cited a rule, not how often a session followed it: a zero says the rule was never named in
  a refusal, not that it is unused.
- "States the same thing" means the other rule gives the same instruction, in whole or in part, for the same actor; a
  rule that only points at another (for example "as in SPEC-0030 rule 3") is not listed.

## Session rules

| Session rule | States the same thing as |
| --- | --- |
| session rule 1 (1) | SPEC-0030 rule 1 (0), SPEC-0030 rule 2 (0), session rule 16 (0), session rule 20 (0), session rule 24 (1) |
| session rule 2 (0) | SPEC-0030 rule 1 (0), SPEC-0023 rule 2 (0), SPEC-0032 rule 8 (0), session rule 29 (1), session rule 30 (3), CLAUDE.md item 2 (not counted) |
| session rule 3 (0) | SPEC-0030 rule 1 (0), SPEC-0025 rule 5 (2), SPEC-0025 rule 6 (0), CLAUDE.md item 2 (not counted) |
| session rule 4 (0) | SPEC-0030 rule 1 (0) |
| session rule 5 (0) | SPEC-0030 rule 3 (0), session rule 18 (0) |
| session rule 6 (0) | SPEC-0030 rule 1 (0), session rule 21 (1), CLAUDE.md item 1 (not counted) |
| session rule 7 (1) | SPEC-0033 rule 1 (1), SPEC-0033 rule 2 (0) |
| session rule 8 (0) | SPEC-0033 rule 3 (0) |
| session rule 9 (0) | SPEC-0033 rule 4 (0), SPEC-0033 rule 5 (0) |
| session rule 10 (0) | SPEC-0032 rule 3 (2), SPEC-0032 rule 4 (1), session rule 24 (1), session rule 32 (0) |
| session rule 11 (0) | SPEC-0032 rule 3 (2), SPEC-0033 rule 7 (0), session rule 23 (0), session rule 33 (0) |
| session rule 12 (0) | SPEC-0033 rule 8 (0) |
| session rule 13 (2) | SPEC-0034 rule 7b (1), session rule 15 (0), session rule 23 (0), session rule 31 (0) |
| session rule 14 (1) | SPEC-0034 rule 7 (0), SPEC-0025 rule 3 (1), session rule 15 (0) |
| session rule 15 (0) | SPEC-0034 rule 7c (1), SPEC-0025 rule 2 (0), session rule 13 (2), session rule 14 (1) |
| session rule 16 (0) | SPEC-0034 rule 11 (1), session rule 1 (1), session rule 17 (1), session rule 21 (1) |
| session rule 17 (1) | SPEC-0034 rule 11 (1), SPEC-0034 rule 12 (0), SPEC-0035 rule 7 (0), session rule 16 (0), session rule 25 (0), session rule 26 (0), session rule 32 (0) |
| session rule 18 (0) | SPEC-0034 rule 5 (2), session rule 5 (0) |
| session rule 19 (0) | SPEC-0032 rule 9 (0), session rule 21 (1) |
| session rule 20 (0) | SPEC-0032 rule 10 (0), session rule 1 (1), session rule 24 (1) |
| session rule 21 (1) | session rule 6 (0), session rule 16 (0), session rule 23 (0), CLAUDE.md item 1 (not counted) |
| session rule 22 (1) | none |
| session rule 23 (0) | session rule 11 (0), session rule 13 (2), session rule 21 (1), session rule 33 (0) |
| session rule 24 (1) | SPEC-0030 rule 2 (0), session rule 1 (1), session rule 10 (0), session rule 20 (0) |
| session rule 25 (0) | SPEC-0035 rule 1 (2), SPEC-0035 rule 2 (0), SPEC-0035 rule 7 (0) |
| session rule 26 (0) | SPEC-0035 rule 3 (1), SPEC-0035 rule 7 (0) |
| session rule 27 (1) | SPEC-0036 rule 1 (2), SPEC-0036 rule 6 (0) |
| session rule 28 (1) | SPEC-0034 rule 9 (0) |
| session rule 29 (1) | SPEC-0032 rule 5 (2), SPEC-0032 rule 6 (1), session rule 2 (0), CLAUDE.md item 2 (not counted) |
| session rule 30 (3) | session rule 2 (0) |
| session rule 31 (0) | session rule 13 (2) |
| session rule 32 (0) | session rule 10 (0), session rule 17 (1) |
| session rule 33 (0) | session rule 11 (0), session rule 23 (0) |

Three groups stand out, each one row of ADR-0212:

- What a session runs first on a start or a restart is stated by session rules 11, 23 and 33, each with "first" or
  "before anything else".
- What a session runs before a push is stated by session rules 13 and 31.
- When `session.py watch` ends is stated by session rules 1, 10, 20 and 24.

## Specs

Each spec below has rules that a session rule states again; the session rules column is the reverse of the table above.
Specs not listed have no rule that a session rule states again.

| Spec rule | Stated again by |
| --- | --- |
| SPEC-0023 rule 2 (0) | session rule 2 (0) |
| SPEC-0025 rule 2 (0) | session rule 15 (0) |
| SPEC-0025 rule 3 (1) | session rule 14 (1) |
| SPEC-0025 rule 5 (2) | session rule 3 (0) |
| SPEC-0025 rule 6 (0) | session rule 3 (0) |
| SPEC-0030 rule 1 (0) | session rules 1 (1), 2 (0), 3 (0), 4 (0), 6 (0) |
| SPEC-0030 rule 2 (0) | session rules 1 (1), 24 (1) |
| SPEC-0030 rule 3 (0) | session rule 5 (0) |
| SPEC-0032 rule 3 (2) | session rules 10 (0), 11 (0) |
| SPEC-0032 rule 4 (1) | session rule 10 (0) |
| SPEC-0032 rule 5 (2) | session rule 29 (1) |
| SPEC-0032 rule 6 (1) | session rule 29 (1) |
| SPEC-0032 rule 8 (0) | session rule 2 (0) |
| SPEC-0032 rule 9 (0) | session rule 19 (0) |
| SPEC-0032 rule 10 (0) | session rule 20 (0) |
| SPEC-0033 rule 1 (1) | session rule 7 (1) |
| SPEC-0033 rule 2 (0) | session rule 7 (1) |
| SPEC-0033 rule 3 (0) | session rule 8 (0) |
| SPEC-0033 rule 4 (0) | session rule 9 (0) |
| SPEC-0033 rule 5 (0) | session rule 9 (0) |
| SPEC-0033 rule 7 (0) | session rule 11 (0) |
| SPEC-0033 rule 8 (0) | session rule 12 (0) |
| SPEC-0034 rule 5 (2) | session rule 18 (0) |
| SPEC-0034 rule 7 (0), 7b (1), 7c (1) | session rules 13 (2), 14 (1), 15 (0) |
| SPEC-0034 rule 9 (0) | session rule 28 (1) |
| SPEC-0034 rule 11 (1) | session rules 16 (0), 17 (1) |
| SPEC-0034 rule 12 (0) | session rule 17 (1) |
| SPEC-0035 rule 1 (2) | session rule 25 (0) |
| SPEC-0035 rule 2 (0) | session rule 25 (0) |
| SPEC-0035 rule 3 (1) | session rule 26 (0) |
| SPEC-0035 rule 7 (0) | session rules 17 (1), 25 (0), 26 (0) |
| SPEC-0036 rule 1 (2) | session rule 27 (1) |
| SPEC-0036 rule 6 (0) | session rule 27 (1) |

Several of these specs ask for the restatement themselves (for example, SPEC-0033 rule 1 ends "`config/session-rules.md`
says so in one numbered rule", and SPEC-0035 rule 7 says the session rules give the shapes), so a spec rule and the session
rule that states it again are one decision written for two readers; ADR-0212 proposes them as such.
