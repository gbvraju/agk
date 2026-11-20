# ADR-0652: The personal reviewer agent file is pinned to LF in the installed gitattributes (REQ-039)

- Status: Proposed
- Date: 2026-11-19
- Deciders: maintainers
- Related: brief #1559, brief #1507, #1550, ADR-0160, ADR-0641
- Requirements: REQ-039

Protected classes: `kit/`

## Context

The default branch is red at 3c383bd, the merge of #1550 (brief #1507). That change installs a new verbatim file,
`.claude/agents/personal-reviewer.md` (listed in `kit/manifest.json`), without the `text eol=lf` line that ADR-0160
gives every file the kit installs. Governance fails on one test,
`tests/kit/test_windows_install.py::test_the_installed_gitattributes_pins_lf_for_every_path_the_kit_installs`
(run 44610532832). It is the only installed path without the line.

## Decision

1. `kit/templates/gitattributes` gains `.claude/agents/personal-reviewer.md text eol=lf`, in name order after the
   `drift-auditor.md` line. Nothing else in the file changes.
2. The test is not changed: it already states the rule and found the gap.

## Consequences

The default branch turns green. A Windows checkout of the personal reviewer agent keeps LF line ends, so the doctor
and an upgrade read an untouched copy as untouched. No behaviour a project runs changes otherwise.

## Residual

None.
