# ADR-0421: Three project gaps from the pilot: a protected-path brief warning, local mode adopts workflows already off, the review agent re-runs the evidence check

- Status: Proposed
- Date: 2026-11-10
- Deciders: maintainers
- Related: brief #982, issues #482, #485, #486 and #488, plan #661, brief #390 (ADR-0214), brief #371 (ADR-0213), brief #434 (ADR-0233), SPEC-0023, SPEC-0030 rule 4
- Requirements: REQ-010, REQ-013

Protected classes: `scripts/agk/`, `.claude/`, `tests/kit/`

## Context

The first pilot project (2026-11-02) hit four gaps, each once; this decision closes three. A brief whose `Touches:` named a protected path class and
reserved no ADR passed `check_brief.py` and cost a round at `check_protected_changes.py`. With every workflow already turned off by hand, `local_mode.py enter` had nothing to do and recorded
nothing, so `leave` needed `--since`. The review agent's guard did not allow `evidence.py check`, so a local-mode review
marked the builder's figures `(verify)`.

## Decision

1. `check_brief.py --root DIR` warns, and never fails, on `rule 4b: Touches names a protected path class (<class>) and the
   brief reserves no ADR and names no Covered-by`, reading the classes from `DIR/config/protected-paths.txt` (a folder class
   matches a `Touches:` glob below or above it, a file class only a glob that matches the file). A `Reserved:` line naming an
   ADR or a `Covered-by: ADR-` line silences it. The file check prints `warning: ...` before `ok brief`; a passing `--event`
   result carries a `warnings` list. Without `--root`, or without the file, nothing is warned.
2. `local_mode.py enter`, when every workflow of the repository is `disabled_manually`, takes the day of the earliest of them
   (midnight UTC) as the start, opens the record issue `Local mode since YYYY-MM-DD` with `--write` when none is open (the
   dry run prints the call; an open one is kept; an unreadable list opens nothing and exits 4), and prints
   `leave: python3 scripts/agk/local_mode.py leave --since YYYY-MM-DD`. `--write` stays refused inside an agent session.
3. `architect_guard.py --review` allows `python3 scripts/agk/evidence.py check RECORD [--head SHA] [--sample N] [--json]` and
   no other form. The check writes nothing in the repository: its worktree is made in a temporary folder, removed and
   pruned, and the lock lives in the temp folder or `lock_dir`. The deciding architect's list is unchanged.

## Consequences

A brief that would need an ADR says so when it is filed.
Entering local mode after the workflows were turned off by hand leaves a start `leave` can read. A local-mode review can
re-run the evidence check instead of marking the figures `(verify)`.

## Residual

The warning reaches the person only in the file check and the event's JSON; the brief workflow does not yet post it (a
workflow change, not made here). The earliest disabled day can predate local mode when a workflow was turned off long
before; `enter` prints that day so a person can correct it (Q-982-1). The fourth gap, `project.mk` missing from an init
project's protected paths (#485), is not decided here: it also needs the kit's own `config/protected-paths.txt`,
`config/reviewers.yaml` and two `tests/kit_dev/` tests, and goes to a later brief of its own (owner, 2026-11-10).
