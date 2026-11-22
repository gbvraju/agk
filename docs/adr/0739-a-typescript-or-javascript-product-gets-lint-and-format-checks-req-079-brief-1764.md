# ADR-0739: A TypeScript or JavaScript product gets lint and format checks from a standards pack (REQ-079)

- Status: Proposed
- Date: 2026-11-22
- Deciders: maintainers
- Related: SPEC-0072 rules 2, 6, 7 and 8, ADR-0665, ADR-0669, ADR-0702, brief #1764, plan #661
- Requirements: REQ-079

Protected classes this pull request changes: `scripts/agk/` (the new `gates/node_pack.py`, `run_gates.py` and
`playbook_format.py`), `config/` (`config/playbooks/web-app.toml`, `config/playbooks/mobile.toml`), `agk.toml` (the
`[[testing.map]]` entries), `tests/kit/` (the new `test_node_pack.py`, `test_python_pack.py`, `test_product_deps.py`,
`test_playbook_standard.py`) and `kit/` (`kit/manifest.json`, the new installed file). `kit/hashes.json` is not edited
by hand.

## Context

On main at 7306a8b (2026-11-22; the brief read b4a865c9) `run_gates.py` holds `PACKS = ("python_pack",)`, so a project
whose Accepted stack record chose Node prints `not run standards: no pack for node` (ADR-0702) and its code gets no
check from the kit. `gates/pins.py` already knows the `node` stack and holds its `devDependencies` exact. ADR-0665's
format requires a `version` in a pack's `rules` table; the Python pack's version pins ruff from `config/ci-tools.txt`,
while a Node pack's tools are the product's own pinned copies, so the kit has no version of its own to name, and the
`mobile` playbook's own test refuses any version number in that file.

## Decision

1. A new pack `scripts/agk/gates/node_pack.py` serves the stack `node`. It is on only when the one Accepted stack record
   chose a Node runtime (`pins.chosen`) and the product has a `package.json`; otherwise ADR-0702's line stands, so a
   Node record without a build file is never silent. `run_gates.py` `PACKS` gains `node_pack`.
2. It reads the `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs` and `.cjs` files of `project_lint_paths` (unset: the layers'
   paths, the Python pack's own reading), less hidden folders, `node_modules/`, `build`, `dist`, `out`, `coverage`,
   `vendor`, `third_party` and the kit's `lint_paths`; paths compare by forward slash.
3. Its steps run the product's `node_modules/.bin/eslint` and `prettier` with an argument list, never a shell, `npx` or
   a download: `floor` (`eslint --print-config <file>` shows every id of `rules.codes` at `error` or `warn`; each one
   `off` or absent is named), `lint` (`eslint --max-warnings 0 --format json`; ESLint's "File ignored" notice for a file
   the config's `ignores` names is not counted) and `format` (`prettier --check`). A missing tool fails naming the
   tool, the setting and `npm ci`, never a version; a tool that does not report is a failure, never a pass. Lines name
   the rule id or the format and the path class, never a file or a value. `lint` and `format` report per-file counts
   for the baseline (rule 7). The `node-type` step is the brief's part 2; the entry names it and this pack runs none.
4. `web-app.toml` and `mobile.toml` each gain one `[[standards]]` entry: `stack = "node"`, steps `node-lint`,
   `node-format`, `node-type`, `config = "package.json"`, `rules = { tool = "eslint", codes = [...] }`, the codes being
   the rules of `eslint:recommended` that are on by default (Q-B4-1, the conservative reading).
5. ADR-0665's `rules` table: `version` becomes optional (`playbook_format.py`), so a pack whose tools are the
   product's own pins names none; `tool` and `codes` stay required and the Python entries keep their version.

## Consequences

A Node product's code is red on a planted lint fault, an unformatted file or a configuration that turns a floor rule
off, inside the existing `governance` job, `make governance` and `prepush.py`, with no workflow or ruleset change. A
Python product is unchanged. A TypeScript product that follows typescript-eslint's own advice to turn some core rules
off fails the floor on those rules; see the residual.

## Residual

- 2026-11-22: Q-1764-1, whether a core rule that typescript-eslint replaces (for example `no-unused-vars` by its own
  rule) counts as on for the floor; until the maintainers answer, it does not.
- 2026-11-22: the rule ids of the floor were written from ESLint 9's `eslint:recommended` (verify) without a network
  read in this session.
