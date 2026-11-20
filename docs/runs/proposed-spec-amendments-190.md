# Proposed spec amendments 190 (SPEC-0032; REQ-039)

Date: 2026-11-20 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0653 (brief #1555), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0032-github-events-label-each-pr-people-approve-specs-a-red-branch-stops-work.md` (rules 1, 7 and 8, a new
rule 15, and the `## Contexts` section). Brief #1555 reserved amendment 190. This file proposes the lines and does not
edit the spec. Build (a) applies them word for word, on a person's `Approve: SPEC-0032` on its pull request; no session
posts it.

The sentence (brief #1555): "Which GitHub jobs a repository runs is one setting, `full`, `events` or `off`, read by each
kit workflow without a billed job and switched by one command, and each thing a value turns off has a named owner, in
the kit and in every project."

The owner's word, quoted as data (brief #1555, 2026-11-19, the co-owner chat): "Lets decide all off or keep both as a
setting , why we need to hard push , is there any issue on this approach ?"; on Q-7, "In private default kep events";
on Q-9, "Make default off on clean Layout projects".

## What is on the default branch today

Read in the code by this session on main at a948d695 (2026-11-20), after brief #1554 (#1563, ADR-0654) merged. The
brief traced 5a5ebf9d; where a line moved, the new line is named:

- `.github/workflows/` holds 9 workflows; `kit/manifest.json` installs 8 (`agk-brief`, `agk-route`, `drift-audit`,
  `governance`, `merger`, `metrics`, `product-report`, `proof`); `agk-tag.yml` is the kit's own.
- The jobs and their `if:`: `agk-route` (one job, line 63), `merger` (`merger` line 72, `sweep-gate`, and `sweep` that
  needs it), `governance`, `proof`, `agk-brief`, `drift-audit` (`report`, and `file` that needs it), `metrics`,
  `product-report`, and `agk-tag` (no `if:`). `merger.yml`'s `workflow_run` now listens only to `gh-readonly-queue/**`
  (ADR-0654 decision 2), and the merger's comment job and `sweep-gate` already read `vars.AGK_MERGER`.
- `local_mode.py` `VERBS` (line 57) and `SESSION_SETTING = "CLAUDECODE"` (line 64): `enter` and `leave` are all or
  nothing. `doctor.py` `local_switch_result` is now line 889, `common.execution` line 1364, `merge_cleared.py`
  `close_brief` line 1345, `github_mode` line 1962, `local_mode` line 2572, `holds` line 2578, `queue_mode` line 2628,
  `route.py` `finish_brief` line 998, `route_branch` line 1233, `route_health` line 1309, `OWNER_ANSWER_LINES` line 1481
  (it holds `Answer:`), `main` line 1506, `upgrade.py` `CLEAN_KEPT` line 944 and `clean_refusal` line 959.
- `kit/templates/ruleset.json` `phase2_rules` requires the status check `governance`; `merge_cleared.py` reads GitHub's
  `rule violation` (line 322) as held by the ruleset.
- There is no `actions` key in `agk.toml` or `kit/templates/agk.toml`, and no `AGK_ACTIONS` in any workflow.

## Items

1. **Rule 15 (new), which jobs run.** Added after rule 14:

   "15. **Which jobs run.** A repository runs its kit workflows by one top-level setting of `agk.toml`, `actions`, with
   the value `full`, `events` or `off`; absent reads as `full`. `full` is every kit workflow as rules 1 to 8 say.
   `events` keeps only the comment jobs of the router (`agk-route.yml`) and the merger (`merger.yml`), with their
   first-line conditions; every other event of the two and every job of the other kit workflows starts no job. `off`
   keeps no kit workflow. `events` and `off` are refused unless `execution = "local"`; a clean-layout project
   (SPEC-0071) takes `off` only; personal mode (`forge = "files"`) refuses the setting, since it installs no workflow.
   Each refusal names the setting, and the layout or the mode, never a value. A job `if:` cannot read `agk.toml`, so
   each job of each kit workflow reads the repository variable `AGK_ACTIONS` in its `if:` (unset reads as `full`), and a
   job that a value turns off is skipped, billing nothing; a workflow the value turns off is also disabled, so it creates
   no run. One command, `local_mode.py actions full|events|off`, prints and, with `--write` outside an agent session,
   makes the variable's call and each kit workflow's enable or disable, and refuses `--write` while the value differs
   from `actions` on the default branch; it touches no workflow of the project's own. No value posts a status or a check
   run for a check that did not run (principles 2 and 11), so under `events` and `off` the required checks never report
   and the ruleset holds each merge until the owner changes it; no session changes the ruleset. `doctor.py` row
   `actions-setting` (GET only) compares the setting, the variable and each kit workflow's state, and reports a
   difference naming the setting and the variable. The default proposed by setup and `/agk:upgrade`, which a person
   confirms (SPEC-0072 rule 8): `full` for a public repository, `events` for a private one, `off` for a clean-layout
   project; nothing switches on its own when the visibility changes, and `doctor.py` says so."

2. **Rule 7, a red default branch, one sentence at the end.** "Under `actions = "events"` or `"off"` (rule 15) no
   governance run reports on the default branch, so the supervisor's pass (SPEC-0064), on the machine that holds the
   plan lease, reads each new head of the default branch by local `git`, and for a head whose commit lacks
   `Merged-by: merge_cleared.py` runs SPEC-0039 rule 6's after-merge governance run once, through the same function and
   lock, opens or updates this issue on red through the router's function, closes the brief the merged body finishes and
   runs the health issues once per pass; without `[autopilot]` `doctor.py` warns that nothing raises this issue after a
   person's merge and prints `failures.py run --on default` for the person."

3. **Rule 8, what it does not do, one sentence at the end.** "Under rule 15's `events` the router runs only on a
   comment, and under `off` not at all; the conductor's `route.py --all` then moves the labels on its pass, and the
   unpark on an owner line waits for the supervisor's pass."

4. **Rule 1, the router, one sentence at the end.** "Which of these events start a job is rule 15's setting."

5. **The `## Contexts` section, two entries rewritten.** Each stays one line with no semicolon outside brackets, as
   `check_specs.py` joins the section's lines with `; ` and cuts them there. The `github` entry becomes:

   ```
   - github: the router workflow runs on each comment, push and finished check and sets the label, with no workflow change (rules 1 and 2), and with `actions = "full"`, absent or a public repository's default, every kit workflow runs as today (rule 15)
   ```

   and the `local` entry becomes:

   ```
   - local: a laptop builder that stops posts the same `Report:` line and gets the same label at the router's next event (rules 2 and 3), and `actions = "events"` or `"off"` keeps only the comment jobs or none, the conductor's pass labels and merges and the supervisor's pass raises the red-branch issue and closes briefs (rules 7, 8 and 15)
   ```

   The `kit`, `personal` and `stacks` entries are unchanged; `personal` stays true, since rule 15 refuses the setting
   there by name.

6. **The `## Tests` section, one line added.** "- Rule 15: each kit workflow's job `if:` per value of `AGK_ACTIONS`, the
   setting's refusals, the switch's dry run and refusal, doctor's `actions-setting` row, and the after-merge pass of a
   person's merge under `events` and `off`; REQ-039 AC1 and AC5."

7. **Unchanged:** rules 2 to 6 and 9 to 14, the Proof, the Residual and the `kit`, `personal` and `stacks` contexts.
   ADR-0654 stands; `AGK_MERGER` stays independent of `AGK_ACTIONS` (Q-1555-6).

## What each value keeps, and who does it

| | `full` (absent: today) | `events` | `off` |
|---|---|---|---|
| workflows enabled | all 8 (the kit: 9) | `agk-route.yml`, `merger.yml` | none of the kit's |
| jobs that start | as today (ADR-0654's gates) | router and merger on `issue_comment` only | none; no run is created |
| `execution` | any | `local` only | `local` only |
| required checks on GitHub | report | never report | never report |
| ruleset (requires `governance`) | met by CI | each merge is the admin's call until the owner changes it | the same |
| labels | the router, on every event | the router on a comment; a push waits for the conductor's `route.py --all` | the conductor's `route.py --all` on each pass |
| unpark on an owner line | seconds (router) | seconds (router) | the supervisor's pass, at most `interval_minutes`; with no `[autopilot]`, the next sweep |
| owner's `Merge:` line (#1539), local | the supervisor's pass | the same | the same |
| brief close on a merge | router and guarded merge | the guarded merge; a person's merge: item 2's pass | the same as `events` |
| "The default branch is red" | governance on push plus the router | the guarded merge's after-merge run; a person's merge: item 2's pass | the same as `events` |
| health issues | the router | the router on comments, and item 2's pass | item 2's pass only |
| brief check on filing | `agk-brief.yml` | `check_brief.py` by the `brief` skill | the same |
| drift audit, metrics, weekly report | weekly on GitHub | by hand | by hand |
| tag check (kit) | `agk-tag.yml` | `release_pack.py`'s local run | the same |

Billed minutes a day, as brief #1554 measured them (its 23-hour window, x 24/23): the kit `full` 1,237 before #1554 and
about 1,171 after; `events` about 279 after #1554 with `AGK_MERGER = off`; `off` 0. A five-builder private customer
project with the defaults: `full` about 447 after #1554, `events` about 110 to 135, `off` 0 (scaled as #1554 scaled it,
verify on a real project). A public repository bills none; there the value only cuts the runs on the Actions list and
the run-list reads.

## The builds

Each from the default branch, filed later by the `brief` skill with its own Settings section and `Depends-on:` this
intake, tests first, about 300 changed lines or fewer, invented data only (example.com), no network and no model in
checks. No existing assertion is removed or loosened (principle 11).

- (a) `config.py` `actions_mode(root)` with its refusals, `kit/templates/agk.toml`'s commented key, `doctor.py`'s
  `actions-setting` row (the variable read `GET repos/{owner}/{repo}/actions/variables/AGK_ACTIONS`, `cannot-check` when
  the token cannot read it, verify the permission; `local_switch_result` reads the setting, so under `events` the two
  active workflows are expected), and items 1 to 6 applied to the spec word for word on the owner's `Approve: SPEC-0032`.
- (b) the job `if:` gates: every job of the 8 installed workflows and `agk-tag.yml` gains `vars.AGK_ACTIONS != 'off'`;
  the jobs of `governance`, `proof`, `agk-brief`, `drift-audit`, `metrics` and `product-report` and `agk-tag` also gain
  `vars.AGK_ACTIONS != 'events'`; in `agk-route.yml` and `merger.yml` `events` keeps only
  `github.event_name == 'issue_comment'` with today's first-line conditions. A job that `needs:` a gated job (the
  merger's `sweep`, the drift audit's `file`) is skipped with it. A test reads each job `if:` and asserts the gate per
  value. A workflow change: the owner merges it by hand (session rule 30).
