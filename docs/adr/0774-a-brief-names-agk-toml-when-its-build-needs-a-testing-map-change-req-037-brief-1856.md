# ADR-0774: A brief names agk.toml in Touches when its build needs a testing map change (REQ-037)

- Status: Accepted
- Date: 2026-11-23
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1856, ADR-0757 (brief #1815), ADR-0756 (brief #1813), ADR-0752 (brief #1800), ADR-0479,
  ADR-0650, ADR-0393, ADR-0285, plan #661
- Requirements: REQ-037

Protected classes: `scripts/agk/`, `agk.toml`, `kit/hashes.json`, `tests/kit/`

## Context

Four builders stopped on 2026-11-23 at session rule 21 for one reason: their build needed `agk.toml` (a protected class)
and their brief's `Touches:` did not name it. A new `scripts/agk/*.py` needs a `[[testing.map]]` entry (the kit test
`test_every_script_is_covered_by_an_entry_or_always_full`), a new whole test joins `[testing] whole_tests`, and a test
that starts naming a script that left `always_full` joins that script's map entry. `check_brief.brief_result`, the one
reading every writer uses (ADR-0756), never read `Adds:` against `[testing]`. The owner's word (2026-11-23, the steward
chat, quoted as data): "Ok", then "Yes, go ahead".

## Decision

1. `check_brief.testing_problems(body, root, today, filed)` returns (failures, warnings) and runs in `brief_result`
   after `brief_study.study_result` passes, so the brief workflow, the steward's filing, fixing and triage,
   `plan_intake.py publish`, the conductor's guard and `steward_evidence.triage` read it alike. It reads only files.
2. Rule 4c applies only where the root's `[testing]` table exists (read by `impact.testing_table`, which still refuses
   a bad table naming its setting) and no `Touches:` glob matches `agk.toml` (`impact.matches`).
3. In the kit (`kit/agk-kit.mk` is a file), an `Adds:` entry matching `scripts/agk/*.py` (one level) that no curated
   map `code` glob and no `always_full` glob covers gives `rule 4c: Adds names a new script of the class scripts/agk/
   ...` (answer 1), whatever `profile` or `map_source`. Where `whole_tests` is set, a body line naming an added test
   file (its path or its file name) with `whole_tests` or `whole test` gives `rule 4c: line <n> adds a whole test ...`
   (answer 2). Both fail for a brief filed on or after `[flow] brief_study_fails_from` (`brief_study.enforced`, by
   `created_at`, else today, ADR-0757) and warn before it or when the day is unset.
4. Warnings only: an added test file beside an answer `**The class stays closed.**` when no line states a whole test
   (answer 2); one line per brief naming the folder classes of the test files in `Adds:` or `Touches:` that no
   `tests` glob of the map entries of a touched code path lists (answer 3); in a project (no `kit/agk-kit.mk`), with a
   curated map and profile `balanced` or `fast`, one line per folder of a new non-test file that nothing covers when
   another file of that folder in the tree is a map entry's code (answer 4).
5. A `Reserved:` line that lists path classes without `agk.toml`, in a brief whose `Touches:` names `agk.toml` and
   whose root protects it, warns `rule 4b: Touches names agk.toml and the Reserved line's path classes leave it out`.
6. Messages name the rule, the class and the setting, never a file of the brief. Q-HL-1 (no new day: the study's day
   is shared), Q-HL-2 (`agk.toml` still counts as a code path) and Q-HL-3 (no MALFORMED in `session.brief_shape`) take
   the brief's conservative readings.
7. Path classes changed: `scripts/agk/` (`check_brief.py`), `agk.toml` (the new test joins the `check_brief.py` map
   entry), `kit/hashes.json` (regenerated) and `tests/kit/` (`test_check_brief_testing_map.py`).

## Consequences

A brief that adds a kit script, a whole test or a mapped test is told at filing to name `agk.toml`, so its builder no
longer stops for it; briefs filed before the refuse day are warned only, never refused or MALFORMED. A project's
curated map is warned when a new file of a file-by-file mapped folder would go unselected; it is never refused.

## Residual

Open briefs filed before the refuse day (#1835, #1840) are warned only; the steward may propose their body edits and
the owner applies them. Whether `agk.toml` should leave the code-path count (Q-HL-2), refuse from an earlier day of
its own (Q-HL-1) or make a brief MALFORMED (Q-HL-3) is left to the owner's own brief.
