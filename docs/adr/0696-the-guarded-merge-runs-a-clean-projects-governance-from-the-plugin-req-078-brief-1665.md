# ADR-0696: The guarded merge runs a clean project's governance from the plugin, and its printed ruleset fits

- Status: Proposed
- Date: 2026-11-21
- Deciders: maintainers
- Related: ADR-0611, ADR-0613, ADR-0683, SPEC-0039, SPEC-0071, brief #1665, plan #661
- Requirements: REQ-078

## Context

ADR-0683 decision 1 lets `init` and `adopt --layout plugin` start a project with no `agk.mk` and no `.github/workflows/`.
`merge_cleared.py` `governance_argv` still ran `make -C <tree> -f agk.mk agk-governance`, so the guarded merge of a clean
project printed `make: agk.mk: No such file or directory` and held. `kit_root.gate` (ADR-0611) already gives the plugin's
command; `prepush.py` uses it, the merge did not. And `print_branch_rules` printed a ruleset requiring the `governance`
check, which no clean project reports, so GitHub would refuse every merge (verify: GitHub's refusal of a merge with a
required check that never reported), with scanner, workflow and "CI works without the plugin" lines about files a clean
project never has.

## Decision

1. `governance_argv` reads the merged tree's layout with `kit_root.layout`. An installed tree (or one whose `agk.toml`
   cannot be read) runs exactly today's `make -C <tree> -f agk.mk agk-governance AGK_BASE=<base>`. A clean tree runs
   `kit_root.gate(tree)`, the plugin's `kit_root.py governance`, under the same `lock_argv` and clean environment, with
   `AGK_BASE` in that environment. `kit_root.py` finds its project from its working folder and `lock.py` takes its lock
   folder from its own, so the command is started through a fixed `python -c` that changes into the tree and runs the
   script (`IN_TREE`).
2. Before anything runs, `gate_refusal` holds a clean tree with kit_root's own line, naming the setting and never a
   value: a `[kit] layout` that is neither `installed` nor `plugin` (`layout`), no plugin found (`CLAUDE_PLUGIN_ROOT`)
   and `kit_root.pin_refusal` (`plugin_version`). The hold is `the merge with the default branch fails governance
   (<line>)`; it is not kept as a checked result, so it is judged again on the next run. A failing plugin gate is the
   step `make governance`, as today.
3. `print_branch_rules` takes the layout init or adopt writes (`--layout plugin`). For `plugin` it prints the new
   `kit/templates/branch-rules-clean.txt`, today's rules with the required status check `agk/verdict` (the conductor's
   status on a cleared head, `Q-A-1` read conservatively), then the plugin settings entries without the sentence "The
   repository's checks and CI work without the plugin"; no phase 2 line, scanner exclusions or workflow notices. The
   installed layout prints exactly today's text.
4. Unchanged: `execution` `local` and `hosted` read the same command; `[flow] auto_merge`, `review_mode`, `pr_mode` and
   `required_checks`; personal mode makes no merge call.

Protected path classes changed: `scripts/agk/` (`merge_cleared.py`, `init.py`, `adopt.py`), `kit/`
(`kit/templates/branch-rules-clean.txt`), `tests/kit/` (`test_merge_cleared_clean.py`, `test_clean_init.py`) and
`agk.toml` (the `[testing]` map entry of `merge_cleared.py`).

## Consequences

A clean project's green head can merge through the guarded merge, and the ruleset it is told to apply requires a status
it reports. An installed project sees no change. Tests: `tests/kit/test_merge_cleared_clean.py`,
`tests/kit/test_clean_init.py`.

## Residual

- 2026-11-21: an installed tree with no `agk.mk` still holds as `make governance` (make's own error), not with a line
  naming `agk.mk`; naming it changes the step that dozens of fixture tests read (`Q-1665-1`, due 2027-01-31).
- 2026-11-21: `/agk:ruleset` (`ruleset.py`) still applies the installed rules; a clean project applies the printed text by
  hand (due 2027-01-31).
