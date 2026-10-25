# ADR-0141: the pipeline document of the router (brief #213 build (b), SPEC-0036 rules 2 to 5 and 7)

- Status: Proposed
- Date: 2026-10-25
- Deciders: maintainers
- Related: ADR-0131, ADR-0137
- Requirements: REQ-043

Protected classes: `.github/`, `kit/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`

## Context

SPEC-0036 (Approved) has the router publish what waits for a person as a small document in plain words. Build (a), the `Summary:` line of a pull request body, is a separate pull request (#226); this build reads the line only and
does not depend on its check. The tests were written first.

## Decision

1. **The writer.** After every routing run (a pull request event, a comment, a finished workflow, a push), whether or not a label changed, `route.py` reads the open pull requests once and writes `pipeline.json`
   (`schema` 1, `as_of` in UTC, `ready`, `approve`, `counts`). The path is `pipeline.json` in the working directory, or the file named by `AGK_PIPELINE_FILE`; the workflow sets it to a file of the runner's temp directory.
   `--dry-run` writes nothing. It is written after the labels are set, so it can fail no routing: a failed read or write prints `skipped rule 4` and the exit status of the routing is unchanged.
2. **The fields.** `ready`: one item per open pull request labelled `agk:ready` (`number`, `summary`, `url`); `summary` is the sentence of the first `Summary:` line of the body (1 to 120 characters), else `unknown`.
   `approve`: for each open pull request labelled `agk:approve`, one item per `Approval:` line of its latest counted verdict (`number`, `spec`, `spec_title`, `url`); `spec_title` is the title line of the spec file named by
   the line, read at the head of the pull request, else `unknown`. `counts`: exactly `review`, `fix`, `ci-red`, `conflict`, `approve`, `ready`, the number of open pull requests with each label (`approve` counts pull
   requests, not items), or `unknown` for all six when the list cannot be read. There is no sha and no raw verdict text.
3. **The schema.** `kit/pipeline-schema.json` defines schema 1, and is not in the manifest's `verbatim` list (it is a source of the kit, like the report and facts schemas).
4. **The workflow.** `agk-route.yml` uploads the file as the artifact `agk-pipeline`, 7 days, overwritten by the next run. The step is `continue-on-error`, runs `if: always()`, and ignores a missing file, so a failed upload
   fails no routing. The permissions are unchanged; the router still posts no comment, merges nothing and runs no agent, and never reads the document back.
5. **Readers (rule 7).** The document is new and the first reader is a portal intake that is not built yet; no build waits for a reader.
6. **Readings taken where the spec leaves a point open** (the most conservative each): the document is also written for an `issue_comment` run that routes no pull request, since the spec says every routing run; an `approve`
   pull request whose comments cannot be read, or whose verdict has no `Approval:` line, gives one item with `spec` and `spec_title` `unknown`; no spec amendment is needed, so reserved amendment 77 is not used.
7. Flow mode: fragment `changelog.d/pipeline-document.md`; no version bump.

## Consequences

- A portal can read the artifact `agk-pipeline` of the latest run of `agk-route` and show what waits for a person.
- The router does one more read per run (the list of open pull requests) and, for each `agk:approve` pull request, its comments and spec titles.

## Residual

- 2026-10-25: a pull request that carries a stale `agk:approve` label until the next routing run appears in the document until then (due 2026-12-31).
