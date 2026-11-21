# ADR-0668: The architecture record, the layer import check and the Layer: line (REQ-079)

- Status: Proposed
- Date: 2026-11-21
- Deciders: maintainers
- Related: SPEC-0072, SPEC-0048, SPEC-0030, brief #1588, brief #1586, brief #1587, plan #661, ADR-0665, ADR-0666, ADR-0667
- Requirements: REQ-079

Protected classes this pull request changes: `scripts/agk/` (the new `gates/layers.py`, `run_gates.py`, `check_brief.py`), `tests/kit/` (the new
`test_layers_step.py`, and `test_installed_imports.py`, which now counts an installed package by its folder),
`tests/kit_dev/` (`test_kit_manifest.py`, `test_reference_commands.py`, `test_init.py`, `test_adopt.py`), `kit/` (the new
`kit/templates/architecture.md`, the four project templates of protected paths and reviewers, the two first ADRs
(`adr-0001.md`, `adr-0001-adopt.md`, which name every protected path),
`kit/templates/runtime/builder.txt`, `kit/manifest.json`) and `agk.toml`
(`[[testing.map]]` entries). No playbook changes. `kit/hashes.json` is not edited by hand.

## Context

SPEC-0072 (Approved, REQ-079) rule 12 build (d) builds rule 5 and rule 8's `Layer:` line: the foundation build writes
`docs/architecture.md` from a template, a `layers` step fails an import between layers that `[architecture] allow`
does not list, the record joins the project's protected paths, every build brief of a work-type project after the
foundation names its layers, and the builder's prompt names the record and the pack. On the default branch at
f5c1c29c (2026-11-21) none of these exist. `default.toml`'s gates are exactly SPEC-0048 rule 21's five and ADR-0665's
eight enterprise gates (`tests/kit/test_playbook_default.py`), and no playbook names a `layers` gate.

## Decision

1. The `layers` step is a step of the composed `[architecture]`, not of a gate: `run_gates.py` runs each step of
   `ARCHITECTURE_STEPS` (`layers`) after the check gates, under its own name, where its `applies(root)` is true (two
   or more composed layers). No playbook gains a gate, so SPEC-0048 rule 21's base is unchanged, and `default.toml`'s
   one `src` layer (the kit's own repository, a project with no work type) runs nothing: its output is unchanged.
2. `scripts/agk/gates/layers.py` reads each `.py` file of a layer of the composed `[architecture]` (the first layer
   whose glob matches, paths by forward slash), resolves its `import` and `from` lines, relative ones included, to a
   module path, and fails on one that lands in another layer with no `allow` entry from the first to the second. The
   path class it returns is `<layer glob>; layers: <from> to <to>`, so the runner's line names the rule, both layers
   and the path class, never a file, a module or a value. A file it cannot parse fails naming its layer's glob.
3. A step module may return `(rule, path class)` pairs and may expose `skipped(root)`; the runner prints `not run
   <id>: <reason>` for a skipped step, never `ok`, and ends `ok gates (<n> check gates; not run: <ids>)`. `layers` is
   skipped with `no reader for <stack>` when the Accepted stack record (`gates/pins.py` `chosen`) names a runtime
   other than Python (brief #1588 `Q-1`); with no record chosen it reads Python, the one reader that exists.
4. `layers.py --root DIR --write-record` writes `docs/architecture.md` from `kit/templates/architecture.md` once
   (the layers and their paths, the allowed directions and the stack record's ADR number, or `none chosen yet`), is
   refused naming the setting `work_type` with no work type, and never overwrites a record.
5. `docs/architecture.md` is added to the four project templates (`protected-paths.txt`,
   `protected-paths.adopt.txt` and `classes.protected.paths` of `reviewers.yaml` and `reviewers.adopt.yaml`), so a
   project's record changes only by its own ADR; an existing project receives it by `/agk:upgrade`'s template line.
   The kit's own list does not gain it (the kit has no architecture record, and `.github/CODEOWNERS` is unchanged):
   REQ-009 AC2's equality test leaves it out of the kit's list as it leaves out `project.mk`.
6. `check_brief.py --root` refuses, naming `SPEC-0072 rule 8` and never a value, a brief of a project with a
   declared work type that is not `Kind: foundation` and has not exactly one `Layer:` line, names a layer the
   composed `[architecture]` does not hold, or leaves out a layer whose glob a `Touches:` entry meets
   (`Q-S0072-15`). The rule needs the root, so it lives beside `screens_problems` in `check_brief.py`, not in
   `session.py` `brief_problems`, which has no root.
7. The builder's task text (`kit/templates/runtime/builder.txt`) tells a builder of a work-type project to read
   `docs/architecture.md` and the chosen stack's pack before writing code. `.claude/agents/builder.md` is unchanged:
   it holds no rule of its own and points to that text, and its rule budget (`config/rule-budget.txt`) only goes down.

## Consequences

A project's governance is red when its code imports across layers against its architecture, naming both layers; a
non-Python project sees `not run` until its reader is built. A build brief of a work-type project names its layers.
The kit's own governance output is unchanged. No workflow, ruleset, required check or `agk.mk` changes.

## Residual

- 2026-11-21: `[testing] always_full` does not yet gain `docs/architecture.md` (SPEC-0072 rule 9): each playbook's own
  `[testing]` is written into the project's `agk.toml`, whose non-infrastructure entries need a `# full:` reason;
  brief #1588 `Q-1588-2` (due 2027-01-31, with build (e)'s pack configuration files).
- 2026-11-21: readers for `node` and the other stacks, one per pack build (SPEC-0072 Residual, due 2027-03-31).
