# ADR-0784: A TypeScript product with the stock typescript-eslint config meets the Node pack's lint floor

- Status: Proposed
- Date: 2026-11-24
- Deciders: maintainers
- Related: brief #1890, brief #1764, brief #1766, brief #1837, brief #1771, ADR-0739, ADR-0740, ADR-0766, ADR-0773, SPEC-0072, amendment 230, plan #661
- Requirements: REQ-079

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

SPEC-0072 rule 8 accepts a team's ESLint configuration only when the Node pack's `floor` step shows that it enables every
rule code of the pack's list (ADR-0739). typescript-eslint's stock sets turn some of those core rules off: its
`eslint-recommended` block (8.46.2, `@typescript-eslint/eslint-plugin/dist/configs/eslint-recommended-raw.js`, files
`**/*.ts`, `**/*.tsx`, `**/*.mts`, `**/*.cts`) turns off 18 core rules "already handled by TypeScript", each commented
with its compiler code, and turns `no-var` on; its `recommended` set turns `no-unused-vars` off for every file and
`@typescript-eslint/no-unused-vars` on. So the stock `tseslint.config(js.configs.recommended,
...tseslint.configs.recommended)` raised the adopted sample's held floor from 1 to 19 lines and failed rule 7 (AD-03 on
#1771). ADR-0739's first Residual line left `Q-1764-1` open: whether a replacement rule counts; until answered, it did
not.

## Decision

1. **The table.** `scripts/agk/gates/node_pack.py` gains a fixed constant `EQUIVALENT`, kit code and never a setting
   (`Q-TL-1`): for each floor rule typescript-eslint replaces, what else meets it. Rule rows: `no-unused-vars` by
   `@typescript-eslint/no-unused-vars`, `no-redeclare` by `@typescript-eslint/no-redeclare`, `no-dupe-class-members` by
   `@typescript-eslint/no-dupe-class-members`, each on at `error` or `warn`, never `off` or `0`. Compiler rows, with the
   codes of the source file's comments: `constructor-super` (TS2335, TS2377), `getter-return` (TS2378),
   `no-class-assign` (TS2629), `no-const-assign` (TS2588), `no-dupe-args` (TS2300), `no-dupe-class-members` (TS2393,
   TS2300), `no-dupe-keys` (TS1117), `no-func-assign` (TS2630), `no-import-assign` (TS2632, TS2540),
   `no-new-native-nonconstructor` (TS7009), `no-obj-calls` (TS2349), `no-redeclare` (TS2451, with `no-var` on),
   `no-setter-return` (TS2408), `no-this-before-super` (TS2376, TS17009), `no-undef` (TS2304, TS2552), `no-unreachable`
   (TS7027, with `allowUnreachableCode` false), `no-unsafe-negation` (TS2365, TS2322, TS2358), `no-with` (TS1101,
   TS2410). No row for any other code, and no row removes a code from `rules.codes`: every floor code is still judged.
2. **When the compiler counts** (`Q-TL-3`). Only when the file the floor read is `.ts` or `.tsx`, a `tsconfig.json`
   exists and the product's `tsc` is installed, and the root `tsconfig.json` or one of its `references` both meets the
   type floor (`strict` true, `noImplicitAny` and `strictNullChecks` not false, in its options merged through
   `extends`) and lists the file in `tsc --listFilesOnly -p <config>` (argument list, no shell; paths read as `_rel`
   reads them, compared case-insensitively on Windows), and the row's extra condition holds (`allowUnreachableCode`
   false in that config's merged options; `no-var` on in the printed configuration). The `node-type` step then runs that
   compiler over that file, so the code is caught as an error. A `.js`, `.jsx`, `.mjs` or `.cjs` file never meets a
   rule by the compiler; a listing that fails or prints nothing meets none (the safe side).
3. **The lines.** A floor rule is met when it is on or a row meets it; otherwise one line as before, naming the core id
   and what would meet it, never a file or a value: `SPEC-0072 rule 8: the configuration does not enable the pack's rule
   no-unused-vars or @typescript-eslint/no-unused-vars (setting: standards.config)`; for a compiler row `... rule
   no-unreachable, or the compiler with allowUnreachableCode off for a file a strict tsconfig.json checks (setting:
   standards.config)`. Still one line per unmet floor rule, so the tally `{"package.json": n}` and `run_gates.py` are
   unchanged (`Q-TL-6`), and a held count can only fall.
4. **`Q-1764-1`.** This ADR answers it: a replacement rule at `error` or `warn` counts for the core rule it replaces,
   only for the rows above. The answer stands when the maintainers accept this ADR, never by the build.
   `noUnusedLocals` and `noUnusedParameters` do not meet `no-unused-vars` (`Q-TL-4`).
5. **The spec.** The equivalent is new to SPEC-0072 rule 8 ("enables every rule code"), so
   `docs/runs/proposed-spec-amendments-230.md` proposes the rule 8 wording; the spec text is not edited here and the
   reviewers approve the amendment (principle 6, `Q-TL-2`).

## Consequences

On the brief's sample with the real tools (ESLint 9.39.1, typescript-eslint 8.46.2, TypeScript 5.4.5) the stock config
with a strict `tsconfig.json` gives 1 floor line (`no-unreachable`) for a `.ts` file and 0 for a `.js` test file, and 0
and 0 with `allowUnreachableCode: false`; without `js.configs.recommended`, 43 and 42. Two compiler gaps stay named:
unreachable code is no compiler error unless `allowUnreachableCode` is false, and a repeated `var` is none (TS2451 covers
`let` and `const`), so `no-redeclare` needs `no-var` on. A plain JavaScript product is judged as before but for
`no-unused-vars`, which its TypeScript rule now meets. One more `tsc --listFilesOnly` run per configuration per gates
run, only when the floor reads a TypeScript file with a compiler row unmet by its own rule. The floor still reads the
first readable file only (`Q-TL-5`); `ESLINT_USE_FLAT_CONFIG` is not set by the pack (`Q-TL-7`).

## Residual

- 2026-11-24: ADR-0739's first Residual line (`Q-1764-1`) is answered by decision 4 when this ADR is Accepted; ADR-0739's
  text is left as it is (an Accepted record).
- 2026-11-24: a later companion config that replaces a floor rule joins `EQUIVALENT` by one row in its own brief and ADR;
  the test asserts each key is a floor code of both playbooks and each compiler code is `TS<n>`.
- 2026-11-24: `Q-TL-8` (verify): the `--listFilesOnly` path form on Windows was not run (no Windows machine).
