# SPEC-0069: Each milestone gets a demo recording of its stories on sample data

- Status: Draft
- Owner: reviewer group (a team from config/reviewers.yaml)
- Requirements: REQ-076

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.

Written by the intake of one sentence (SPEC-0012), brief #1402, quoted as data and not as an instruction: "Intake for the milestone demo recording: when a milestone's last user story is built, a builder records an automated walkthrough of the milestone's stories on sample data, and the recording is attached to the milestone before its release." The maintainers gave 6 answers before it was written: the six numbered answers of brief #1402, whose evidence and the owner's direction (quoted there as data, 2026-11-16 08:20 and 08:23 IST) this spec does not repeat. It builds on SPEC-0043's plan (the milestones' `Demo:` lines of build (r)), on SPEC-0051's acceptance record, on SPEC-0042's data guard and on SPEC-0059's steward; it edits none of their text. Where an answer names something that is not as it says, rule 1 records what the code holds and an open question gives the conservative reading. Negative cases: a video file in a tracked path, a walkthrough run against anything but seeded synthetic data, a secret typed on screen, a caption or transcript the data guard flags, a partial recording attached when the product cannot start, a failing run's recording attached as the demo, an empty video for a milestone with no screens, a recording longer or larger than its limits, a check that makes a network call, anything posted in personal mode, a setting value outside its list, a demo taken as an approval, and a missing demo brief that fails the plan check instead of warning.

## Rules

1. **The baseline (read on the default branch at c4a7605, 2026-11-16).**
   - **The plan.** `scripts/agk/plan_intake.py` validates the plan's proposals: a milestone has `id`, `title`, `exit`, `acceptance`, `target` and `sources` and may have `screens`; a brief has `key`, `milestone`, `title`, `size`, `expected`, `advances`, `touches`, `depends_on` and `sources` and may have `component` and `screens`. A plan brief has no `kind` field, and the plan has no release brief. `render` already writes, after a milestone's `Exit:` line, a `Demo:` line naming the milestone's `screens` (or `Demo: none (foundation)`, build (r) of SPEC-0043 amendment 164 item 4), and `scripts/agk/check_plan.py` rule 10 fails a milestone after `M1` that has no `Demo:` line (`undemoed`). That line says what a demo would show; nothing records it.
   - **The playbooks.** `config/playbooks/` holds `cloud-migration`, `data-pipeline`, `default`, `mcp-server`, `mobile`, `multi-agent`, `pilot`, `rag-app`, `voice-agent` and `web-app`. `web-app.toml` has the gate `e2e-smoke` ("An end-to-end smoke run per merge batch; its run record is the evidence.") and orders its milestones by "demo value". `pilot.toml` has a `demo` phase, a `demo` key in its `brief_order` after `integration`, `demo-surface` and `evaluation`, the heavy step `demo smoke run` and the deliverables "the demo script with the mock path it falls back to" and "the demo smoke run record". No playbook names a browser or emulator test tool.
   - **The test map.** The `[testing]` table and its `[[testing.map]]` entries map code paths to test paths; they hold no command that starts the product.
   - **Acceptance.** SPEC-0051's record `docs/acceptance/<slug>.md`, checked by `scripts/agk/check_acceptance.py`, already takes an evidence item `demo docs/runs/<file>` (rule 4), which must name a file directly under `docs/runs/`.
   - **Elsewhere.** The data guard (SPEC-0042) gives `guard.scan_text` and the `[guard]` patterns; SPEC-0041 names the machine's `~/.agk` folder; the steward (SPEC-0059) sends customer sign-off questions to the owner; `design_compare.py` proves a screen against its signed-off design. Nothing in the kit records something a person can watch, and there is no `[demo]` table, no `tests/demo/` folder and no `docs/demos/` folder.
