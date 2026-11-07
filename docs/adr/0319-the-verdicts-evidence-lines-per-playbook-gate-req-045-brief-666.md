# ADR-0319: The verdict's evidence lines per playbook gate (REQ-045, brief 666)

- Status: Proposed
- Date: 2026-11-07
- Deciders: maintainers
- Related: ADR-0251, ADR-0312, ADR-0310, SPEC-0038
- Requirements: REQ-045

Protected classes: `.claude/`, `config/`, `tests/kit/`

## Context

SPEC-0038 rule 12 build (h) builds rule 9: with a declared work type (`[delivery] work_type` of
`agk.toml`, rule 5, built by ADR-0312), the conductor's role file says that a clearing verdict on a
pull request of that project names, in one `Playbook evidence:` line, each `evidence` item of the
playbook that applies to the brief, with where it was read, or `not applicable: <reason>`, and
that a missing judgement gate is a fix item, never a clearing verdict; `check_pr_body.py`,
`proof.py` and the CI proof job do not change, the conductor reads the line (`Q-S0038-10`;
REQ-045 AC3). Brief #666 gives the build and its answer 2: a `judgement` gate names a person's line
or a run record, a `check` gate names the step, and nothing merges on a missing line only when a
work type is declared. ADR-0251 sets the direction and lists `.claude/agents/conductor.md` among
the classes the builds change; ADR-0310 holds the rule budget of `config/rule-budget.txt`, which
only shrinks. This ADR number was reserved for brief #666 by the conductor (the brief's text).

## Decision

1. **The line.** With a declared work type, a clearing verdict carries one line
   `Playbook evidence: <item> (<where>); <item> (<where>); ...`, after the shape of the verdict
   (`Read:` to `Checklist:`) and before the findings, with one `<item>` per entry of `evidence` in
   `config/playbooks/<work type>.toml`, in the playbook's order and with the entry's own words.
2. **Where.** `<where>` is where the conductor read the item: for a `judgement` gate a person's
   line, `comment <id>` (a comment on the pull request or on the brief), or a run record,
   `docs/runs/<file>` of the repository; for a `check` gate the governance step, `step <name>`,
   green on the reviewed head; an item that does not apply to the brief reads
   `not applicable: <reason>`. The form of `<where>` says which kind of gate the item evidences;
   the playbook format ties no `evidence` entry to a gate, and the shipped playbooks list their
   evidence in their gates' order (Q-666-1).
3. **Fail closed, only when declared.** A missing item, or a missing line, on a project with a
   declared work type is a fix item, never a clearing verdict, so nothing merges on a missing
   line. Without a declaration no verdict carries the line and nothing changes (rule 5).
4. **Read by the conductor, never by a check.** `check_pr_body.py`, `proof.py`, `pr_body.py`,
   `route.py`, `merge_cleared.py` and the workflows do not read the line (`Q-S0038-10`); the test
   of this build holds the documented shape itself and reads a verdict fixture with and without
   the gate lines by it, so that the shape the guide documents is the one a reader would parse.
5. **The rule budget.** The paragraph of `.claude/agents/conductor.md` is prose, not a rule
   line, and its words are paid for in the same file by cutting repeated sentences and asides, so
   that the file's word count goes down; `config/rule-budget.txt` lowers the file's line to the
   new count in this pull request (ADR-0310). The rule-line count stays 37.
6. **The guide.** `docs/guides/reference.md` gains one section, `## Playbook evidence`, with the
   line, the forms of `<where>` and one example with invented data.

## Consequences

A conductor on a project with a declared work type writes one more line in a clearing verdict and
asks for a fix list when a judgement gate has no evidence; a project without a work type sees no
change. No script, workflow, check or setting changes, so the proof job and the body check pass
exactly what they passed before, and the line is a review discipline held by the conductor's role
file and a person reading the verdict.

## Residual

- 2026-11-07: the line is not checked mechanically (`Q-S0038-10`); whether a verdict carries it,
  and whether its `<where>` is true, is the conductor's and a person's reading (due 2026-12-31).
- 2026-11-07: the playbook format has no key that ties an `evidence` entry to a gate (Q-666-1); a
  later amendment of SPEC-0038 may add one, and until then the `<where>` form carries the kind (due
  2026-12-31).
