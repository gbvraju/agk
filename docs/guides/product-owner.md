# The product-owner guide

For the person who owns the product and does not read the code. Every Monday AGK writes you one GitHub issue, the product report. This
page says when it arrives, what is in it, the five questions it answers, and what to do about each thing that waits for you.

Read [the limits](../../README.md#honest-limits) too. The report states what the repository's files and GitHub records show. It
does not judge whether the work is good.

## When it arrives

The report is written by the `product-report` workflow, scheduled for Monday 07:13 UTC (12:43 in India). GitHub starts scheduled
runs late. The first scheduled report, on 2026-10-19, arrived about 7.5 hours after its slot (about 20:10 in India), so expect it on
Monday afternoon or evening in India, and sometimes later. If nothing has arrived by Tuesday, start the workflow by hand (Actions,
`product-report`, Run workflow) and read [When something goes wrong](getting-started.md#when-something-goes-wrong).

The issue is titled `agk product report <year>-W<week>` and has the label `agk-product-report`. It covers the whole ISO week before
the Monday it runs: a pull request merged this week is in next Monday's report. A section with no line says `nothing this week`.

## The five sections, with a real line from each

These lines come from the report of week 2026-W42 of this project's own repository,
[issue 88](https://github.com/gbvraju/agk/issues/88). Every line of a report ends with a link to its evidence.

| Section | The question it answers | A line from issue 88 |
| --- | --- | --- |
| Delivered | Which of my requirements are done, against which acceptance criteria? | `REQ-001 "Protected paths change only with an ADR in the same PR" is done: 3 acceptance criteria (AC1, AC2, AC3)` |
| Proven | Is each acceptance criterion backed by a test that would fail if the behaviour broke? | `REQ-002 is proven (last change PR #83: proven)` |
| Needs you | What is waiting for my decision right now? | `Draft spec SPEC-0014 "The weekly product report footer names the kit version" waits for approval` |
| At risk | What is overdue, drifting or being reworked? | `PR #45 was merged before its last commit was cleared` |
| Cost | How much rework and waiting did this week take? | `PR #79 "feat(k4): G1, check_specs lifecycle rules a and b and the shared parsers, kit 0.20.0 (ADR-0040)": 0.8 hours from opening to merge, 0 fix verdicts` |

In a busy week, when more than ten pull requests merged, Delivered lists the done requirements and then one line with the number of merged pull requests and one link to the full list, and Cost shows only the week's total, ending with the same link. A quiet week lists each pull request.

In At risk, when two or more pull requests share one kind of risk (open too long, sent back, merged with no verdict, merged before its last commit was cleared), the kind is one line with every number, each a link, for example `PRs #12 (41 days), #15 (30 days) have been open`. One pull request keeps its own line with its title.

The last line of the Cost section is the week's total, for example `This week: 74 pull requests merged; hours in total: 130.0; fix
verdicts in total: 32; declared "Behaviour: unchanged": 4`. A fix verdict is a reviewer's `Verdict: fix list` on a pull request: work
sent back. The hours are from opening to merge and include waiting.

The footer names the commit the report was computed from (`facts: <commit>`), the kit version that produced it (`kit version: <version>`, or `unknown`), the week's metrics issue (`metrics: #86 "agk metrics
2026-W42"`) and the drift audit. The same facts at the same commit give the same report.

## Five questions you should be able to answer from it

Answer these from the report alone. If you cannot, that is a finding: open an
[I got stuck issue](../../.github/ISSUE_TEMPLATE/stuck.md) with the section and the line.

1. Which of my requirements are done, and against which acceptance criteria? (Delivered)
2. Is each of those criteria backed by a test that would fail if the behaviour broke? (Proven)
3. What is waiting for my decision right now? (Needs you)
4. What is overdue, drifting or being reworked? (At risk)
5. How much rework and waiting did this week take? (Cost)

## What to do for each kind of "Needs you"

The Needs you section groups what waits for a person by kind, each group headed by its count. There are six kinds.

| The line says | What it means | What you do |
| --- | --- | --- |
| `Draft spec SPEC-NNNN "<title>" waits for approval` | a spec is written and nobody has approved it | Read the spec. If it has open questions, rule on them first (see the `Question` row). When you agree, change its `Status: Draft` line to `Status: Approved` in a pull request and merge. An implementation pull request that advances a requirement is refused until an Approved spec names that requirement. |
| `Proposed ADR-NNNN "<title>" waits for a decision` | a decision is written and nobody has accepted it | Read it. When you decide, change its `Status:` line in a pull request. The drift audit lists a Proposed ADR that is more than 14 days old. |
| `Question Q-... is waiting, asked in <file>` | a question was left open on a spec or an ADR | Answer it in the pull request or in the notes file: a row under `## Rulings` or a decisions-log row that says `<id> ruled`. |
| `PR #N "<title>" has had no verdict for N days` | a pull request is open and nobody has reviewed it | Ask the architect session to review it (see [getting started, step 10](getting-started.md#step-10-the-architect-reviews-you-merge)), or review it yourself. Merge only after the latest commit has a `Verdict: cleared <sha>` line. |
| `Overdue since <date>: <text>` | a residual (a known open item with a due date) is past its date | Do it, or move the date and record why in the same pull request. |
| `REQ-NNN "<title>" is planned and no spec names it` | a requirement exists and nobody has started a spec | Ask for a Draft spec: `/agk:spec "<one sentence>"`, or ask the architect session. |

**If you do not use git.** A change of a `Status:` line is one line in one file, and you can make it in the browser. Open the file on
github.com (the link at the end of the report line takes you to it), tap the pencil, change the one line, choose "Create a new
branch and start a pull request", and open the pull request. When `governance` is green, merge it.

AGK only lists these. It never decides one of them for you, and nothing it does approves a spec, accepts an ADR or merges.

## What `unknown` means

The report never guesses. When a value cannot be found, the line says `unknown` and says what it is waiting for. For example the
Proven section can say a requirement `has an unknown proof`: no `proof` run was found for its last change. A proof can also read
`skipped (declared unchanged)`: the pull request declared `Behaviour: unchanged`, so no new test was required, and the report counts how
many pull requests declared it so that overuse is visible. `unknown` is a prompt to look, not an error and not a pass.

What `proven` means is narrow: the new tests of the last change failed on the old code and passed on the new. It does not say the
tests are good or that the requirement is the right one.

## What is in this guide's evidence

The report format is [SPEC-0011](../specs/0011-inbox-and-report.md). Its first scheduled run is recorded in
[the decisions log](../runs/decisions-log.md) and its first hand-started run in
[product-report-live-1.md](../runs/product-report-live-1.md). Nobody outside the project has yet answered the five questions from a
report for two weeks running (REQ-018 AC1 is open).
