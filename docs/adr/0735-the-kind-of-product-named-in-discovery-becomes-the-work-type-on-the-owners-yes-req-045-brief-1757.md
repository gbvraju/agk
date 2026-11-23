# ADR-0735: The kind of product named in discovery becomes the work type on the owner's yes (REQ-045)

- Status: Proposed
- Date: 2026-11-22
- Deciders: maintainers
- Related: brief #1757, SPEC-0038, ADR-0312, ADR-0316, ADR-0703, amendment 218
- Requirements: REQ-045

Protected classes: `scripts/agk/`, `tests/kit/`, `docs/specs/`

## Context

SPEC-0038 rule 5 lets only the owner's ADR write the `[delivery] work_type` line of `agk.toml`, and no session writes it.
In a clean solo sample project of 2026-11-22 (brief #1757's evidence), discovery recorded `- Work type: web-app
(proposed)`, but nothing carried it to `agk.toml`: `engines.py stack-write` drafted the generic default stack, the
web-app playbook's gates never switched on and `doctor.py` printed `work type: none (no playbook)`. The only path for a
business owner was a hand edit of a protected file plus a decision record.

## Decision

1. `steward_owner.py work-type --propose`: with no `[delivery] work_type` and exactly one work type other than `pilot`
   named by the `- Work type: <type> (proposed)` lines under `docs/discovery/`, print one plain owner question with no
   kit term ("Your discovery says this is a web app. Shall I set that up, so the web-app checks run? Yes or not yet; I
   recommend yes.") and record it as the session's one open ask. Two named types: a question naming both, and no
   proposal. A declared work type: nothing is proposed; one that differs from discovery is kept, and noted once.
2. `steward_owner.py work-type --yes --said FILE --at TIME`: on the person's plain yes to that ask by the `approve`
   rules (one line, no condition, not older than the ask, not in the future, no older than four times `[flow]
   owner_wait_minutes`, the data guard passes, the same steward session), in solo mode with one person listed, it
   records the yes, makes the branch `steward/work-type` from the default branch, writes the `[delivery]` line and ADR
   `docs/adr/<next>-work-type.md` (Status Proposed, naming `agk.toml`, quoting the ask and the owner's words), and
   prints the add, commit and push commands. It never commits or pushes; the owner's merge approves it, as for every
   protected change. A dirty work tree or an existing branch is refused and nothing is written. In team mode, in
   personal mode, or without one listed person it prints the change only. `not yet` is recorded and writes nothing; a
   reply with a condition (`yes but ...`) is refused. A steward the supervisor started (`AGK_STEWARD_START=conductor`)
   writes nothing.
3. `engines.py stack-write` refuses, naming `delivery.work_type` and never the value, while a discovery document names
   a work type other than `pilot` and none is declared. With no discovery document, one at `pilot`, or a declared work
   type, it writes as today.
4. `doctor.py` prints one `warn work type: ... (setting: work_type)` line when discovery names an undeclared work type,
   and one `note work type: ...` line when the declared one differs; neither changes the exit code.
5. The reader of the discovery documents is `playbook_format.discovered_work_types`, in an installed module, so the
   installed `doctor.py` and `steward_owner.py` read it without the kit-only `engines.py`.
6. Amendment 218 (`docs/runs/proposed-spec-amendments-218.md`) proposes the SPEC-0038 rule 5 text for items 2 and 3;
   the spec is unchanged until it is approved.

## Consequences

On the idea path the owner's one step to switch on a playbook is a plain yes and a merge. Until amendment 218 is
approved the `--yes` write stands only on this Proposed ADR, so it is the maintainers' choice to accept both together.

## Residual

- Q-1757-1 (the brief's `Q-W2-1`, 2026-11-22): `stack-write` refuses rather than reading discovery's proposed work
  type, the conservative reading; a proposed type never selects a playbook.
- 2026-11-22: two named work types get a question and no recorded ask; the owner's choice between them is not yet
  written by the steward.
- 2026-11-22: the steward's role file does not name `work-type` yet; it is outside this brief's `Touches:`.
