# Proposed spec amendments 149 (SPEC-0034, SPEC-0006; REQ-041)

Date: 2026-11-09 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written
for brief #842, whose build (a) is ADR-0384; that ADR's residual leaves the capacity table to this amendment. The paths:
`docs/specs/0034-a-team-sets-how-many-builder-sessions-run-at-once-and-agk-ha.md` and `docs/specs/0006-doctor.md` (rule
5, item 9 only). The number 149 is the one brief #842 reserved. This amendment is not applied to the spec text in this
pull request; the owner decides it, and it needs a person's `Approve: SPEC-0034` and `Approve: SPEC-0006`; no session
posts them, and builds (b) and (c) start only after them.

The brief names "SPEC-0034 rules 2 and 15". Rule 2 is the brief shape; the capacity is rule 1, so this amendment changes
rules 1 and 15. Rule 15 is the rule amendment 88 added (its items 1 and 3), and item 3 of that amendment is what changes
here, with the default that ADR-0384 already changed.

1. **Rule 1, one capacity table.** Add: "`agk.toml` may have a `[capacity]` table with `profile` (`auto`, `full`,
   `balanced`, `small` or `fixed`; `auto` when the table omits it), the ceilings `max_builders`, `reviews_in_flight`,
   `builder_memory_gb`, `builder_cpus` and `builder_disk_gb`, and `review_minutes` (default 15), each number whole and 1
   or more. `max_builders`, `reviews_in_flight` and `builder_memory_gb` of `[flow]` keep working and are read as
   ceilings; where a key is in both tables the smaller value is the ceiling. An unknown key or a wrong value is refused,
   naming `setting: capacity.<key>` and never the value."
2. **Rule 1, the profiles.** `full` uses every ceiling as given and measures nothing. `balanced` keeps 25 percent of the
   machine's memory, CPU and disk free. `small` keeps 50 percent free and runs at most 2 builders at once. `fixed` uses
   `max_builders` only: no other ceiling and no measured figure. `auto` is item 4. A reserve is taken only from a figure
   whose per-builder ceiling is set: with no `builder_disk_gb`, disk is not counted.
3. **Rule 15, the sessions to start.** Item 3 of amendment 88 reads: "The sessions to start are the smallest of the
   ready non-overlapping briefs and the capacity less the running builders, where the capacity is what the profile
   gives; the pull requests waiting for a verdict (ADR-0384, decision 4) count against `reviews_in_flight`, which is
   `max_builders` when unset." The merge queue limit (amendment 88 item 4) applies under every profile, as today.
4. **Rule 15, measured each pass (`auto`).** The plan takes the smallest of the ceilings and of what it measures on the
   machine that runs the builders: available memory over `builder_memory_gb`, free cores (`os.cpu_count()` less the
   one-minute load) over `builder_cpus`, and free disk under the repository over `builder_disk_gb`, each rounded down.
   Where each builder runs in its own container (`[capacity] builders_run = "cloud"`; `here` by default, `Q-842-3`) the
   machine figures do not apply and the plan counts the account's refused starts (item 6). A figure that cannot be read
   prints `unknown` and is left out, never read as 0. The floor of 1 while no builder runs (ADR-0223) stays.
5. **Rule 15, adapted by evidence (`auto`).** With no history the count is the smallest of item 4. It rises by one each
   pass, never above that smallest figure, while starts are accepted, checks stay under their usual minutes and the
   conductor's review time (minutes from a `Report:` that asks for a verdict to the `Verdict:` on its head) stays under
   `review_minutes`. It drops by one after a refused start, a memory or disk figure under its reserve (25 percent of the
   machine, as `balanced`, `Q-842-5`) or reviews over that time, never below 1. "Usual" is the median duration of the
   last 20 successful `governance` runs, 1.5 times over (`Q-842-6`); review time is the median of the last 10 verdicts.
   A condition that cannot be read is left out, and counts neither way. The last 20 changes are kept in the plan's
   output.
6. **Rule 15, where the evidence lives (`Q-842-2`).** Rule 15 says the plan posts and writes nothing. `plan --record`, a
   new flag, appends one line per pass to a path kept out of git; `plan` alone reads that file and writes nothing. No
   record means no history: the count is the smallest of item 4, and refused starts read `unknown`. No check reads it.