- (c) `local_mode.py actions full|events|off [--write]`; `enter` also sets the variable to `off`, `leave` enables the
  kit workflows the setting keeps and restores the variable; `docs/guides/local-mode.md`, with `agk-tag.yml` added to
  step 1 and Leave step 1.
- (d) item 2's after-merge pass in the supervisor, `doctor.py`'s warning without `[autopilot]`, and the lines of
  `docs/runbooks/red-default-branch.md` and `docs/runbooks/actions-blocked.md`.
- (e) `upgrade.py` and `setup.py` print, never run, the switch's dry-run line on a difference, read the visibility once
  (`gh api repos/{owner}/{repo}`, never in a check) to propose the default, and `upgrade.py --clean-repo` writes
  `actions = "off"`.

## Tests (the builds)

- a mismatch: `actions = "events"` with the variable `full`: doctor fails `actions-setting` naming both, and
  `local_mode.py actions events` prints the calls that bring them together;
- switching with a pull request at `agk:ci-running`: `route.py --all` relabels it from the builder's `Evidence:` line;
  `off` to `full`: `leave` says to push a new head;
- a red default branch under `off`: a head without `Merged-by: merge_cleared.py` and a red run opens the issue, and the
  next guarded merge is held;
- a required check that never reports under `events`: `route.py --all` reads an `Evidence:` line as green and a
  `prepush: stopped at` line as red, and `merge_cleared.py` reads the ruleset's `rule violation` as held;
