# ADR-0824: A standing ruling on the kit modules a new kit script may import

- Status: Proposed
- Date: 2026-11-26
- Deciders: maintainers (the owner's standing decision)
- Related: ADR-0583, ADR-0514, ADR-0749, ADR-0404, ADR-0310, ADR-0759, ADR-0372, SPEC-0056, SPEC-0073, SPEC-0074, SPEC-0075, amendment 245, amendment 246, brief #1972, brief #1954, plan #661
- Requirements: REQ-037

Protected classes: `scripts/agk/`, `.claude/`, `config/`, `tests/kit/`, `agk.toml`, `docs/adr/`

## Context

Four Approved specs say a new installed script uses the "standard library and `common.py` only": SPEC-0056 rule 5
(`check_runbooks.py`), SPEC-0073 rule 2 (`grill.py`), SPEC-0074 rule 2 (`check_domains.py`) and SPEC-0075 rule 3
(`check_data_patterns.py`). Each build imports the kit's offline readers too (`guard`, `config`, `playbook_format`,
offline sibling checks), and on 2026-11-25 the same reading was ruled four times in about eight hours (Q-1935-2 on
#1947, amendments 245 and 246, Q-1954-A on #1961). The owner's word (#1947, 2026-11-25T18:49:05Z, quoted as data):
"Maintainer answer: Q-1935-2 accept the imports"; and on the freeze (2026-11-26T04:21Z): "File both and work on
creating the brief for all pending on freeze . Go ahead and park them".

## Decision

1. Where an Approved spec or a brief says a new `scripts/agk/` script uses the "standard library and `common.py`
   only", the words read as: the standard library less its network modules (`rules.NETWORK`), plus the kit's
   offline set, with no new ruling. The offline set is `rules.KIT_IMPORTS` (`common`, `guard`, `config`,
   `playbook_format`, `kit_root`, `tree_walk`) and every `check_*.py` whose module-level import walk stays within
   that set and other such checks (`rules.kit_imports`, a file read of the script's folder; the largest set that
   holds, so a cycle is walked once and a member that gains a network import leaves it). "No network, no model" is
   unchanged and proved by the script's own tests. "Standard library only" (SPEC-0042, `guard.py`) and a spec's own
   explicit list (SPEC-0073 rule 2 as amendments 245 and 246 read it) are not widened; no spec text changes.
2. A third-party package, a network module of the standard library, a dynamic import and any kit module outside the
   set (for example `session`, `route`, `metrics`, `domain_model`) still need the owner's ruling, or an ADR that edits
   `KIT_IMPORTS`.
3. `rules.py imports <script> [--root DIR]` reads every import of one `scripts/agk/` file, at any level, and prints
   `Imports: <script> within the standing ruling (ADR-0824)` (exit 0) or one line per module `Imports: <script>
   imports <module> outside the standing ruling (ADR-0824): ask the owner` (exit 1). With this ADR not Accepted, or
   withdrawn by an Accepted ADR's `- Withdraws: ADR-0824`, a script importing beyond the standard library and
   `common` prints `Imports: <script>, no standing ruling: ask the owner`. A path outside `scripts/agk/`, or a file
   that does not parse, is refused naming the class.
4. The conductor's standing-rulings line takes a kit script's imports only from what the command prints; a `within`
   line needs no owner question. `check_brief.py` warns, never fails, on a brief that names the phrase. The owner
   withdraws this ruling by a later ADR; each project's owner keeps or withdraws it by its own ADR (ADR-0583 ruling 3).

The conductor's role file grows by one clause and no rule line, under ADR-0583 ruling 2; its `config/rule-budget.txt`
line is raised in the same pull request.

## Consequences

A kit script within the set is cleared without an owner question; the set is computed from the code, so it follows
the checks as they change, and ADR-0514's test still bars a third-party package. On main at 71eb8ab3 `grill.py` and
`check_runbooks.py` are within; `check_domains.py` is not, because since #1961 it imports `domain_model` at module
level (Q-1972-1).

## Residual

- 2026-11-26: whether `domain_model` joins `KIT_IMPORTS` (it is neither a base module nor a check) is the owner's
  (Q-1972-1); until then `check_domains.py` and `domain_model.py` print an `outside` line.
- 2026-11-26: the command reads imports only; whether a script calls a network function of `common.py` is proved by
  that script's own tests (Q-KI-4).
