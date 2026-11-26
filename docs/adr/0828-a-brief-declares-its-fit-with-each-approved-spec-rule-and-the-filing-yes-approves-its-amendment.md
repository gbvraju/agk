# ADR-0828: A brief declares its fit with each Approved spec rule it names, and the owner's filing yes approves its amendment (REQ-066)

- Status: Proposed
- Date: 2026-11-26
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #2002, ADR-0723 (an approval is read only on the pull request that changes it), ADR-0752 (the brief's
  study), ADR-0756 (one reading of a brief), ADR-0757 (the study's fail day), ADR-0747 and ADR-0749 (an `Owner
  needed:` checked before it is posted), ADR-0813 (amendment classes), ADR-0814 (the approval reader), ADR-0559 (the
  steward relays the owner), amendments 254 and 255, plan #661
- Requirements: REQ-066

Protected classes: `scripts/agk/`, `skills/`, `.claude/`, `tests/kit/`

## Context

Of the 40 most recently merged pull requests (#1845 to #1984), 14 carried an `Owner needed:` about a build against its
Approved spec or its brief, about 31 hours of owner wait: nine amendments the brief had reserved at filing and still
asked at merge, two amendments a review found undeclared and three brief-against-spec conflicts asked as Q ids. No
check read a brief against its spec's rules, and an approval was read only on the pull request (ADR-0723). The owner's
word (2026-11-26T11:05Z, the steward chat, quoted as data): "Brief 2 and 3 ,".

## Decision

1. **The spec fit line.** For each Approved spec that a brief's Answers name, or whose `- Requirements:` line names a
   requirement of its `Advances:`, the brief carries one line `Spec fit: SPEC-<nnnn> <part>[; <part>]`, each part
   `rule(s) <list> within` or `rule(s) <list> change by amendment <m>`, naming every rule of that spec the brief names.
   A `change` part needs `Reserved:` naming amendment `<m>` and the amendment's items quoted right under its line
   (`> 1. ...`, each with its `Class:` line), read by `check_amendments.items` and classed by `item_class` as a file.
2. **The check.** `check_brief.spec_fit_problems(body, root)`, called from `brief_result` after the study, refuses a
   missing line, a named rule left out, a rule the spec does not have, a spec that is not Approved, two lines for one
   spec, a rule both within and changed, and a `change` without its `Reserved:` amendment or quoted items, naming the
   `Spec fit:` line, the spec and the rule, never the text. One heuristic only warns: a number limit of a fitted rule
   (`at most <n>`, `up to <n>`, `<n> or fewer`, `batches of <n>`) that the brief states with another number while its
   line does not name that rule.
3. **What it cannot catch.** It cannot tell whether a `within` is true, nor see a conflict with a rule the brief never
   names; the brief skill's spec fit step reads those, and a miss found later is counted (7).
4. **The skill.** `skills/brief/SKILL.md` gains a spec fit step after the study; `docs/briefs/TEMPLATE.md` the line.
5. **One yes covers both.** `steward_owner.file_brief` never files a brief with a `change` under `[steward]
   auto_file`; the person's yes approves each amendment only when it names it (`Yes, file the <NAME> brief with
   amendment <m>`, or a plain yes to an ask that named each number). In solo mode the steward then posts on the brief
   one `Maintainer answer: amendment <m> approved` per amendment with `Text: <digest of the quoted items>`, `Owner
   said`, `Asked` and `Who: ProductOwner`; in team mode it prints the first two lines for a spec approver to post. A
   yes that names no amendment files the brief and prints `amendment <m>: not approved at filing (setting: Spec fit:)`.
6. **The review.** `conductor.full_problem` gains `filed_problem`: an `Owner needed:` that asks for amendment `<m>`
   is refused when the pull request's `Brief: #<b>` issue holds an approval that `check_amendments.approval` reads
   whose `Text:` digest equals the digest of the items of the file at the head. A different digest allows the ask.
7. **A departure no one declared** from an Approved rule the line states within is a fix list item, never an owner
   ask; an owner ask that stays names `Spec fit miss: brief #<b> SPEC-<nnnn> rule <n>`.
8. **No new setting.** `[flow] brief_study_fails_from` makes a missing or incomplete line fail on and after that day
   (warn before); a `change` without its amendment or items fails on any day; a `Priority: 0` brief is held only for
   a `change`.

The spec text changes only by amendments 254 (SPEC-0030 rules 4 and 6) and 255 (SPEC-0059 rule 6).

## Consequences

An amendment the owner approved at filing is not asked again at merge while its text is unchanged; a brief that would
make a build depart from its Approved spec is seen before the build starts. A brief writer spends a few minutes more
per fitted spec. The steward posts one more comment per amendment on a brief; the conductor makes two more GETs
before an amendment ask.

## Residual

- 2026-11-26: `Q-SF-1`, a standing rule for a brief and spec that disagree, is the owner's; this build keeps the ask.
- 2026-11-26: `Q-SF-3`, a settled line at filing, is not read in this build.
