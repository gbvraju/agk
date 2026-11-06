# The guard ladder

How a lesson becomes a rule and a rule becomes a check, by evidence and never by memory (brief #645, ADR-0309 Proposed).

## Where lessons live

A lesson is a row of a catch log, `docs/runs/<name>-catches-<n>.md`: a table under `## The catches` with at least the
columns `#`, `Date`, `Kind`, `Cause` and `Guard`, and optionally `Cost`. The conductor catch log
(`docs/runs/conductor-catches-1.md`, ADR-0294) is the first on the ladder. A project's own conductor keeps its logs in the
same shape, with its own rows. A log without a Guard column, as the architect catch logs are today, is named and not read.

## The ladder

Weakest first. A row's level is the strongest guard it holds.

| Level | Written in the Guard cell | Holds when |
| --- | --- | --- |
| `lesson` | `lesson`, `pending #<n>` or `pending (to be filed)` | nothing yet: it may be followed or not |
| `rule` | `` rule `<path>` `` | a line of that agent or guide file cites the row as `(row <n>)` |
| `test` | `` test `<path>` `` | a test fails the case |
| `check` | `` check `<path>` `` | a governance check or a command refuses the case |
| `workflow` | `` workflow `<path>` `` | CI or a scheduled job enforces it (on the owner's hold list) |

A guard may carry a note in parentheses after it; several guards are separated by `; `, strongest first.

## When a row is due to climb

Decided from the logs alone:

- A `lesson` is due to become a `rule` when another row has the same kind and cause (compared without case, spacing or a
  final period), or when its cost is one hour or more (`N h` or `N min`; an unknown cost never is).
- A `rule` is due to become a `test` or a `check` when a row of the same kind and cause is dated after it, or when it has
  stood 30 days. The row's date stands for the day its rule line was added: the row and its line land in one change.
- A `test` or a `check` is never due: a check becomes a `workflow` only with the owner's yes.

A due row is never promoted automatically: the pass names it, and the conductor files the brief that builds the guard.

## The pass

`python3 scripts/agk/lessons.py ladder [--root DIR] [--today YYYY-MM-DD]` reads the logs and the files their guards name,
and prints every row with its level, every row due to climb and the rule it meets (`due`), every row whose date the rules
cannot read (`undecided`), every guard whose file is missing or has no line citing the row (`missing`), every malformed
guard (`malformed`), every log not on the ladder, and one count line. It reads files only. It exits 1 on a `missing` or a
`malformed` line and 0 otherwise: the due list never blocks. The kit's suite runs it on this repository's own logs.

Running it weekly is a follow-up: carrying the due list in the drift audit needs a change of SPEC-0004.
