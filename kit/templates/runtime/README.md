# Round-the-clock task texts

The texts of the tasks that run AGK without a person at the keyboard, for a project to set up in its own runtime
(ADR-0477). The kit installs none of them and starts nothing: a person copies each text into a scheduled task of the
runtime, replaces `<owner>/<repo>` and `<default branch>`, and keeps every rule. `docs/guides/getting-started.md`,
"Running the loop", item 7, section "Running around the clock", says how, on a laptop or in the cloud.

| File | Task | Runs | Tier |
| --- | --- | --- | --- |
| `launcher.txt` | the supervisor in CI mode (SPEC-0064 rule 13): runs `autopilot.py jobs --claim` and starts one short cloud session per review, build or fix job; restarts a builder whose pull request was handed over or went silent | every 30 minutes | mid |
| `conductor.txt` | the conductor role of `.claude/agents/conductor.md` for one review job, holding the `conductor-long` lease | fired by the launcher | strongest |
| `builder.txt` | one builder per brief, as one short job per step until its pull request closes; one text for two tasks, by its `Tier:` line | fired by the launcher | strongest for `design` and `build`; mid for `small` and `mechanical` |

The launcher fires the two builder tasks and the conductor task and nothing else; the conductor fires none. A builder started by either gets its item in
a second message (`Session name: ... Item: brief #<n> ... Reserved: ...`); with no such message it stops.

The launcher is the supervisor in CI mode (brief #1391): the script picks the jobs by the rules a machine's
`conductor.py watchdog --pass` uses and posts each claim, so every mode starts the same jobs; every job ends at its
`Report:`, `Verdict:` or `Question:`, and the launcher stays the backup for a builder silent for 45 minutes.
