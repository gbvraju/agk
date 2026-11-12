# ADR-0477: The kit ships the round-the-clock task texts as templates

- Status: Proposed
- Date: 2026-11-12
- Deciders: maintainers
- Related: SPEC-0045, brief #1117, plan #661
- Requirements: REQ-039

## Context

A project can run AGK without a person at the keyboard only with a launcher, a conductor and builders started by its
own runtime, and `docs/guides/getting-started.md` ("Running the loop", item 7) says the kit ships no launcher. The rules
that keep such a run safe (a builder keeps its pull request until it closes, the hand-over line, never writing the
merger's record line, the maintainers' questions, the tests that fail only in CI, the launcher's capacity, kind-to-tier
routing and the restart of handed-over and silent pull requests) were written only in one person's scheduled tasks, so a
new project had to rediscover them. The guide also says a builder waits in the background, which is right for an
interactive session and wrong for a cloud scheduled task, which ends when its session goes idle (brief #1117).

## Decision

1. `kit/templates/runtime/` holds four plain-text templates and no code: `launcher.txt`, `conductor.txt`, `builder.txt`
   (one text for the strongest and mid builder tasks, by its `Tier:` line) and `README.md`. They name no repository,
   person or date; `<owner>/<repo>` and `<default branch>` are placeholders, and every rule of the source texts is kept.
2. `conductor.txt` templates only what `.claude/agents/conductor.md` and the guide's conductor loop already say, with a
   `<long-run rules>` placeholder for the long-run additions the maintainers will post.
3. The kit installs and starts none of them: they are not in `kit/manifest.json`, `doctor.py` gains no check, and the
   guide's rule that a launcher is the team's own stands. The guide gains `Running around the clock` under item 7: the
   four roles, the laptop path (the conductor loop and `/agk:launch`, the only path in personal mode) and the cloud path
   (one scheduled task per template, a launcher every 30 minutes, a conductor every 12 hours), what the person still
   does, and which way a builder waits: background in an interactive session, foreground in a cloud scheduled task.

## Consequences

A new project starts its AI workforce from the same texts and the same rules, on a laptop or in the cloud, and the guide
no longer contradicts the foreground wait of a cloud task. `tests/kit/test_runtime_templates.py` checks that the files
exist, are generic, carry the builder's rules by their first words, stay out of the manifest and are named by the guide.
Protected path classes changed: `kit/` (the templates) and `tests/kit/` (their test). No workflow, script or installed
file changes.

## Residual

- 2026-11-12: the `<long-run rules>` placeholder of `conductor.txt` waits for the maintainers' long-run additions (due
  2026-11-30).
- 2026-11-12: the texts are copies of the rules of `config/session-rules.md` and the role files; nothing checks that a
  later rule change reaches them beyond the first words test (due 2026-12-31).
- 2026-11-12: `Q-1117-1`, whether the templates should also be installed into a project (the `templates` maps of
  `kit/manifest.json`), is the maintainers' to rule; until then they stay kit-side, by answer 3 (due 2026-11-30).
