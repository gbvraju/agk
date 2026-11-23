# ADR-0740: A TypeScript product's types are checked in strict mode, and a weakened compiler setting is refused (REQ-079)

- Status: Proposed
- Date: 2026-11-22
- Deciders: maintainers
- Related: SPEC-0072 rules 6, 7 and 8, ADR-0739, brief #1766 (part 2 of 2; part 1 brief #1764), plan #661
- Requirements: REQ-079

Protected classes this pull request changes: `scripts/agk/` (`gates/node_pack.py`, `run_gates.py`) and `tests/kit/`
(`test_node_pack.py`). `kit/hashes.json` is not edited by hand.

## Context

On main at ab649c8 (2026-11-22) the Node pack (ADR-0739) runs `floor`, `lint` and `format`; the `node-type` step that
its `[[standards]]` entry names runs nothing. The Python pack's `type` step runs mypy with strict flags, so a Python
product's types are checked and a Node product's are not.

## Decision

1. When the product files of the pack hold a `.ts` or `.tsx` file, the pack adds two steps after `format`:
   `type-floor` and `type`. Without one, both are skipped and the pack prints one note, `standards node: the type step
   is skipped: no TypeScript file`; neither `tsc` nor `tsconfig.json` is then needed.
2. `type-floor` (rule 8) reads the product's `tsconfig.json` as JSON with comments and trailing commas, merges
   `compilerOptions` over its `extends` chain (a string or a list; later wins), and judges the root config and each
   config its `references` name: each must have `strict` set to `true`, and neither `noImplicitAny` nor
   `strictNullChecks` may be `false`. Each option that fails is named with the path class (`tsconfig.json` or
   `tsconfig.json references`), never its value. A missing root `tsconfig.json` fails naming that class. A relative
   `extends` is read inside the product; a package `extends` is read from `node_modules/` when it is installed,
   otherwise it is skipped and the product's own files alone are judged; a path that leaves the product is never read.
   The floor is its own step and has no tally, so a baseline never holds it.
3. `type` runs the product's own `node_modules/.bin/tsc --noEmit --pretty false -p <config>` for each config of (2),
   with an argument list, never a shell, `npx` or a download. Each error is named by its `TS<n>` code and the path
   class of the file (the `project_lint_paths` glob, else the config's class), never a file or message. An exit that
   is not 0 with no error line fails as a tool that did not run. Per-file counts fill the `type` tally for the baseline
   (rule 7).
4. A missing `tsc`, with TypeScript files present, fails naming the tool, `standards.type` and `npm ci`.
5. `run_gates.py` prints a pack step named `note` as note lines, never as a failure.

## Consequences

A Node product with TypeScript files is red on a planted type fault, a missing `tsconfig.json` or a weakened compiler
setting, in the existing `governance` job, `make governance` and `prepush.py`, with no workflow or ruleset change. A
JavaScript-only product and a Python product are unchanged. A product that adopts the pack can hold its type count by
the baseline, as it can for lint and format.

## Residual

- 2026-11-22: a solution-style root config (`"files": []` with `references`) is judged too, so it must set `strict`
  itself (the conservative reading; brief #1766 answer 6 names the referenced configs only).
- 2026-11-22: `tsc --pretty false` prints `path(line,col): error TS<n>:` (verify); the tests use a stand-in compiler.
