# Proposed spec amendments 231 (SPEC-0044, SPEC-0002, SPEC-0001; REQ-051, REQ-010)

Date: 2026-11-24 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0785 (brief #1891), which stays `Proposed` for the maintainers' decision. The paths:
`docs/specs/0044-a-large-test-suite-finishes-sooner-without-removing-a-test.md` (rule 10),
`docs/specs/0002-agk-adopt.md` (rule 9) and `docs/specs/0001-agk-init.md` (rule 14). This file proposes the lines and
does not edit the specs. A later pull request applies them word for word, on the owner's
`Maintainer answer: amendment 231 approved`; no session posts it (`Q-AN-6`).

The sentence (brief #1891): "Adopt and init write the test_patterns of the project's own stack: a Node or TypeScript
project gets its *.test.js, *.spec.js, .jsx, .mjs, .cjs, .ts and .tsx patterns, a mixed one both sets, and a project with
no test and no known stack an empty list, never the Python default."

## Items

1. **SPEC-0044 rule 10, its first sentence.** Replace "the name patterns `*.test.ts`, `*.test.tsx`, `*.spec.ts` and
   `*.spec.tsx`" with "the name patterns `*.test.<ext>` and `*.spec.<ext>` for each of `.js`, `.jsx`, `.mjs`,
   `.cjs`, `.ts` and `.tsx` (twelve patterns), matched with case on every system". Keep "Its output for a project with
   none of them is unchanged" for a Python-only project (amendment 231).
2. **SPEC-0002 rule 9, "with no match the defaults apply".** Replace with: "with no match, the stacks whose manifests of
   the kit's `config/stack-signals.toml` the tree holds give the patterns: a Python manifest `["test_*.py"]`, a
   `package.json` the web patterns of SPEC-0044 rule 10, both give both, and neither gives `test_patterns = []` with
   `test_dirs = ["tests"]`, which adopt names in one line (setting: `test_patterns`). A stamped `test_dirs` or
   `test_patterns` that is not a list of strings is refused before any write, naming the setting" (amendment 231).
3. **SPEC-0001 rule 14, after "`test_dirs = ["tests"]`".** Add: "and, when the target holds a test file or a stack
   manifest whose patterns are not all Python names, a `test_patterns` line with the patterns adopt would detect
   (SPEC-0002 rule 9); an empty repository, or one whose patterns are all Python names (`test_*.py`, `*_test.py`),
   gets no such line" (amendment 231).

No other rule changes.
