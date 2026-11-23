# Proposed spec amendments 220 (SPEC-0055; REQ-062)

Date: 2026-11-23 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0751 (brief #1792), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0055-the-right-tests-for-each-stack-run-at-the-right-time-by-a-map-that-learns.md` (rule 6). Brief #1792
reserved the number 220 (its `Q-F2-1`, the conservative reading). This file proposes the lines and does not edit the
spec. A later pull request applies them word for word, on the owner's `Maintainer answer: amendment 220 approved`; no
session posts it.

The sentence (brief #1792): "A change of a shipped skill or agent file runs every kit test that reads that file, even
when the test builds its path in parts and the change holds only Markdown, so it fails on its pull request, not on the
default branch."

## What is on the default branch today

Read in the code on main at 3d19d44 (2026-11-23): `impact.name_index` indexes only path-like words of a test file, so
`ROOT / "skills" / "upgrade" / "SKILL.md"` names no file, and `impact.is_doc` is true for every `*.md` file, so a change
of only `skills/upgrade/SKILL.md` gives `docs_only=True` and selects nothing, though `skills/**` is mapped and
protected. Replayed on `ee47218b..11255059` (#1773), the selection does not hold `tests/kit/test_upgrade_adr.py`.

## Items

1. **Rule 6, after its first sentence.** Add: "A test names a path also when it builds it in parts: a run of two or
   more quoted literals joined by `/`, or a `Path`, `PurePosixPath`, `PurePath` or `os.path.join` call whose arguments
   are all quoted literals, the parts joined with `/`; a part with `*`, `?` or `{` ends the path at the folder before
   it. This only adds names (amendment 220)."
2. **Rule 6, at its end.** Add: "Documentation, which selects nothing, is a file under `docs/`, or a `*.md` file that no
   `[[testing.map]]` entry covers and no class of `config/protected-paths.txt` holds; any other `*.md` file is code to
   the selection, so its entries' tests and the tests that name it run, and it is unmapped when neither covers it. A
   change under `docs/` only still selects nothing (amendment 186, Q-1548-3; amendment 220)."

No other rule changes. `docs/guides/testing.md` says the same in its `Documentation` item.
