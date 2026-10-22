# Proposed spec amendments 38 (SPEC-0013 rules 4 and 5; REQ-030 part b)

Date: 2026-10-22 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0075. The path: `docs/specs/0013-playbook.md`.

1. **SPEC-0013 rule 4, what `/agk:start` writes.** The charter's Decision has, besides **Milestones**, **Non-goals** and **Done means**, the numbered item **Discovery** (one bullet `- <topic>: <answer or not known yet>`
   for each of `users`, `existing`, `runs`, `data`, `scale`, `compliance`, in that order) and, where SPEC-0023 rule 6 requires, **Slice** (`- <topic>: <one sentence saying what breaks if it is wrong>`). The skill asks
   the product owner about the open topics, at most three questions per round, before it writes; the two files written are still the whole difference.
2. **SPEC-0013 rule 5, the checks.** `check-start` also refuses a charter without the Discovery item, one of the six topics, an answer, the order, or the Slice bullet of a topic answered `not known yet`
   (SPEC-0023 rule 7). It runs on the start only.
