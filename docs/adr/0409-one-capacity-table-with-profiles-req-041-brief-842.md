# ADR-0409: One capacity table with profiles decides how many builders start

- Status: Accepted
- Date: 2026-11-10
- Deciders: maintainers
- Related: SPEC-0034 rules 1 and 15, SPEC-0006 rule 5, amendment 149, ADR-0384, ADR-0223, ADR-0153, brief #842
- Requirements: REQ-041

Protected classes: `agk.toml`, `scripts/agk/`, `tests/kit/`

## Context

Amendment 149, applied to SPEC-0034 and SPEC-0006 on the owner's `Approve:` lines, gives `agk.toml` one `[capacity]`
table with five profiles, so that a fast machine runs at full force and a small one runs a best fit. Build (a)
(ADR-0384) only made `reviews_in_flight` follow `max_builders`. This is build (b): amendment 149 items 1 to 3 and 7 to
10, with the measured reserves that `balanced` and `small` need. Measuring and adapting under `auto` (items 4 to 6) is
build (c).

## Decision

1. `config.py` reads the `[capacity]` table: `profile` (`auto` when omitted), the ceilings `max_builders`,
   `reviews_in_flight`, `builder_memory_gb`, `builder_cpus`, `builder_disk_gb`, and `review_minutes` (15). Every number
   is whole and 1 or more. An unknown key or a wrong value is refused as `setting: capacity.<key>`, never the value. A
   personal project (`[personal] forge = "files"`) reads `profile` as `small` when no table sets it. `builders_run`
   (item 4) is not accepted until build (c) reads it.
2. `session.py plan` takes each ceiling as the smaller of `[flow]` and `[capacity]`; `reviews_in_flight` is the
   `max_builders` ceiling when neither table sets it.
3. The profiles: no table (`none`) and `auto` keep today's figures, the `[flow]` memory figure of ADR-0223 with no
   reserve; `full` measures nothing; `balanced` keeps 25 percent and `small` 50 percent of the machine's memory, cores
   and disk free, each counted only where its per-builder ceiling is set, and `small` starts at most 2; `fixed` uses
   `max_builders` only, and the pull requests waiting for a verdict count against it. A figure is
   `floor((free - reserve x total) / per builder)`, never below 1 while no builder runs. Free cores are
   `os.cpu_count()` less the one-minute load; disk is the disk under the repository; total memory is read with
   `os.sysconf`. A figure that cannot be read is `unknown` and left out.
4. Every plan prints `Capacity: <n> of <ceiling> (<profile>; limit: <name> <figure>).`, replacing the line of ADR-0223,
   followed by ` Unknown: <names>.` when a counted figure cannot be read. A `Start 0` held by a profile figure names it.
5. `agk.toml` maps `tests/kit/test_capacity_profiles.py` to `session_plan.py`, `config.py` and `doctor.py` in
   `[[testing.map]]`, and `docs/guides/getting-started.md` no longer says `reviews_in_flight` is 3 by default.
6. `doctor.py` gains the `capacity` row (`warn`): a refused table fails it; otherwise it prints the profile, the
   ceilings, the measured figures and the suggested profile (`small` under 8 GB free, `balanced` under 32 GB, `full`
   above), and it never fails the run. With `--api-dir` every figure prints `unknown`, so that two runs print the
   same bytes (SPEC-0006 AC1); a live run measures (the maintainer answer to Q-842-17).

## Consequences

A project with no `[capacity]` table starts what it started before; only the wording of its capacity line changes. A
team picks `balanced` or `small` to keep room on a shared or small machine, and `full` to ignore the machine. The plan
reads three more figures each pass, all local and without a new dependency.

## Residual

- 2026-11-10: `session.py next`, `demand` and `builder_slots` still read `max_builders` of `[flow]` only, because
  `scripts/agk/session.py` is not in the brief's `Touches:` line (Q-842-13).
- 2026-11-10: `auto` reads as `none` until build (c) measures and adapts (amendment 149 item 11).
