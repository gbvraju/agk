# Proposed spec amendments 226 (SPEC-0071; REQ-014)

Date: 2026-11-24 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0780 (brief #1886), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0071-the-kit-runs-from-the-plugin-and-a-product-repository-keeps-only-its-project.md` (rule 2). This file
proposes the lines and does not edit the spec. A later pull request applies them word for word, on the owner's
`Maintainer answer: amendment 226 approved`; no session posts it.

The sentence (brief #1886): "The plugin snapshot of a release builds: it ships no tests/kit/ (nothing reads it from the
plugin), and the 32 shipped kit files whose code or fixtures the data guard reads as an address, number or key are
rewritten so the unchanged guard finds nothing; a whole test keeps every shipped file clean."

## Items

1. **SPEC-0071 rule 2, the "In the plugin" item.** Replace "the gate that `make lint` and `make governance` run today,
   and the kit's tests (`tests/kit/`, run against the project's root)." with "and the gate that `make lint` and `make
   governance` run today. The kit's tests (`tests/kit/`) are not in the plugin: nothing reads them there, and the
   kit's own repository runs them (amendment 226)."

No other rule changes.

2026-11-26 (from `date -u`), brief #1966: item 1 (to rule 2) applied to `docs/specs/0071-the-kit-runs-from-the-plugin-and-a-product-repository-keeps-only-its-project.md` word for word, on the maintainer's answer on #1906 (comment 7127025275).
