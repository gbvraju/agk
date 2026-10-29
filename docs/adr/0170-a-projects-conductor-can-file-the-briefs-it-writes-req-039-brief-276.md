# ADR-0170: a project's conductor can file the briefs it writes (REQ-039, brief 276)

- Status: Proposed
- Date: 2026-10-29
- Deciders: maintainers
- Related: ADR-0105, ADR-0136, ADR-0149
- Requirements: REQ-039

Protected classes: `.claude/`, `config/`, `tests/kit/`

## Context

Brief #276 (priority 1): in a project pilot (2026-10-27) the conductor wrote twenty checked brief bodies, but its guard
(`.claude/hooks/conductor_guard.py`, ADR-0105) allows only comments, so it handed the person a shell script to run, which the
person first ran in the wrong shell. The conductor also cannot close a brief, so a brief stays open until a person closes it or a
pull request says `Closes #n`. The tests were written first (`tests/kit/test_conductor_guard_issue.py`) and failed on the
unchanged guard (the first checkpoint of the pull request, f1d55a5).

## Decision

1. **The one new action.** Without `--shadow` the guard allows `gh api --method POST repos/<origin>/issues` (also `-X POST` or
   `--method=POST`), where `<origin>` is the repository of the checkout's origin remote, with exactly three fields in any order:
   one `-f title=<text>` (not empty), one `-f labels[]=agk-brief` and one `-F body=@<file>`. The file is a regular file of a
   scratch directory (no link out of it, at most 65536 characters, GitHub's limit of a body, never read in part) whose text
   `check_brief.py FILE --root <project>` accepts: the shape of SPEC-0030 rule 4 and SPEC-0034 rule 2, and an `Advances:` that
   names a requirement of the project's `docs/requirements.md`. A project whose requirements file cannot be read files nothing.
   The guard calls the functions of `check_brief.py` (`brief_problems`, `absent_requirements`), the one reading of a brief, as it
   calls the router's reading of a verdict (ADR-0149); without them it files nothing.
2. **Nothing else widens.** Any other label, a second label, a label as a plain string, another field (an assignee, a milestone,
   a second title), any other flag (`-H`, `--input`, `--jq`, `--hostname`), an inline body, another repository, an issue edit
   (`issues/<n>`), a close, a label creation and `gh issue create` stay denied. The shadow mode files nothing. The refusal names
   the rule, never the body or the path.
3. **The role file.** `.claude/agents/conductor.md` says how to file a brief, in dependency order (a brief before every brief whose
   `Depends-on: #n` names it), and to stop and file nothing more when GitHub answers with a number other than the one the plan
   expects, saying which brief got which number.
4. **Closing a brief.** Session rule 28: the last pull request of a brief carries `Closes #<brief>`, so that GitHub closes the
   brief when it merges; an earlier build's pull request does not close it.
5. **Reading Q-276-1 (taken, the conservative one).** Answer 1 of the brief also names the `agk-conductor` issue and the creation
   of the two labels. The task that started the build kept the guard strict, with creating an issue labelled `agk-brief` as the
   only new action; so the `agk-conductor` issue and both labels are still created by a person (`doctor.py` reports a missing
   `agk-brief` label). Widening the guard to them is a later decision.
6. **Reading Q-276-2 (taken, the conservative one).** The second half of answer 3, that the router or a check names a merged pull
   request that advances a brief and does not close it, is not built here: the brief's `Touches:` names neither the router nor a
   check, and a check of one pull request cannot tell the last build of a brief from an earlier one. It waits for a decision.
7. **Flow mode.** Fragment `changelog.d/conductor-files-briefs.md`; no version bump. `kit/hashes.json` is not edited, although the
   brief's `Touches:` lists it: it is a release file (session rule 14).

## Consequences

- A conductor files the briefs of a plan itself, each one checked by the same reading that `session.py next` applies, and a
  person runs no script.
- A brief created this way has the label `agk-brief` and nothing else; its title is free text, which the guard does not compare
  with the body.
- A brief whose last pull request carries `Closes #<brief>` closes at the merge; one whose last pull request forgets it stays open
  until a person closes it, as today.

## Residual

- 2026-10-29: the guard cannot tell from the command alone that the plan's numbering held; the stop on a differing number is the
  role file's, not the guard's (due 2026-12-15).
- 2026-10-29: the guard runs the check on the file when the command is judged; a file changed between that moment and the upload
  by `gh` is not seen. Only the conductor writes in its scratch directory (due 2026-12-15).
