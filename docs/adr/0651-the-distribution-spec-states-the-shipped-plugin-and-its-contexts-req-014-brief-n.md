# ADR-0651: The distribution spec states the shipped plugin and its contexts, so its pending amendments apply (REQ-014)

- Status: Proposed
- Date: 2026-11-19
- Deciders: maintainers
- Related: SPEC-0005, amendment 188, amendment 113, amendment 142, brief #1551, brief #1507, #1550, Q-1507-1, Q-1518-1, ADR-0612, ADR-0641, plan #661
- Requirements: REQ-014

Protected classes the build of this decision changes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `skills/`. This
pull request changes none of them.

## Context

SPEC-0005 rule 7 says the plugin ships no hook and no agent. On the default branch at 3c383bd3, `.claude-plugin/plugin.json`
registers two hooks (`PreToolUse` with `onFailure: block`, and `Stop`, both running `.claude/hooks/plugin_hooks.py`) and
lists seven agents: the six role agents of ADR-0612 decision 1 and `personal-reviewer` (#1550). Rule 15's third bullet,
rule 19's test list, `docs/guides/reference.md` and `skills/review/SKILL.md` repeat the old footprint.

Two pending patches to rule 7 cannot be applied. `check_specs.py` `contexts_failures` (amendment 142 item 2) refuses any
change to an Approved spec without a `## Contexts` section, and SPEC-0005 has none. Applying amendment 113 item 5 to rule 7
on a probe tree fails with `spec 'docs/specs/0005-distribution.md' Contexts section: rule 4: no section` (reproduced
2026-11-19). Build (i) of SPEC-0041 left item 5 out (Q-1507-1 on #1550), and the owner ruled it goes to a later build
(2026-11-19T17:16Z, quoted as data in brief #1551). Q-1518-1's one-line patch for the hooks (#1519) was never answered.
Item 5 also no longer matches the code: it keeps "the plugin still ships no hook".

Every installed project runs the same check on its own specs (`check_specs.py` and the spec template are `verbatim` in
`kit/manifest.json`), and its message names `rule 4`, the kit's SPEC-0030 rule, not a rule of the project.

## Decision

1. SPEC-0005 changes only through amendment 188, which this intake writes and does not apply. It gives SPEC-0005 its
   `## Contexts` section (item 1) and rewrites rule 7 (item 2), rule 15's third bullet (item 3) and rule 19's footprint
   test (item 4) to the plugin as it ships. Item 2 replaces amendment 113 item 5 and Q-1518-1's patch, and item 5 marks
   amendment 113 item 5 and its item 9 test line as replaced.
2. Build (a), filed later by the `brief` skill, applies amendment 188 word for word on the owner's `Approve: SPEC-0005`,
   corrects the reference guide's trust bullet and the review skill's reviewer line, and pins the texts and the plugin's
   footprint in `tests/kit_dev/test_distribution.py`.
3. Build (a) also makes the message of `contexts_failures` for a missing section say where the fix is: `spec '<path>'
   Contexts section: rule 4 (amendment 142): no section, add one with kit, github, local, personal and stacks as the
   spec template lists them`, naming `docs/specs/TEMPLATE.md` only when that file exists in the repository. It still
   names the rule and the path, never the spec's text. The rule itself does not change, so SPEC-0030 is not amended.
4. The 15 other Approved specs that have amendments waiting on the same rule get their sections in one later intake (Q-1),
   not here. Until then each waiting amendment stays unapplied. The 35 Approved specs with nothing pending stay as
   amendment 142 item 2 says: not refused until next amended.

## Consequences

- With amendment 188 applied, rule 7 states what `plugin.json` registers, and the pending patch of Q-1518-1 is settled
  by the owner's approval of the amendment, not by a session.
- A project sees no change in what passes or fails. Its own Approved specs meet the rule on their next amendment as today.
  Build (a) only makes the message say how to fix it.
- No workflow, ruleset, required check, secret or GitHub API call changes. No project file is rewritten by an upgrade.

## Residual

- 2026-11-19: 15 Approved specs still have amendments waiting on the Contexts rule, until the intake of Q-1 lands (due 2026-12-31).
- 2026-11-19: no doctor or brief-time warning names an Approved spec without the section (Q-3, Q-4). Revisit with the
  intake of Q-1 (due 2026-12-31).