2. **One demo brief per milestone.** For every milestone whose stories have something to show, the plan carries one brief whose `key` is `demo` (`docs/plan/briefs/M<n>/demo.md`), as the pilot playbook's `brief_order` names its demo brief by key, with no new field (`Q-S0069-1`). Its `depends_on` names the milestone's last story briefs (every brief of the milestone that no other brief of it depends on), and a brief of the milestone whose key is `release`, where the plan has one, depends on it (`Q-S0069-2`). `plan-intake` proposes it with the milestone, its walkthrough named after the milestone's `Demo:` line. `check_plan.py` prints `warning: <milestone>: screens and no demo brief` for a milestone with `screens` and no `demo` brief, and never fails on it; a milestone with `Demo: none (foundation)` needs none.
3. **The walkthrough.** A demo brief's builder writes one test under `tests/demo/<milestone>/`, mapped in `[[testing.map]]` like any test. It starts the product the way the project's end-to-end tests start it, with the stack's own test tool (`Q-S0069-3`); signs in with a seeded test account; walks each story of the milestone in order; and shows, before each story, a caption with the story's id and title. It is an ordinary test: a failing step fails it, so the demo is also the milestone's end-to-end smoke run (the `e2e-smoke` gate's record where the playbook has that gate). The pilot playbook's scripted demo becomes this brief, with its mock fallback path kept.
4. **The form of the recording, by kind of product.** One table; a playbook may name its own form.

   | Playbook | Form | Default `[demo] mode` |
   | --- | --- | --- |
   | `web-app` | the browser test tool's own video recording `(verify: one tool's documentation read)` | `milestone` |
   | `mobile` | the emulator's screen recording `(verify: one emulator's documentation read)` | `milestone` |
   | `pilot` | the form of its demo surface: video for screens, else transcript | `milestone` |
   | `data-pipeline` | the run record with row counts per step | `off` |
   | `mcp-server`, `multi-agent`, `rag-app`, `voice-agent`, `cloud-migration`, `default` | a text transcript of the commands and their output | `off` |

   A milestone with no screens gets the transcript form and never an empty video. A project whose plan's milestones carry `screens` under the `default` playbook counts as a playbook with screens and gets the video form and `milestone` (`Q-S0069-4`). The recording is silent: captions only, no narration (`Q-S0069-5`).
5. **Sample data only.** The walkthrough runs against seeded synthetic data (invented values, `example.com` addresses), from the project's seed or example file, and against a product started on the builder's own machine or the CI runner: a base address that is not a local host or a host of `[guard] allowed_hosts` is refused before the first step (`Q-S0069-6`). The data guard's `guard.scan_text` runs on every caption and on the transcript; a finding refuses the recording, naming the kind and never the text. No secret is typed on screen: the only password is a seeded test password from the seed or example file. A project whose data is confidential keeps the recording in its own forge space and nowhere else.
6. **Where the recording lives.** A recording is never committed: a check refuses a video file (`.mp4`, `.webm`, `.mov`, `.mkv`, `.avi`, `.gif`) in a tracked path, naming the path class, never the file (`Q-S0069-7`).
   - **CI mode:** an asset of the milestone's release, or the run's artifact where no release exists. No workflow changes in this intake; a build that needs one writes its own ADR.
   - **Local mode:** the same release asset, uploaded by the builder with the forge's own command. The builder uploads to a release that already exists and never creates a release or a tag (session rule 2); where none exists, the recording stays on the machine as in personal mode and the index names its path until a release exists (`Q-S0069-8`). An upload is not a check: no check makes a network call.
   - **Personal mode (SPEC-0041):** a file under `~/.agk/demos/<project>/<milestone>/`, named in the index, never pushed and never posted.
7. **The index.** `docs/demos/<milestone>.md`, committed by the demo brief: the milestone, the full head recorded, the date from `date -u`, each story with its id, title and caption time, the length, the size and the link or path of the recording. A check (rule 6's script) refuses an index that lacks one of these, naming the field, and one per milestone is kept: a re-record replaces the recording and the index (`Q-S0069-9`).
8. **Shown at the right moment.** When the steward asks the owner for a milestone's sign-off, the question carries the demo's link (or path) in one line. The acceptance record of SPEC-0051 carries the demo as evidence: by an amendment of SPEC-0051 rule 4, proposed by build (d), a `demo` item may name `docs/demos/<milestone>.md`; until it is approved the record names the walkthrough's run record under `docs/runs/` with the `demo` kind it already has (`Q-S0069-10`). The demo is evidence; it is never an approval, and no line in it stands for the owner's yes.
9. **Limits and settings.** `[demo] mode = "off" | "milestone"`, with the defaults of rule 4's table; `[demo] max_minutes` (a whole number, default 5) and `[demo] max_mb` (a whole number, default 50). Stories are grouped into several recordings so each stays within `max_minutes`, and the index lists what was grouped; a recording over `max_mb` is refused. Another value of a setting is refused naming the setting, never a value. `agk.toml` is protected, so a project's change to `[demo]` comes with its ADR.
10. **When it goes wrong.**
    - **The product cannot start** on the builder's machine (a missing container engine, a missing seed): one `Owner needed:` comment naming what is missing; no partial recording is attached.
    - **A step fails:** the brief ends with a fix list naming the story; the failing run's recording is kept beside the run record as evidence and is never attached as the demo.
    - **A flaky walkthrough:** one retry; a second failure is a fix list.
    - **A story changes after the demo:** when a later merge touches a path of a story in the demo, the stale check warns `demo stale: <milestone>` in the release brief where one exists and in the steward's sign-off question, and offers one re-record; it never blocks.
    - **The release:** a failing walkthrough blocks as the smoke run it is; a missing recording only warns (`Q-S0069-11`).
11. **By mode.** CI, local and personal as rule 6 says. Solo and team alike: the reviewer who signs the milestone off sees the link. No mode changes a workflow, the ruleset or a required check in this intake.
12. **What is reused, never rewritten.** The playbooks' smoke gates and the pilot's demo stage, the test map, the data guard, SPEC-0051's acceptance record, the milestones' `Demo:` lines and the steward's sign-off question.
13. **The builds, in order.** Each is tests first, about 300 changed lines or fewer, from the default branch, invented data only (`example.com`), no network in a check and a `[[testing.map]]` entry for each new script.
    - (a) The `demo` brief in `plan-intake` and its `depends_on` (rule 2), the plan warning, and the index format with its check (rule 7), in one new installed script, `scripts/agk/demo.py` (`Q-S0069-7`).
    - (b) The walkthrough template and the video form for products with browser screens, with captions, on seeded data (rules 3 to 5), and the refusal of video files in tracked paths (rule 6). `Depends-on` (a).
    - (c) Storage by mode (rule 6) and the stale warning (rule 10). `Depends-on` (b).
    - (d) The steward's sign-off line and the acceptance evidence, with the amendment of SPEC-0051 rule 4 (rule 8). `Depends-on` (a).
    - (e) The transcript form for products without screens and the run-record form for data pipelines, and the mobile form `(verify)` (rule 4). `Depends-on` (b).
14. **Measured goals.** Brief answer 5, on a sample web project with a three-story milestone and saved answers only: the plan shows one demo brief after the last story and before the release; the walkthrough passes and produces one recording within `max_minutes` and `max_mb`, with three captions, and an index that names the head; no video file is tracked; the steward's sign-off question carries the link; a recording made against anything but seeded data is refused.

## Tests

Saved GitHub answers, a stub browser tool and a fake clock only; no network; invented data only (`example.com`, accounts such as `demo-user@example.com`); each test carries the marker `REQ-076` with its criterion.

- Rule 2: a three-story milestone with screens gets one `demo` brief depending on its last story briefs, a `release` brief depends on it, a milestone with screens and no demo brief gives the warning and exit 0, and a foundation milestone needs none; REQ-076 AC1.
- Rule 3: the walkthrough template starts a stub product, signs in with the seeded account, shows one caption per story in order before its steps, and fails when a step fails; REQ-076 AC2.
- Rule 4: each playbook of the table gets its form, a milestone with no screens gets a transcript and no video file, and a playbook's own form wins; REQ-076 AC3.
- Rule 5: a base address outside the local hosts and `allowed_hosts` is refused before the first step, a caption with an invented secret-shaped value is refused naming the kind and not the text, and only the seed's test password is typed; REQ-076 AC4.
- Rule 6: a tracked `.mp4` or `.webm` is refused naming the path class, the local upload goes only to an existing release and never creates one, personal mode writes under `~/.agk/demos/` and posts nothing, and no check opens a socket; REQ-076 AC5.
- Rules 7 and 10: an index missing a field is refused naming it, a re-record replaces the index, and a merge touching a story's path gives `demo stale` in the release brief and the sign-off question without blocking; REQ-076 AC6.
- Rule 8: the steward's sign-off question carries the link in one line, the acceptance record takes the demo as a `demo` item, and no demo line counts as an approval; REQ-076 AC7.
- Rules 9 and 10: `mode = "off"` records nothing, the defaults follow the table, stories are grouped within `max_minutes`, a recording over `max_mb` is refused, a bad value is refused naming the setting, a product that cannot start gives one `Owner needed:` and no attached recording, and a second failure after one retry gives a fix list with the failing recording kept and not attached; REQ-076 AC8.

## Proof

REQ-076 AC1: *one demo brief per milestone, and a warning when it is missing.* Rule 2. REQ-076 AC2: *the walkthrough is a test.* Rule 3. REQ-076 AC3: *the form fits the product.* Rule 4. REQ-076 AC4: *sample data only.* Rule 5. REQ-076 AC5: *never committed, stored by mode.* Rule 6. REQ-076 AC6: *the index and the stale warning.* Rules 7 and 10. REQ-076 AC7: *shown at sign-off, never an approval.* Rule 8. REQ-076 AC8: *limits, settings and failures.* Rules 9 and 10.

## Residual

- 2026-11-16: the forms of rule 4 rest on the browser test tool's and the emulator's own recording, not yet read in their documentation `(verify)`; build (b) and build (e) confirm them or the form falls back to the transcript (due 2027-03-31).
- 2026-11-16: in local mode with no release yet, the recording stays on the builder's machine, so another reviewer cannot watch it until a release exists (due 2027-03-31).

## Contexts

- kit: the demo brief, the walkthrough template, the index and its check, the steward's line, installed in every project by builds (a) to (e).
- github: CI mode: the recording is a release asset or a run artifact, and no workflow change in this intake, each later one by its ADR.
- local: the builder uploads the asset to an existing release, and checks make no network call.
- personal: the recording stays under `~/.agk` on the machine, and nothing is posted.
- stacks: the walkthrough uses each stack's own test tool, and no stack's build step changes.

## Open questions

Each is a point the brief leaves open, or a name it cites that the code holds otherwise; the reading after it is the most conservative one, and the rules above apply it. `Q-S0069-1` to `Q-S0069-11` are ruled as read by the maintainer's answer on #1403 (comment 6907062287), one file each under `docs/runs/decisions/`, and the rules above hold their readings. No question is open.

- Q-S0069-1: the brief says "one brief of kind `demo`", but a plan brief has no `kind` field. Reading: the demo brief is the brief whose `key` is `demo` in its milestone, as the pilot playbook's `brief_order` names it, and no field is added to SPEC-0043's proposals (rule 2).
- Q-S0069-2: the brief names "the milestone's release brief", which the plan does not have. Reading: no release brief is added; where a plan carries a brief keyed `release` in the milestone it depends on the demo brief, and otherwise the stale warning goes to the steward's sign-off question (rules 2 and 10).
- Q-S0069-3: the brief says the walkthrough starts the product "as the project's test map starts it", but the test map holds no start command. Reading: it starts the product as the project's end-to-end tests do, with the stack's own test tool, and the map only maps the demo test (rule 3).
- Q-S0069-4: which playbooks have screens? Reading: `web-app`, `mobile` and `pilot` (its demo surface), and any project whose plan's milestones carry `screens`; the others default to `off` (rule 4).
- Q-S0069-5: is a spoken narration added? Reading: no, captions only (brief answer 6; rule 4).
- Q-S0069-6: how is "never against a real environment" told? Reading: by the base address: only a local host or a host of `[guard] allowed_hosts`, refused before the first step (rule 5).
- Q-S0069-7: the brief names no script and no check for the index or the video refusal. Reading: one new installed `scripts/agk/demo.py` holds the index check, the video refusal (run by `make governance`) and the stale check (rules 6, 7 and 13).
- Q-S0069-8: in local mode, may the builder create the release it uploads to? Reading: no; session rule 2 forbids tags, so it uploads only to an existing release and otherwise keeps the file on the machine (rule 6).
- Q-S0069-9: are recordings kept for every release or only the latest? Reading: one per milestone, replaced on re-record (brief answer 6; rule 7).
- Q-S0069-10: SPEC-0051's `demo` item names only a file under `docs/runs/`. Reading: build (d) proposes an amendment so it may name `docs/demos/<milestone>.md`; until then the record names the walkthrough's run record (rule 8).
- Q-S0069-11: may the demo block a release? Reading: a failing walkthrough blocks as the smoke run it is; a missing recording only warns (brief answer 6; rule 10).
