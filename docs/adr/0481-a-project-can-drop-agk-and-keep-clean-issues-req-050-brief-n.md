# ADR-0481: A project can drop AGK and keep clean issues

- Status: Accepted
- Date: 2026-11-12
- Deciders: maintainers
- Related: ADR-0203, ADR-0459, ADR-0160, brief #348, brief #1124, plan #661, amendment 169
- Requirements: REQ-050

## Context

A project may have AGK plan its GitHub milestones and issues, then drop AGK so its engineers build from those issues
without it (the owner, 2026-11-12, brief #1124). Offboarding exists: `uninstall.py --pause` and `uninstall.py` (brief
#348, ADR-0203). Two gaps remain. `plan_intake.py publish` (SPEC-0043 rule 25, ADR-0459) prints each issue body in AGK's
brief shape, so after offboarding the issues read as AGK forms. The GitHub list `uninstall.py` prints does not name the
`merge` environment and its `AGK_MERGE_TOKEN` secret (`merger.yml`), the `claude/*` branches builders leave, or the
scheduled tasks and loops that start AGK sessions, and it gives no order.

## Decision

1. Amendment 169 to SPEC-0043 rule 25: an issue body that `publish` prints or writes starts with an engineer part
   (`## What` with the sentence, `## Acceptance` with the `Answers` items as checkboxes, a `Part of milestone <M<n>>.` line and
   `Depends on #<n>.`), followed by the rendered brief body unchanged between a line `<!-- agk` and a line `-->`. A body
   holding `-->` is refused. `check_brief.py` runs on the whole issue body.
2. `uninstall.py`'s GitHub list starts with "stop the scheduled tasks or loops that start AGK sessions for this project",
   names the `merge` environment and its `AGK_MERGE_TOKEN` secret and the open `claude/*` branches (by pattern; the tool
   reads nothing from GitHub), says that local mode has no ruleset, and ends with the order: stop the sessions, pause,
   relax the ruleset, merge the removal branch, then the rest.
3. `docs/guides/getting-started.md` gains a section `Handing a project over without AGK` with that order.
4. No change to `init.py`: a checkout of the release commit of the newest release row installs and is removed with every
   kit file `delete`, none `changed`; a test proves it on the real table. An install from the default branch between
   releases (`--unreleased`) carries files no release row lists, which removal keeps as `changed`, as designed.

Protected path classes changed: `scripts/agk/` (`plan_intake.py`, `uninstall.py`), `tests/kit/` (`test_plan_publish.py`)
and `tests/kit_dev/` (`test_uninstall.py`).

## Consequences

Plan issues read as ordinary engineering issues on GitHub, and every AGK reader still finds its fields. A person who
drops AGK has one printed list, in order, of every GitHub item AGK left, and still does each step by hand with admin
rights. A person who edits an issue on GitHub and deletes the hidden block leaves AGK nothing to read in it; that issue is
then the engineers' own.

## Residual

- 2026-11-12: the tag `v0.62.0` points at a commit whose `kit/manifest.json` says `0.61.0`, not at the release commit of
  row 0.62.0, so `init.py` from that tag refuses; moving a tag is the maintainers' act (due 2026-12-31).
