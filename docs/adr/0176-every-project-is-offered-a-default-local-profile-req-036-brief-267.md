# ADR-0176: every project is offered a default local profile once its stack is accepted (REQ-036, brief 267)

- Status: Proposed
- Date: 2026-10-29
- Deciders: maintainers
- Related: ADR-0170
- Requirements: REQ-036

Protected classes: `scripts/agk/`, `kit/`, `skills/`, `tests/kit_dev/`

## Context

Brief #267 (priority 1): a project pilot on this kit specified identity, email, file storage and scheduled jobs as real cloud
services, so its specs could be tried end to end only after accounts, a registered identity app and a verified mail domain
existed. Nothing in the kit asks for a local profile, in which the whole product runs on one machine with a stand-in for every
external service, so each project has to think of it, often too late. The tests were written first
(`tests/kit_dev/test_engines_local_profile.py`) and failed on the unchanged scripts (16 failed, 9 passed at the first checkpoint
of the pull request, 1210f67).

## Decision

1. **The offer (answer 1).** When the tree holds one stack ADR that is Accepted, passes `stack-check` and names its `Chosen`
   option, `engines.py stack-next-steps` (the accepting pull request's steps, printed by `/agk:stack`) prints one extra step after
   the body: a ready-to-run `/agk:spec "<sentence>"`, the decline line and who accepts it. `playbook.py next-steps` prints the
   same step when the tree holds such an accepted stack. Nothing is written; the Proposed options pull request gets no offer.
   A sentence that the intake's own `check_sentence` refuses (over 300 characters, or not one sentence) is still printed, with
   one line that gives the intake's own refusal and says to shorten or reword the list of services.
2. **The services of an option (answer 3).** An option bullet may carry one segment `External services: <text>.` before its
   `Practices:`; `stack-check` fails a segment that is empty, placed after `Practices:`, given twice or holding a double quote,
   naming the rule and the setting and never the text. A double quote is refused rather than replaced, so that the printed
   `/agk:spec "…"` stays one quoted argument and the option's text is never changed silently. The offer fills the template's one placeholder with the text of the chosen option's segment, unchanged, so it
   names no product or vendor that the option does not already name; an option without the segment fills it with
   `none named by the stack yet`. The stack ADR template carries the segment as `TODO(architect)` and the skill describes it.
3. **The template (answer 4).** `kit/templates/local-profile.md` is the sentence on one line with one placeholder,
   `{{services}}`: one machine, one command, a setting that swaps each external service for a stand-in, invented data seeded on
   start, and a startup guard that refuses it outside the local environment. The stack ADR template gains the Practices bullet
   `local profile: check (step: a smoke test that starts the local profile and signs in with the stand-in identity)`.
4. **The decision (answer 2).** The requirement is decided when `docs/requirements.md` holds a requirement whose title or
   acceptance names `local profile` (it went through the intake, which a spec approver approves with its `Approve:` line), or
   when the stack ADR's Residual holds one line `local profile: declined, <reason of at least 20 characters> (YYYY-MM-DD)`,
   whose date is a real calendar date (`date.fromisoformat`); a date that does not exist makes it a badly shaped decline.
   `stack-check` fails a Residual line that starts the decline and does not have that shape, naming the rule and never the
   reason. While an accepted stack is not decided, `stack-check` prints `info engines: local profile: not decided` after its
   `ok` line and still exits 0. One existing test of an accepted stack now expects that line.
5. **Reading Q-267-1 (taken, the conservative one; accepted by the conductor's verdict on a576d87, 2026-10-29).** Answer 1 names `playbook.py next-steps`, which prints only for a start
   branch whose difference is the vision and one charter, a step that comes before `/agk:stack`. The step is added there as the
   brief says (it prints when the tree holds an accepted stack), and the offer a person sees in practice is the one of
   `stack-next-steps` on the accepting branch. A separate playbook command for a later moment waits for a decision.
6. **Reading Q-267-2 (taken, the conservative one; accepted by the conductor's verdict on a576d87, 2026-10-29).** Answer 3 says the sentence is filled in from the accepted option's external
   services, and no part of the stack ADR named them; the optional `External services:` segment of decision 2 is the smallest
   addition that lets a script read them. Reading them from free text was not built.
7. **Reading Q-267-3 (taken, the conservative one; accepted by the conductor's verdict on a576d87, 2026-10-29).** The brief's `Touches:` names `tests/kit/test_playbook*.py` and
   `tests/kit/test_engines*.py`; the tests of `engines.py` and `playbook.py` (kit-only scripts) and their fixtures live in
   `tests/kit_dev/`, so the new tests are there, and the class is named above.
8. **Flow mode.** Fragment `changelog.d/local-profile-offer.md`; no version bump. `kit/hashes.json` is not edited, although
   the brief's `Touches:` lists it: it is a release file (session rule 14). No project, product or vendor is named; the tests use
   an invented stack.

## Consequences

- Every project that accepts a stack is offered the same local-profile requirement, with the services its own option names,
  and either takes it through the normal intake or records why not.
- A check cannot tell that a decline line was written by a maintainer, nor that a requirement which names `local profile` is the
  offered one; both are left to review.

## Residual

- 2026-10-29: the decline line's author is not checked; review of the pull request that adds it is the only control (due
  2026-12-15).
