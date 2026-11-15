# ADR-0559: The steward relays the owner, and the conductor starts it

- Status: Proposed
- Date: 2026-11-15
- Deciders: maintainers
- Related: SPEC-0059, ADR-0557, ADR-0543, ADR-0528, ADR-0190, brief #1322, brief #1320, brief #1282, plan #661
- Requirements: REQ-066

## Context

SPEC-0059 (Approved, #1280) rule 17 build (c): the owner question and its relay (rule 5), the bounded owner wait and
the park-and-resume flow for the steward (rule 10), the conductor's start of the steward and the steward's start of
the conductor (rule 2), personal mode's printed form (rule 14) and the conductor's text (rule 15). Build (a) (#1326,
ADR-0557) added the role, its guard and its memory; the bounded owner wait with its parking is on the default branch
since #1287 (ADR-0543). This build adds only what the steward needs on top of them.

## Decision

1. **The owner question.** `scripts/agk/steward_owner.py ask` takes one line of at most 500 characters that asks
   (`?`), gives a recommendation (`I recommend`) and holds no kit term: a backtick, a file name, an `agk:` or `agk-`
   label, a path under `scripts/`, an option, a rule, principle or item number, a SPEC, ADR, REQ or Q id, an issue
   number, a command name (`python`, `gh`, `git`, `make`, `pytest`, `claude`) or a kit word (pull request, brief,
   verdict, conductor, builder, commit, branch, label). It records `Owner question: <Q> <sentence>` through
   `steward.record` (the data guard runs there), prints the sentence for the chat and posts
   `Question: <Q> for the maintainers: <sentence>` ending `Who: AGK steward`.
2. **The relay.** `steward_owner.py relay` builds the three lines of rule 5 from the answer, the owner's words (one
   line read from a file, verbatim) and the UTC time, and refuses a body whose first line is not
   `Maintainer answer: Q-<id> <answer>`, whose second line is not `Owner said (<UTC time>): "<words>"` or whose last
   line is not `Who: ProductOwner`. The guard of build (a) still denies a hand-typed `Maintainer answer:` without the
   quote.
3. **Park and resume for the steward.** `steward_owner.py park --pr N` is one pass of `session.owner_step` on one pull
   request, with #1287's `park_pull` and `unpark_pull`: the same label and `Parked-by:`/`Unparked-by:` comments, so
   the conductor's sweep and the builder's watch read the steward's parks as their own. An evidence `Answer:` by an
   answerer ends the wait, as `owner_item` already reads it. After an unpark, and after a relay that removes the owner
   wait's park, the steward runs `session.py tell` with `parked #<n> answered <Q>`. With no steward, the conductor's
   sweep parks and resumes as today.
4. **The conductor's start of the steward.** `conductor.py sweep` reads the comments it already read for the owner
   waits and prints one `STEWARD:` line when a `Question:` that an earlier sweep saw still has no `Answer:`,
   `Maintainer answer:` or `Correction:` by a listed verdict author or spec approver that names its Q id (or names
   none); once per question, kept in `<git dir>/agk/steward-starts`. The line names
   `python3 scripts/agk/launch.py role --role steward --session steward-<UTC minute>`, with `--adapter` only when
   `auto_start` and `launch_adapter` are set in the checkout and on the default branch. `conductor_guard.py` allows
   that one form and no other role. `launch.py role` prints the role's prompt or calls the adapter once on the
   `design` kind's tier and effort, with `AGK_ROLE` and `AGK_AGENT` and no `AGK_BRIEF`; a refused start prints
   `stuck: <role> <session> not started (<why>)` and exits 1, which the conductor lists under `Needs a fix`. A
   second steward start writes nothing, by build (a)'s `Started:` marker.
5. **The steward's start of the conductor.** `steward_owner.py ready` reads the saved output of
   `check_plan.py --trace` (its last line must start `ok plan`), the saved `session.py plan --json` (its `malformed`
   list must be empty), `docs/plan/scope-lock.md` (it must exist) and the memory as `steward.py start` last read it
   (no open `Owner question:` that names `M1` or names no milestone: read conservatively, one naming no milestone
   blocks). Any failure prints its `not ready:` line and starts nothing; with `--start` and every check passed it
   calls `launch.py role --role conductor` (verify: the adapter's start of a conductor).
6. **The conductor's text.** `.claude/agents/conductor.md` leaves the answers from the rules to a running steward,
   names the one steward start and the `stuck:` line, and reads a steward's `Tell:` as a resume. The rule budget
   (`config/rule-budget.txt`, ADR-0310) raises the word counts of the two agent files by the words added; no rule
   line is added.
7. **Personal mode.** `ask` and `relay` print what they would post; `park` parks nothing.

## Consequences

The owner is asked in plain words and the trail holds the owner's own words; a waiting question brings the steward
within one conductor pass, and a plan that fails a check starts no conductor. Session rule 21's "then waits there" is
not changed here (brief answer 5): it is raised as a question. Protected path classes changed: `.claude/`
(`agents/conductor.md`, `agents/steward.md`, `hooks/conductor_guard.py`), `scripts/agk/` (`steward_owner.py`,
`conductor.py`, `launch.py`), `agk.toml` (the `[[testing.map]]` entries), `tests/kit/` (the two new test files),
`config/` (`rule-budget.txt`) and `kit/` (`manifest.json`).

## Residual

- 2026-11-15 (verify): the adapter's start of a conductor and of a steward, and the `--agent` flag of the runtime.
- 2026-11-15: questions on briefs (with no pull request) are not read by the sweep's steward start; the steward reads
  them itself when it runs.
