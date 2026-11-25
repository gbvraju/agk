# ADR-0808: The architecture record holds quality scenarios, threats and operations, and the stack record compares designs per layer

- Status: Proposed
- Date: 2026-11-25
- Deciders: maintainers
- Related: SPEC-0073, SPEC-0072, ADR-0675, ADR-0668, ADR-0677, ADR-0793, ADR-0801, brief #1952, brief #1933, plan #661
- Requirements: REQ-080

Protected classes: `scripts/agk/`, `kit/`, `skills/`, `tests/kit/`, `docs/specs/`, `agk.toml`

## Context

SPEC-0073 (Approved) rule 8, "Architecture: decided on day 1", and rule 15 build (g); amendment 236 to SPEC-0072
rule 5, approved by the owner on #1920 (comment 7172944626, `Maintainer answer: amendment 236 approved`). Before this
change, on the default branch at 312343b1, `front_door.record_problems` read only `NEW_SECTIONS` and `## Layers`: a
record with `## Threats` and no `## Quality scenarios` gave `ok architecture-record`, and no check held a threat, a
quality number or what is watched. The v1 acceptance run (#1772, CM-12) found the three pilots' records without them.

## Decision

1. `front_door.py` gains `QUALITY_SECTIONS = ("Quality scenarios", "Threats", "Operations")`, apart from
   `NEW_SECTIONS` and `RECORD_SECTIONS`, which are unchanged, and `quality_held(text)`: true for a record that holds
   none of them (`Q-73G-2`). A record that holds one or more is checked whole by `record_problems`: each missing
   section, a `TODO(architect)` marker in one, a section with no `- ` line, a line out of its form, and fewer
   scenarios than `## Needs` lines that hold a number each fail naming `SPEC-0072 rule 5` and the section, never a
   value (principle 8). `record_held` and its exemption are unchanged.
2. The forms, read by form only (`Q-73G-4`): `- <attribute>: <stimulus> -> <response> (<number>)` with `<attribute>`
   one of the eight quality characteristics of ISO/IEC 25010, by name only; `- <flow>: <letters>: <mitigation>` or
   `...: accepted: <reason>`, the letters a non-empty subset of `S T R I D E`, none twice; `- traced: ...` or
   `- alerted: ...`. Whether a mitigation is good stays the reviewer's.
3. `kit/templates/architecture.md` carries the three sections after `## Diagram`, each one `TODO(architect)` line;
   `layers.py --write-record` writes them as it writes the others and refuses a template that lacks one of
   `QUALITY_SECTIONS` (`kit/templates/`), so the template, the writer and the check read one tuple.
4. The hold is printed by a new step `architecture-quality` (`scripts/agk/gates/architecture_quality.py`, installed,
   the runner's interface `RULE`, `check`, `skipped`, `applies`), the third of `run_gates.ARCHITECTURE_STEPS`. It
   applies only where the record holds none of the quality sections and then prints
   `not run architecture-quality: the record predates its quality sections; held until its next edit`, never `ok`; a
   held record prints both `not run` lines. `architecture_record.py`'s interface is unchanged. `check-design` prints
   the same hold as a note.
5. `skills/stack/SKILL.md` step 2: with more than the single default layer `src` in `[architecture] layers`, the
   skill compares `[quality] designs` interface designs for each layer (one with `designs = 1`, said so), keeps the
   chosen one in the option and the rejected one in a `## Designs compared` section of the stack ADR after
   `## Decision`, outside the `- Option` bullets (`Q-73G-3`); `kit/templates/stack-adr.md` carries that section empty.
   `pins.OPTION`, `pins.CHOSEN` and `front_door.chosen_services` read the same option with it present.
6. Amendment 236 items 1 and 2 are applied word for word to SPEC-0072 rule 5.

## Consequences

Every record written from now on carries quality numbers, threats and operations, and its first edit must fill them;
records written before print one more `not run` line until their next edit. No workflow, label, required check,
`agk.mk` recipe or setting changes; the step runs the same in `prepush.py`, `make governance` and the `proof` job, and
reads files only. `kit/hashes.json` and the version stay the release's.

## Residual

- 2026-11-25: whether each data flow of `## Diagram` has a `## Threats` line is not checked (form only); the reviewer reads it.
