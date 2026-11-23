# ADR-0752: A kit brief shows its study before it is filed: impact, wiring, earlier record and the lasting fix (REQ-037)

- Status: Proposed
- Date: 2026-11-23
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1800, SPEC-0030 rule 4, amendment 142, amendment 168, brief #1425 (ADR-0598), brief #982, ADR-0650,
  SPEC-0059 rule 6, plan #661
- Requirements: REQ-037

Protected classes: `scripts/agk/`, `skills/`, `tests/kit/`, `tests/kit_dev/`, `agk.toml`, `kit/`

## Context

`check_brief.py` checks a brief's shape only. Nothing asks what the change costs, where it is wired in, which earlier
decision or bug of the same kind it repeats, or whether it fixes the kind or the case. In the week to 2026-11-23 the
kit repeated work four times for that reason (brief #1792 built beside the unbuilt ADR-0650; the `utf8_output` break
twice, #1581 and #1627; the clock class a third time, #1680 then #1791; amendments 186 and 187 approved and not
written into their specs). The owner's word (2026-11-23, the steward chat, quoted as data): "Yes, file the brief study
gate".

## Decision

1. With `--root DIR`, a brief that passes its shape also shows its study (`brief_study.study_result`): one `Impact:`
   line followed by `Speed:`, `Quality:`, `GitHub:`, `Cost:` and `Tests:` in that order, each with a text or
   `none: <reason>`; one `Wiring: <file>:<function> called by <callers>; ...` line whose files exist under the root
   and define the function (a `def`, a `class` or a top-level name), or `Wiring: none: <reason>` for a change with no
   entry point; one `Prior:` line whose ADR, spec and amendment ids exist under `docs/`, or `Prior: none: <what was
   searched>`; and one `Class: <kind>; seen <n> ...` line, where `seen` above 0 needs an Answers item headed
   `**The class stays closed.**`. Without `--root` the study is not read: the shape check is unchanged.
2. Rolled in: until `brief_study.STUDY_FAILS_FROM` every study line is a warning (`warning: study: ...` printed
   before `ok brief`, and in the `warnings` list of a passing event), from that day a failure. The constant ships as
   `None` (warnings only) until the maintainers name the day (Q-1800-1): the plan's rendered briefs and a sidecar's
   briefs carry no study lines yet, so a fixed day 7 days out would fail them and their tests on that day. A
   `Priority: 0` brief is held only to `Class:` and `Prior:`; the router's own red-branch brief (`Advances: none` with
   `Priority: 0`, which needs no `Contexts:` either) is held to none, since the router writes it.
3. `scripts/agk/brief_study.py FILE --root DIR [--open-briefs FILE]` prints the earlier record to read: each ADR and
   spec that names a code path of `Touches:` (a `.py` file also by its file name) or a `Wiring:` file or
   `<module>.<function>`; each proposed amendment that names one and that its spec does not name; and each open brief
   of the plan's read cache, or of the saved list, whose `Touches:` meets this one's (`briefs: not read (no plan
   cache)` without it). `agk.toml` and `kit/hashes.json` are no search term. It reads files and the cache only.
4. `check_brief.py --root` warns, whatever the day, for each Accepted ADR and each open brief the study finds that
   `Prior:` leaves out. An amendment is printed but not warned: its approval is not readable from its file.
5. The brief skill runs `brief_study.py` before `check_brief.py`; `docs/briefs/TEMPLATE.md` shows the lines.
6. Path classes changed: `scripts/agk/` (`brief_study.py`, `check_brief.py`), `skills/` (the brief skill), `tests/kit/`
   (the new tests and the study lines in the passing `--root` fixtures), `tests/kit_dev/` (the same lines in the
   screens fixture), `agk.toml` (the `[[testing.map]]` entry) and `kit/` (`kit/manifest.json` installs the script).
   No setting is added; `review_mode`, `pr_mode`, `execution` and personal mode read the same lines.

## Consequences

A kit or project brief names the decision it builds on and the guard that closes its kind, and a brief that repeats
an Accepted decision without naming it is warned on its issue. Writing a brief takes longer by the study. Every
passing `--root` test fixture of the brief check carries the study lines.

## Residual

The switch day is unset (Q-1800-1); until it is named the study only warns. The open-brief part reads open briefs only; the plan's read cache holds no closed briefs (verify). Whether an
amendment is approved is not read.