7. **Rule 15, always said.** Every plan prints `Capacity: <n> of <ceiling> (<profile>; limit: <name> <figure>)`,
   replacing the line of ADR-0223; with no `[capacity]` table the profile prints as `none`. Every `Start 0` names the
   limit and its figure. A figure is a measured number or `unknown`; a setting is named, never a secret value.
8. **Rule 1 and rule 6, what else reads the capacity (`Q-842-4`).** `session.py next` (`full <open>/<max>`), `demand`
   and `builder_slots` read the ceiling of item 1 and measure nothing; only `plan` measures. Their output does not
   change.
9. **SPEC-0006 rule 5 (a consequence of item 7).** `doctor.py` prints the profile, every ceiling and every measured
   figure, and suggests a profile for the machine: `small` under 8 GB free, `balanced` under 32 GB, `full` above. It is
   one row `capacity`, severity `warn` only on a refused table, otherwise a printed line that never fails the run.
10. **Every mode.** GitHub, local and personal projects read the same table with the same defaults. A project with no
    `[capacity]` table behaves as today, apart from ADR-0384 and the line of item 7. The exception is a personal project
    (`forge = "files"`), which reads `profile` as `small` when no table sets it (`Q-842-7`). Nothing here needs a
    workflow, a ruleset, a required check or a network call in a check.
11. **Rule 13, the builds.** Build (a) is merged (ADR-0384). Build (b): items 1 to 3 and 7 to 10, with the measured
    reserves `balanced` and `small` need; `auto` reads as the ceilings alone until build (c). It corrects the default of
    3 that `docs/guides/getting-started.md` still states (`Q-842-1` of #844). Build (c): items 4 to 6. Each is tests
    first and about 300 changed lines or fewer, in `tests/kit/test_capacity_profiles.py` and
    `tests/kit/test_capacity_adapt.py`.
12. **Not in this amendment.** Rule 15's waves, merge queue, safe merge set and drift are unchanged. `constitution/`,
    the workflows, the ruleset and the required checks are not touched. Answer 4 of brief #798 is taken by this brief,
    as #842 says; no `docs/runs/capacity.jsonl` is built.

## Questions

Each is open until a person rules; the reading after it is the conservative one the items apply.

- **Q-842-2, for the owner before build (c):** where does the evidence live? `plan` writes nothing, the conductor's
  guard refuses writes outside a scratch folder, and a file rewritten every pass is a generated file (principle 5). It
  is the same question as `Q-772-1`. Reading: `plan --record` to a path kept out of git, and no history (so no adapting)
  where it is absent, which on cloud sessions is every pass until the owner picks a home.
- **Q-842-3:** what says builders run in the cloud? No setting or detection exists today. Reading: a typed key,
  `builders_run`, default `here`, which the brief's list does not name; no reading of the runtime's environment.
- **Q-842-4:** should `next` and `demand` measure too? Reading: no; they gate on the ceiling, and the plan alone
  measures.
- **Q-842-5:** `auto` has no reserve of its own in the brief. Reading: `balanced`'s 25 percent, the lower of the two
  readings of a drop.
- **Q-842-6:** "their usual minutes" is not defined. Reading: as item 5; a project with fewer than 20 runs has no usual
  and the condition is left out.
- **Q-842-7:** answer 6 says both that a project with no table behaves as today and that personal mode defaults to
  `small`. Reading: the specific sentence decides for personal projects only. `session.py` reads no personal setting
  today, so build (b) reads `forge = "files"` from the sidecar.
- **Q-842-8:** a refused start is recorded nowhere today (`conductor.py` prints re-fire lines and fires nothing, and a
  start refused by the account never reaches the repository). Reading: until a person names the source, refused starts
  read `unknown` and are left out of item 5.
- **Q-842-9:** the reserved `ADR-0384` is spent on build (a), which leaves this table undecided. Reading: this pull
  request adds no ADR and takes no new number; builds (b) and (c) each change a decision, so each asks the conductor to
  reserve one.
