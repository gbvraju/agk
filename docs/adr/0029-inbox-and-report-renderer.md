# ADR-0029: the decision inbox and the product report renderer (SPEC-0011 (a)), kit 0.15.0

- Status: Accepted
- Date: 2026-10-17
- Deciders: maintainers
- Related: ADR-0021, ADR-0023, ADR-0025
- Requirements: REQ-017, REQ-018

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`, `.claude-plugin/`

## Context

SPEC-0011 (Approved) turns the facts document of SPEC-0009 into two things a person reads: the decision inbox (what waits for a person)
and the weekly product report (five sections). ADR-0025 sets the date that matters: the report reaches the pilot repository by
2026-10-31, so that its first scheduled run is Monday 2026-11-02. This is the first of two pull requests: the pure renderer. The
workflow, the installation by `init`, `adopt` and `upgrade`, and the live proof follow in the second, so that the part that can be
checked by tests alone is reviewed first. Nothing in this pull request runs on a schedule or writes to an issue.

## Decision

1. **`scripts/agk/product_report.py`** is added as specified by SPEC-0011 rules 1 to 14: `--facts FILE [--today] [--week]
   [--inbox | --print-action]`, standard library only, five sections in the order Delivered, Proven, Needs you, At risk, Cost,
   a footer `facts: <commit>`, a dirty notice, `unknown` printed as `unknown`, `nothing this week` for an empty section, every line
   ending with a link, refusals that name a field, an option or a path class and never a value. It is a verbatim kit file (it runs
   without the plugin) and is in the manifest.
2. **`--today` is checked, not defaulted over**: an empty `--today` is a refusal (`option: --today`), not "use the document's date".
3. **The only input is the facts file.** The renderer imports `argparse`, `json`, `re`, `sys`, `datetime` (`date`, `timedelta`),
   `decimal` and `pathlib` and reads one file. `tests/kit/test_product_report.py` proves it three ways: the imports and calls by
   `ast`, an observed run (every `open` and `Path.open` recorded, sockets forbidden, a token in the environment never printed), and
   a run with an empty environment in an empty directory compared with the golden. Criterion e of ADR-0021 rests on these.
4. **Fixtures**: the eleven facts goldens of SPEC-0009 are reused as inputs (no second copy of them); three more are added under
   `tests/kit/fixtures/report/` (`kinds`: one item of every kind of the inbox and every reason of Proven; `quiet`: nothing;
   `dirty-unknown`: a dirty tree and fields marked `unknown`). The goldens are in `tests/kit/fixtures/report/golden/<case>/`;
   `AGK_WRITE_GOLDENS=1` rewrites them and a person reads the diff.
5. **Kit 0.15.0**: `kit/manifest.json` lists the script, the test and the fixtures; `kit/hashes.json` is regenerated; the plugin version
   follows.
6. **SPEC-0011 rule 10 (iv) is amended** (Q-K4-137, item 1 of `docs/runs/proposed-spec-amendments-18.md`, accepted by the maintainers): the
   drift line prints one count for every kind the facts' `drift.counts` holds (`D1` to `D7` today). The interim reading of Q-K4-136 stands:
   an inbox line for a spec or an ADR links the `docs/specs` or `docs/adr` directory at the facts commit, until the facts carry a path
   (residual below); item 2 of the proposal is not applied.
7. **Goldens store `<pr>` in place of the pull request marker** so that installed files stay neutral; the test restores it before
   comparing; nothing is excluded from the neutrality check.

## Consequences

- Nothing runs by itself yet. The second pull request adds the workflow, the notice naming three workflows, the doctor's
  `drift-workflow-state` coverage (an amendment of SPEC-0006, Q-K4-52), `inbox_hours = 48` in the `agk.toml` templates, the live proof
  and the pilot upgrade brief.
- 2026-10-31 is the date to keep. This pull request is on time only if it is reviewed in the days after it is opened and the second
  follows within the week; a verdict of "fix list" on this one moves the second by the same days.
- An installed repository receives the script and its test at its next `agk upgrade`; the test is collected only with
  `AGK_KIT_TESTS=1`, as every kit test.

## Questions

| Q | Question | Reading taken (conservative) |
| --- | --- | --- |
| Q-K4-136 ruled | Rules 3 and 11 want every line to link to evidence, and the facts carry no path for a spec or an ADR. | the line links to `docs/specs` or `docs/adr` at the facts commit (a directory), not to the file; the facts could carry the path (proposal 18, item 2) |
| Q-K4-137 ruled | Rule 10 (iv) names `D1` to `D6`; the facts' `drift.counts` now hold `D7`. | the line prints every kind present, sorted (proposal 18, item 1); an unknown count is `unknown` |
| Q-K4-138 ruled | Rule 9 words a proven line `REQ-001 is proven`; the reader needs the evidence. | `REQ-001 is proven (last change PR #44: proven)` or `skipped (declared unchanged)`; two reasons are added to the rule's four, `it lists no acceptance criteria` and `its acceptance criteria are unknown` |
| Q-K4-139 ruled | `inbox_hours` from the facts is `unknown` when the key is not an integer. | the pull-request group prints one `unknown` line naming `inbox_hours`; no default is invented in the renderer (the 48 comes from the facts) |
| Q-K4-140 ruled | Rules 11 and 16 give no way to print the issue title. | the title is derived by the workflow from the marker line; there is no `--print-title` |
| Q-K4-141 ruled | Rule 11: a footer line for an issue that does not exist. | `metrics: none found` and `drift audit: none found`; `unknown` when `issues` is unknown |
| Q-K4-142 ruled | The Cost totals when one figure is unknown. | the total is `unknown`, never a sum of the known ones |

## Residual

- 2026-10-17: the facts carry a path for each spec and ADR so inbox lines link the file (due 2026-11-30).
- 2026-10-17: the dates `2026-10-31` (the report in the pilot) and `2026-11-02` (its first run) depend on the second pull request;
  no step of it is done here (due 2026-10-31).
- 2026-10-17: the spec's tests of rule 18 for the workflow (`test_product_report_workflow.py`) are not in this pull request; they come
  with the workflow (due 2026-10-31).
