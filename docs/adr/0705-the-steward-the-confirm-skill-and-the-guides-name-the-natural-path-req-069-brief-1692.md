# ADR-0705: The steward, the confirm skill and the guides name the natural path

- Status: Proposed
- Date: 2026-11-22
- Deciders: maintainers
- Related: brief #1692, brief #1691, brief #1690, ADR-0661, ADR-0703, ADR-0704, ADR-0179, ADR-0310, SPEC-0062, amendment 194, plan #661
- Requirements: REQ-069

Protected classes this decision changes: `.claude/`, `skills/` and `tests/kit_dev/`.

## Context

ADR-0661 build (c) names the words: the steward's role file, the `confirm` skill, `docs/guides/steward-voice.md` and
`docs/guides/reference.md`. Builds (a) and (b) (ADR-0703, ADR-0704) built `steward_owner.py ask --target` and
`approve`, which in solo mode posts the `Approve:` or `Confirmed:` line on the person's recorded yes. The skill still
says "Never posts it", the role file lists `Approve:` and `Confirmed:` under "Never" with no aside, the voice guide has
no example of the one question, and the reference still says `approve` prints the approval "never posting it".

## Decision

1. **The role file.** `.claude/agents/steward.md`'s "Never" sentence gains "(in solo mode, the `Approve:` and
   `Confirmed:` lines that `steward_owner.py approve` writes on a recorded yes aside, session rule 29)"; its owner
   paragraph names `ask --target` and `approve` as the one path for an approval, the line to paste for a session that
   GitHub marks with an app of `agent_apps`, and personal mode as print only. The file stays within its rule budget
   (ADR-0310): the paragraph is shortened by as many words as it gains.
2. **The skill.** `skills/confirm/SKILL.md` opens with "The natural path" for solo mode; its present steps stay as the
   print path, the fallback for an app-marked session and for a person who prefers to post it.
3. **The voice guide.** One section, "One question, one yes", with two examples: the question with its three lines and
   link, and the reply after a yes (posted, or "paste this one line").
4. **The reference.** The `approve` paragraph says what it posts in each mode; `ask --target` and `approve` stay listed
   beside the standard's `confirm`.
5. **Tests.** `tests/kit_dev/test_confirm_skill.py` and `tests/kit_dev/test_reference_commands.py` check the words
   of each file, with `review_mode = "solo"`, `agent_apps` and personal mode named in each.

No script, workflow, ruleset, setting or reader changes.

## Consequences

- A person, and a steward reading its own role file, meet one path for an approval: one question, a yes in the chat.
- An installed project gets the new words by `upgrade`, as any kit file; a plugin project reads the plugin's copy.
