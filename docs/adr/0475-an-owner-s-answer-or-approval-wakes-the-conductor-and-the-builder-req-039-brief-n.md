# ADR-0475: An owner's answer or approval wakes the conductor and the builder

- Status: Proposed
- Date: 2026-11-12
- Deciders: maintainers
- Related: SPEC-0032, ADR-0308, brief #961, brief #1102, brief #1112, plan #661
- Requirements: REQ-039

## Context

`conductor.py watch` ended only on a new comment whose first line starts `Question:` or `Report:` (`TRIGGERS`), and
`session.py watch` only on a verdict, a correction, a label change, a conflict, a merge or a close. An owner's
`Maintainer answer:`, `Answer:` or `Approve:` woke neither. On 2026-11-12 the owner answered Q-1101-3 on #1102 at 13:36Z
and the pull request sat green at `agk:review` until a person restarted its builder to post a fresh `Report:` at 13:45Z.

## Decision

1. `conductor.py`: `WAKES = TRIGGERS + ("Answer:", "Maintainer answer:", "Approve:")` is used only by `new_lines`
   (through `wakes`), so `watch` prints `<n> <first line>` for each such new comment on an open brief or pull request.
   An `Answer:` or `Maintainer answer:` counts only when it names a `Q-` id (`session.ANSWER_LINE`); an `Approve:` only
   when its author is a listed spec approver. `waiting_on`, and with it `sweep`, keeps `TRIGGERS` unchanged.
2. `session.py watch --pr N`: after a `Question:` by the pull request's author, a later `Answer: Q-…` or
   `Maintainer answer: Q-…` that names one of its Q ids, by a listed verdict author or spec approver, prints
   `answer <Q-id> (comment <id>)` and exits 0; it is read from the same floor as a missed verdict or correction (the
   author's last `Report:`, or `--since`), so one that landed before the watch started is not lost, and the builder's
   fresh `Report:` after applying it spends it. An `Approve: <sha> SPEC-nnnn` by a spec approver whose sha names the
   current head, newer than the comments the watch read at its start (and than `--since`), prints
   `approve <head7> SPEC-nnnn` and exits 0; an approval needs no change, so a restarted watch does not wake on it again.
3. The builder's handling is unchanged in meaning: on `answer` it applies the answer and posts a fresh
   `Report: <head> ready for review`; on `approve` there is nothing to change. `config/session-rules.md` rule 10 lists the
   watch's ends; its text is the maintainers' (Q-1112-1).

Protected path classes changed: `scripts/agk/` (`conductor.py`, `session.py`) and `tests/kit/`
(`test_conductor_wakes.py`, `test_session_watch_answers.py`, and the `new_lines` stand-ins of `test_pool_health.py`
and `test_builder_assign.py`, which take the new `approvers` argument), and `agk.toml` (the test map only: the two new
test files under `conductor.py` and `session.py`).

## Consequences

An answered or approved pull request is reviewed on the conductor's next pass and its builder wakes at once, without a
hand restart or the stopgap `Report:` the builder prompt asks for. The conductor wakes once more per answer and per
approval; `sweep` and the review queue read what they read before. No workflow changes: the router already routes
`Maintainer answer:` and `Approve:` (#1102).

## Residual

- 2026-11-12: an answer by an account that is also the pull request author's login is read as an answer only when its
  first line is `Answer:` or `Maintainer answer:`; a builder never posts such a line (due 2027-01-31).
