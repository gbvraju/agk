# ADR-0773: An adopted project can require each file a change edits to meet the standards pack

- Status: Proposed
- Date: 2026-11-23
- Deciders: maintainers
- Related: brief #1844, brief #1837, brief #1771, ADR-0666, ADR-0669, ADR-0680, ADR-0681, ADR-0702, ADR-0743, ADR-0766, ADR-0111, SPEC-0072, plan #661
- Requirements: REQ-079

Protected classes: `scripts/agk/`, `kit/`, `tests/kit/`

## Context

SPEC-0072 rule 7 holds an adopted project to its baseline: a count may only fall or hold. A file a change edits keeps
its baselined findings for ever (AD-09 on #1771: `src/pages/home.ts` was edited with its format fault left and passed
`standards node format (baseline)`). The runner never knows which files the change touched.

## Decision

1. **The setting.** A new optional top-level key `touched_files` in `agk.toml`, read by `config.touched_files`:
   absent or `"hold"` (the default) is rule 7 exactly as before, with no git read; `"meet"` makes the pack's
   `lint`, `format` and `type` steps (rule 6) read the baseline line of a file the change touches as 0 for that run,
   so a finding left in it fails with `standards <stack> <step>: SPEC-0072 rule 7: a file this change touches must meet
   the pack (setting: touched_files)`, exit 1, naming no file and no count. Any other value, or one that is not a
   string, is refused `not an accepted value (setting: touched_files)`. The run writes no baseline line; a clean file
   prints today's `a count fell` note and the next build's lowering commit removes its line.
2. **Touched.** The paths `common.changed_files` gives from the merge base of `common.resolve_base` (`--base`,
   `AGK_BASE` (in CI the merge ref's first parent, ADR-0111), `GITHUB_BASE_REF`, the default branch) to the working
   tree, less deletions, `\\` read as `/`; never the brief's `Touches:` line (no network in checks; SPEC-0003 F7
   already keeps the change inside it). With no base outside CI, or a tree with no `.git` (the personal floor's
   `git archive` tree), the runner prints `not run standards touched: no base (setting: touched_files)`, named in the
   last line, and no-rise holds; in CI with no base, today's `no base ref resolves in CI` is one failure row.
3. **Scope.** Only the pack steps of rule 6; the floors, the counted gates of rules 3 and 5 and the `HELD` steps
   `secrets` and `licences` keep no-rise under either value (`Q-HK-3`). The adoption run that writes a baseline is
   green under either value; `mode = "init"` has no baseline, so the value has no effect there.
4. **The spec.** The key is new to an Approved spec, so `docs/runs/proposed-spec-amendments-221.md` proposes one
   sentence for rule 7 and one row for rule 9's table; the reviewers approve it (principle 6). The default stays
   `"hold"` until the owner rules `Q-HK-1`.

## Consequences

No project's result changes until it sets `"meet"`; one that does holds every file it edits to the full pack, so the
code people work in improves build by build. One `git diff` per run with `"meet"`. `kit/templates/agk.toml` names
the key in a comment; `docs/guides/reference.md` describes it.

## Residual

- 2026-11-23: `Q-HK-1` (whether `"meet"` becomes the default) is the owner's; a later brief flips it after the amendment
  (due 2027-01-31).
