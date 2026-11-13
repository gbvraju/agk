# Round-the-clock task texts

The texts of the tasks that run AGK without a person at the keyboard, for a project to set up in its own runtime
(ADR-0477). The kit installs none of them and starts nothing: a person copies each text into a scheduled task of the
runtime, replaces `<owner>/<repo>` and `<default branch>`, and keeps every rule. `docs/guides/getting-started.md`,
"Running the loop", item 7, section "Running around the clock", says how, on a laptop or in the cloud.

| File | Task | Runs | Tier |
| --- | --- | --- | --- |
| `launcher.txt` | keeps one conductor alive, starts one builder per brief the plan offers, restarts a builder whose pull request was handed over or went silent | every 30 minutes | mid |
| `conductor.txt` | the conductor role of `.claude/agents/conductor.md` on a long run, holding the `conductor-long` lease | every 12 hours | strongest |
| `builder.txt` | one builder per brief, kept until its pull request closes; one text for two tasks, by its `Tier:` line | fired by the conductor, or the launcher as its backup | strongest for `design` and `build`; mid for `small` and `mechanical` |

The launcher fires the two builder tasks and the conductor task and nothing else; the conductor fires only the two builder tasks. A builder started by either gets its item in
a second message (`Session name: ... Item: brief #<n> ... Reserved: ...`); with no such message it stops.

The conductor text starts builders itself, in real time, on every `START` line of its watch and after every merge and
verdict, and restarts handed-over and silent ones; the launcher is its backup, at 45 minutes of silence (brief #1202).
