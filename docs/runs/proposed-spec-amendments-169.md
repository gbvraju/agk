# Proposed spec amendments 169 (SPEC-0043; REQ-050)

Date: 2026-11-12 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0481 (brief #1124), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0043-a-project-s-plan-is-drafted-from-its-sources-and-tracked-with-calibrated-ranges.md`. The numbers 169 and
0481 are the ones brief #1124 reserved. The owner decides it with `Approve: <head> SPEC-0043` on the pull request; no
session posts that line.

The sentence (brief #1124): "A project can drop AGK at any time and keep clean engineering issues: plan issues read as
ordinary issues with AGK's fields in a hidden block, and the uninstall list names every GitHub item AGK left."

## What is on the default branch today

Read in the code by this session on `origin/main` (9a7b074):

- `scripts/agk/plan_intake.py` `publish` (rule 25) prints, for each brief, one `gh api repos/{owner}/{repo}/issues`
  command whose body is the rendered brief file as it is (`# <title>`, `Sentence:`, `Answers ...:`, `Advances:`,
  `Touches:`, `Size:`, `Expected:`, `Milestone:`, `Depends-on: #n`, `Contexts:`, `Source:`), with each key on a
  `Depends-on:` line swapped for its issue number (`numbered_body`). An engineer who opens the issue after the project
  dropped AGK reads an AGK form.
- Every reader of a brief body (`session.py brief_problems`, `check_brief.py`, the brief workflow) reads it line by line
  with `startswith` or a whole-line pattern, so a line keeps its meaning inside an HTML comment.

## Items

1. **Rule 25, one added paragraph.** "Each issue body `publish` prints, or writes in personal mode, has two parts. The
   first is for an engineer: `## What` and the brief's sentence as one paragraph; `## Acceptance` and each numbered item
   of the brief's `Answers` list as one `- [ ] <item>` checkbox, its number taken off; and one line `Part of milestone <M<n>>.`
   followed, when the brief depends on others, by `Depends on #<n>.` (the numbers joined with `, `). The second is the
   brief body as rendered, its `Depends-on:` lines numbered as before and otherwise unchanged, between a line `<!-- agk`
   and a line `-->`, which GitHub does not show. The issue's title stays the brief's title. A brief body that holds the
   text `-->` is refused, naming the brief's key, since it would end the hidden block early. The check of
   `check_brief.py --root .` runs on the whole issue body, so every reader of a brief reads the same lines whether the
   engineer part is there or not."
2. **Tests.** `tests/kit/test_plan_publish.py`: the printed body starts with the engineer part and holds the rendered body
   in the hidden block, with `Depends-on: #<n>`; `brief_problems` gives the same result for the whole body and for the
   rendered body alone; a brief holding `-->` is refused; personal mode writes the same two parts.

## Not changed

Rules 7 and 8, the brief files under `docs/plan/briefs/`, the order of rule 25 and its `--numbers` file, the label
`agk-brief` and the milestone field. The readers of a brief are unchanged.
