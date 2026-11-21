# ADR-0664: Day zero: the steward talks the idea through before a repository exists

- Status: Proposed
- Date: 2026-11-21
- Deciders: maintainers
- Related: brief #1584, SPEC-0066 rules 4 and 8, SPEC-0065 rule 8, SPEC-0043 rule 1, SPEC-0062 rules 3, 4 and 10, ADR-0663, amendments 196 and 197, Q-1584-1, Q-1584-2, Q-1584-3
- Requirements: REQ-072, REQ-069

## Context

In an empty folder the steward greets the person (SPEC-0066 rule 8), but choice A, "start a new product", needs a
repository: `skills/start` and `skills/vision` read `agk.toml`, and nothing in the kit prints `gh repo create`. The only
route is a repository made on the GitHub website and cloned (`docs/guides/getting-started.md` step 1). SPEC-0062 rule 3
makes the conversation the first step, so the person's first answers have nowhere to go, and a chat can end before the
repository exists.

## Decision

1. **Talk first** (brief answer 1). After choice A in an empty folder the steward asks the discovery topics of `engines.py
   questions` and the five of the default playbook's `[[discovery]]`, only those the idea leaves open, at most three per
   round, in plain words, and plays back what it understood. The steps are in `docs/guides/steward-first-run.md`, section
   `Day zero`, not in the role file, whose word budget is full.
2. **Keep the answers, on a yes** (answer 2, the recommendation of Q-1584-1). One plain question first. On a yes, the new
   `scripts/agk/day_zero.py keep --yes` writes each answer, quoted as given, with its UTC time and an optional `--who`
   (team mode, SPEC-0062 rule 15), to `agk-day-zero/<hash>.json` in the person's own Claude folder, where `<hash>` is
   rule 8's folder hash (`steward.folder_key`, the hash the greeting mark already holds, now one shared function).
   Without `--yes` it refuses, naming the setting, and writes nothing. Nothing is written to the opened folder. This is
   a second named exception to SPEC-0066 rule 4 (amendment 197).
3. **Connect GitHub** (answer 3, the recommendation of Q-1584-3). `day_zero.py offer` prints `offer: github` for a folder
   that is not a git repository with an `origin` remote and not a personal-mode project (a `[personal]` table), else
   `offer: none`. On the person's yes, `day_zero.py commands --name <name> --step <n>` prints one of seven commands, in
   order: `gh auth status`, `git init -b main`, a one-line README, the first commit, `gh repo create <name> --private
   --source . --remote origin --push`, `git remote set-head origin --auto` and `gh repo edit --enable-issues`
   `(verify: these gh flags on the person's gh version)`. The person runs each one; the steward asks for the next step
   only after the person's run exited 0, and never runs them (SPEC-0066 rule 4). `--shell powershell` (the default on
   Windows) writes the README with `Set-Content -Encoding utf8`, never `echo >`; `posix` serves WSL, macOS and Linux. A
   name outside letters, digits, `.`, `_` and `-` is refused, naming `--name`. Then `/agk:setup` goes on from SPEC-0065
   rule 8's "the clone has no `agk.toml`" step (amendment 196).
4. **The answers become the first source** (answer 4, the recommendation of Q-1584-2). After the install,
   `day_zero.py write --root <project>` writes `docs/sources/day-zero.md` with SPEC-0043 rule 1's header (`Source:
   Day-zero conversation`, `Kind: other`, `Version: 1`, `Date:` from UTC) and each answer quoted line by line under its
   topic, never rewritten. With `--answers FILE` it also writes the `vision` skill's answers file (the format of
   `front_door.py discovery-write`) for the topics that file knows. It never overwrites an existing source, and it then
   removes the kept file. The file goes in the person's pull request, approved as any.
5. **Settings.** No new `agk.toml` setting. `[engines] vision`, `review_mode`, `execution` and `pr_mode` are unchanged;
   the source pull request is an ordinary one in strict and flow mode. Personal mode gets no offer, and `write --root`
   names the sidecar. An adopted repository gets no day-zero file; `steward.py onboard` harvests as today.

Protected path classes changed: `scripts/agk/` (`day_zero.py`, new; `steward.py`, the shared `folder_key`),
`tests/kit/` (`test_day_zero.py`, new), `skills/` (`skills/vision/SKILL.md`, the answers file), `kit/`
(`kit/manifest.json`, the new script), `agk.toml` (its `[[testing.map]]` entry) and `docs/adr/` (this file).

## Consequences

A person with only an idea and an empty folder can talk it through first, keep their answers, and create the repository
with seven printed commands. Their words become the plan's first source, which `plan-intake` and the charter read.

## Residual

- 2026-11-21 (verify): the `gh repo create` and `gh repo edit --enable-issues` flags on the person's `gh` version, and
  that Windows PowerShell 5's `-Encoding utf8` writes a byte-order mark the README tolerates (due 2027-01-31).
- 2026-11-21: amendments 196 and 197 are proposed for the owner's approval and are not applied by this build.
