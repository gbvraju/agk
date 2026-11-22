# ADR-0713: In local mode a builder's ready report carries its own evidence record (REQ-039)

- Status: Proposed
- Date: 2026-11-22
- Deciders: maintainers
- Related: ADR-0477, ADR-0510, ADR-0536, ADR-0605, ADR-0710, brief #1713, brief #1706, plan #661
- Requirements: REQ-039

Protected classes this pull request changes: `kit/` (`templates/runtime/builder.txt`) and `tests/kit/`
(`test_runtime_templates.py`). `kit/hashes.json` is not edited by hand.

## Context

`agk.toml` sets `execution = "local"`, and session rule 30 with `docs/guides/local-mode.md` asks each head for a
`prepush.py --record` record and a `Local evidence:` line. The builder's task text, `kit/templates/runtime/builder.txt`,
named neither: its small-machine paragraph says "CI's governance and proof on the head are the gate", which no longer
reports in local mode. On the 13 pull requests merged on 2026-11-22, 11 first verdicts asked for the record (6 as the
only item), and 0 of the 13 ready reports carried one (brief #1713).

## Decision

1. `builder.txt` gains one LOCAL MODE paragraph. It applies where `python3 <kit>/execution.py` prints
   `execution: local`, or an issue titled `Local mode since` is open (the guarded merge's own `local_mode` reading).
2. There, before each ready, fix-list, merge-of-main and CI-fix `Report:`, the builder commits, runs
   `prepush.py --quick --record --body <body file>` under the heavy lock with no FILE (the shared folder and the git
   note), then `evidence.py push --branch <branch>`, puts the `Evidence:` and `Local evidence:` lines in the body and
   in the `Report:`, and posts the record byte for byte in one fenced `json` block of that `Report:`, whether the note
   push passed or was refused.
3. In local mode the gate is the record and the conductor's evidence check (session rule 30). The hosted sentence of
   the small-machine paragraph stays word for word.
4. Edges: a refused `execution` value and a missing gitleaks each give a `Question: ... for the maintainers` instead
   of a ready report (Q-1713-2: a record whose secret scan was deferred is not a ready record); a failed record is
   never posted as ready; a push after the report needs a new record; a `Final:`-only fix list on an unmoved head
   needs none.
5. `pr_mode`, `review_mode`, `[governance] level`, `[flow]` and `[personal]` settings leave the step unchanged; the
   paragraph names none of them. `[kit] layout` resolves each command through `<kit>`. No new `agk.toml` key.

## Consequences

A local-mode head's first verdict no longer has to ask for its record. The runtime texts are not installed
(`test_a_the_kit_installs_none_of_them`), so no `changelog.d` fragment and no project using AGK is affected. Hosted
mode reads as before. `session.py` does not refuse a ready without a record (Q-1713-1: the prompt first, measured on
the next ten local-mode heads).

## Residual

- 2026-11-22: measure the next ten local-mode heads' first verdicts for a record-only item (brief #1713 `Measured:`).
