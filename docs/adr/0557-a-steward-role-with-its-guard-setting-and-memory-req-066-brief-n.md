# ADR-0557: A steward role with its guard, its setting and its memory

- Status: Proposed
- Date: 2026-11-15
- Deciders: maintainers
- Related: SPEC-0059, ADR-0555, ADR-0546, ADR-0310, ADR-0247, brief #1320, brief #1277, plan #661
- Requirements: REQ-066

## Context

SPEC-0059 (Approved, #1280) adds a steward: one on-demand session beside the owner that answers what the evidence
settles and asks the owner only the rest. Its rule 17 orders six builds; this ADR covers build (a), on which the
other five depend: the agent file (rule 2), the guard (rule 11), the `[steward]` setting (rule 12), the memory issue
with its entry kinds, its parser and its roll-over (rule 8, with rule 14's personal mode), and the rule changes of
rule 15. On the default branch no steward agent, guard, setting or memory exists (brief #1320's evidence).

## Decision

1. **The role.** `.claude/agents/steward.md`, started as `claude --agent steward` (verify: the flag of the runtime
   used), kind `design` on the `strongest` tier at `high` effort, on demand only: it names no watch, `/loop`,
   `ScheduleWakeup` or lease renew command. Its front matter names its guard as a PreToolUse hook, as the
   conductor's does, and it carries SPEC-0059 rule 19's stage-to-skill table.
2. **The guard.** `.claude/hooks/steward_guard.py` denies what SPEC-0059 rule 11 lists, except the outbound data
   guard, which is build (e)'s. A comment body it cannot read (a command substitution, standard input, a missing
   file) is denied, fail closed, since its first line cannot be checked; so is a GraphQL call (`CLAUDE.md item 10`).
   Read conservatively, a merge includes `git merge`; a push to the default branch includes a `git push` that names
   no branch and any write through the `contents` or `git` endpoints; a workflow change includes `gh workflow run`,
   `enable` and `disable`. The owner's word for a filing above `auto_file` is an `Owner said (<UTC time>): "…"` line
   in the brief's body, the form of SPEC-0059 rule 5.
   A label write through `gh api .../issues/<n>/labels` may carry only `agk:parked` or `agk-steward`, since the hook
   reads no network and cannot tell a pull request from an issue by its number; `gh pr edit` may add only
   `agk:parked` and `gh issue create|edit` only `agk-steward`. Each denial names the rule and the setting or path
   class, never the value. The guard reads only the command, the files a body names and `agk.toml`, and stores
   nothing.
3. **The setting.** `config.steward_settings(root)` reads the optional `[steward]` table: `auto_file`, `false` or a
   whole number from 0 to 3, `0` when unset. Another key or value is refused naming `setting: steward.<key>`.
4. **The memory.** `scripts/agk/steward.py` keeps one open issue labelled `agk-steward` (created when none is open),
   one comment per entry under the twelve first words of SPEC-0059 rule 8, each ending `Who: AGK steward`.
   `start` reads the memory first: the listing of the open memory issue, then its comments with `since=` from the
   last comment seen, held in a file of the clone's git folder (never a tracked file); a quiet start makes at most
   3 counted calls (rule 18 allows 5). It prints the newest entry of each kind first and names an entry of another
   first word. A `Started: steward <session> <UTC time>` newer than 60 minutes with no `Ended: steward <session>`
   after it, by another session, makes a start say so and write nothing. At 500 comments a start opens a new
   memory issue whose first comment links the old one and carries every open `Owner question:` (one with no later
   `Decision:` naming its Q id), then closes the old one. `record` refuses a text the data guard's detectors match
   (`guard.scan_text`), naming the class. In personal mode the memory is `docs/runs/steward/memory.md` of the
   sidecar and nothing is posted.
5. **The rule changes of SPEC-0059 rule 15.** Principle 7 and `CLAUDE.md item 1` in `config/core-rules.md` gain the
   one class: a question that the evidence settles (SPEC-0059 rule 3) may be answered by the steward, with its
   evidence; every other question is recorded and goes to the owner. Principles 1 and 2 are unchanged. The rule
   budget (`config/rule-budget.txt`, ADR-0310) raises the word counts of those two files by the words added and
   lists the new agent file; no rule line is added.

## Consequences

`claude --agent steward` is a role the kit installs in every project; it cannot approve, verdict, merge, push to the
default branch, change a workflow, the ruleset or a secret, or speak for the owner without the owner's quote.
Protected path classes changed: `constitution/` (principle 7), `config/` (`core-rules.md`, `rule-budget.txt`),
`.claude/` (`agents/steward.md`, `hooks/steward_guard.py`), `scripts/agk/` (`steward.py`, `config.py`), `agk.toml`
(the `[[testing.map]]` entries), `tests/kit/` (the three new test files and the two that quote the changed rules)
and `kit/` (`manifest.json`, `templates/agk.toml`, `templates/gitattributes`).

## Residual

- 2026-11-15 (verify): the `--agent` flag and the front-matter hook of an agent started as the main session, as for
  the conductor.
- 2026-11-15: the evidence rule, triage and filing (b), the owner relay and wait (c), the daily list and the
  override share carried at roll-over (d), the outbound data guard (e) and onboarding (f) are later builds.
