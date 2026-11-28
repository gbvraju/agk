# ADR-0875: The rule set is grounded by one skill over the existing tools

- Status: Proposed
- Date: 2026-11-28
- Deciders: maintainers
- Related: ADR-0310, ADR-0404, ADR-0188, ADR-0212, ADR-0243, ADR-0309, ADR-0582, ADR-0583, ADR-0726, ADR-0851, ADR-0852, SPEC-0030, SPEC-0059, REQ-037, brief #2094
- Requirements: REQ-037

Protected classes: `skills/`, `.claude/`, `config/`, `tests/kit/`, `tests/kit_dev/`, `agk.toml`

## Context

The rule set grows and is never cut. `rules.py consolidate --plan` printed `before: 15691 words, 194 rule lines, 184 in
force` and the same `after:` on main 905e01c: `config/rule-plan.txt` has held only its header since ADR-0404, so
`consolidate --apply` has never run. The measures exist (`rules.py budget`, `dropped`, `consolidate`, `core_audit.py`,
`drift_audit.py`, `metrics.py --signals`, the consistency test's `EXPECTED` table), but no step runs them, and
`steward_evidence.py skill --step "grounding the rules"` printed `no skill:` and exited 3.

## Decision

1. `skills/ground/SKILL.md` (`/agk:ground`, `disable-model-invocation: true`) joins the measures into six steps:
   measure, sort every rule into one of five classes (checkable, judgement, duplicate, unused, contradicting), plan in
   a scratch copy in the existing plan format, one owner packet by `steward_owner.py ask`, apply on the owner's yes by
   one brief and one pull request through `rules.py consolidate --apply`, and re-measure with a `Note: grounding` entry.
   It adds no script, no setting and no plan verb; merges, fixes, bullets and paragraphs are hand edits its packet
   lists (`Q-S6-1`).
2. The steward's table gains `| grounding the rules | \`ground\` |`; the `Skills first.` sentence is cut by the
   row's words, so the file's budget line does not rise (`Q-S6-3`).
3. `unused` needs every count; `unknown` or `cannot-check` is never unused. `core_audit.py` stays kit-only (`Q-680-6`):
   the skill names it only in the installed form and a project marks it `cannot-check (kit-only: core_audit)` (`Q-S6-5`).
4. In a project a plan row on a file the plugin's `kit/manifest.json` lists is a kit finding, sent by
   `steward_evidence.py triage` as an `agk-kit-defect` issue.
5. Its signal of use is `ground-run`, a `comment` row of `config/signals.toml` on `^Note: grounding <date>: `. No
   timer is added (`Q-S6-6`); S2's decisions-in-force index is named only when it merges (`Q-S6-4`).
6. `tests/kit/test_ground_skill.py` holds it, joins the `skills/**` and `.claude/agents/*.md` entries of
   `[[testing.map]]`, and asserts that no kit script but `rules.py` names `config/rule-plan.txt`.

## Consequences

The rule set shrinks only by a plan the owner said yes to, in one pull request with its ADR, and every number keeps a
pointer, so one revert undoes it. No workflow, ruleset, required check, `agk.mk` or governance step changes. The first
grounding run itself is a later brief (S5).

## Residual

The plan format still names numbered rules only; a new verb is a later brief if the first grounding shows the need.