- no variable and no key: every job runs as today and doctor reports nothing;
- `events` or `off` with `execution = "hosted"`, `"hybrid"` or `"pool"`: refused by name, and the switch refuses
  `--write`; a clean-layout project with `full` or `events`: refused; personal mode: refused;
- a run created under `events` for a lease edit or a push: skipped by `if:` (ADR-0654's tests extended).

Marker `REQ-039 AC1` and `REQ-039 AC5`.

## The settings, each with its impact, traced

| Setting | Impact |
| --- | --- |
| `execution` | `hosted`, `hybrid`, `pool`: only `full`, since `ci_evidence` needs a green run of each required check; `local`: any value |
| `[flow] auto_merge`, `auto_merge_method` | `false`: nothing merges by itself in any value; `true` under `events` or `off`: the guarded merge runs and the ruleset holds it until the owner changes it, and doctor fails `actions-setting` while the ruleset requires a check of `required_checks` |
| `[flow] merge_queue` | GitHub mode only, so unused under `events` and `off` (`queue_mode` is false in local mode) |
| `required_checks` | unchanged; under `events` and `off` the labels come from the builders' `Evidence:` lines (brief #1212) |
| `[flow] owner_wait_minutes`, `owner_rest_hours`, `owner_utc_offset` | parks unchanged; the unpark latency is the value's (the table) |
| `[autopilot] mode`, `interval_minutes` | under `off` they bound the wait for an unpark and a `Merge:` line; absent with `off` or `events`: doctor warns (item 2) |
| `[flow] plan_issue`, `builder_start` | the lease is unchanged; under `off` only item 2's pass writes the health issues |
| `review_mode = "solo"` | the person's confirmation is labelled by the router in seconds under `full` and `events`, and on the conductor's pass under `off` |
| `paused` | unchanged: every job and pass prints its paused line |
| `AGK_MERGER` (ADR-0654) | independent: under `events` it still gates the merger's comment job; doctor reads both |
| `[kit] layout` | the classic layout takes any value the other rows allow; the clean layout takes `off` only |
| `forge = "files"` | personal mode refuses the setting by name |
| `pr_mode`, `[testing]`, `[models]` | no effect |

No ruleset, required check or secret changes; build (b) changes the workflows, and the owner merges it.

## Customer projects

A public repository bills no minutes, so `full` costs nothing and `events` or `off` only cut noise. A private one saves
the table's minutes. Hosted mode keeps `full`; local mode takes any value; personal mode is refused. One variable and one
`agk.toml` per repository, so every machine of a team reads the same value; the switch is one admin's, and item 2's pass
runs on the lease holder's machine only. With Actions disabled for the repository by an organisation's policy the jobs
never run whatever the value, and doctor reads `GET repos/{owner}/{repo}/actions/permissions` and says so by name. An
organisation variable of the same name applies to a repository without its own (verify the precedence); the kit sets
only the repository's, and the guide says so. No project file is rewritten by an upgrade without the person's confirm.

## Questions (brief #1555), each with the reading this proposal takes

- Q-1555-1: the setting's name and place. Reading: top-level `actions` beside `execution`, and the variable
  `AGK_ACTIONS`. A reviewer may rename both before build (a).
- Q-1555-2: should `events` keep the router's `pull_request` `closed` job? Reading: no, comments only, as the owner named
  it; item 2's pass closes the brief.
- Q-1555-3: are `events` and `off` refused outside `execution = "local"`? Reading: yes; a hosted project with governance
  off would hold every merge forever.
- Q-1555-4: does item 2's after-merge pass belong in these builds? Reading: yes, build (d). Until it lands, doctor warns
  and the runbook names `failures.py run --on default`.
- Q-1555-5: does the switch touch a project's own workflows? Reading: no; only `enter`, for a block, keeps today's scope.
- Q-1555-6: should `AGK_ACTIONS` absorb `AGK_MERGER`? Reading: no; they stay independent.
- Q-1555-7: the default. The owner's answer (quoted above): `events` for a private repository, `full` for a public one,
  proposed by setup and `/agk:upgrade` and confirmed by the person; absent keeps today's behaviour until confirmed.
- Q-1555-8: priority. Reading: 2.
- Q-1555-9: a clean-layout project. The owner's answer (quoted above): `off`, whatever its visibility; `events` and `full`
  are refused there, and no workflow file is added to a clean project.
