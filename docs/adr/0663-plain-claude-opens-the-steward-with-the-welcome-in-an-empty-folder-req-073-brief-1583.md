# ADR-0663: Plain claude opens the steward, with the welcome in an empty folder

- Status: Proposed
- Date: 2026-11-20
- Deciders: maintainers
- Related: brief #1583, SPEC-0066 rules 2, 3, 4, 8 and 11 (build (d)), Q-S0066-1, Q-S0066-2, Q-S0066-3, Q-S0066-8, ADR-0662, plan #661
- Requirements: REQ-073

## Context

Build (a) (brief #1582, ADR-0662) made every kit start name its agent, so a project can now take the steward as its
default agent without a builder, conductor or reviewer starting as the steward. Today `.claude/settings.json` is a
`verbatim` file, the same bytes in the kit and in every project, with no `agent`; the plugin ships no `settings.json`;
the role file has no first run; and each steward script calls `repo_root()` outside its handler, so in a folder that is
not a git repository the person sees a traceback.

## Decision

1. **The project's agent line** (rule 2, Q-S0066-1). The kit's own `.claude/settings.json` carries no `agent`.
   `init` and `adopt` write `"agent": "steward"` into the project's copy after the copy step, as one line right after
   the opening brace (`common.with_agent`). `kit/manifest.json` gains `project_keys` (`.claude/settings.json`:
   `agent`), and `common.without_agent` takes that one line away before the copy is compared with the kit's: in
   `doctor.py`'s drift check, `upgrade.py`'s plan and `uninstall.py`'s kit-copy test. Any other change of the file
   still reads as a project change. The kit file's bytes and their hashes do not change.
2. **The upgrade** (rules 2 and 11). `upgrade.settings_file` writes the kit's settings with the project's own `agent`
   line kept, or `steward` when it has none; another value is kept and named in one line, `agent kept: <name>;
   setting: agent`, never overwritten. While an adapter that the upgrade leaves in place (`scripts/start-session-*`,
   a template written only where absent) or a script that `[flow] launch_adapter` names starts `claude` without
   `--agent`, the upgrade writes no `agent` line that the file did not hold and prints one note naming `[flow]
   launch_adapter`, never the command; the rest of the upgrade proceeds. `common.starts_unnamed` is the one test of
   an adapter's text, shared with `doctor.py`'s warning of ADR-0662.
3. **The plugin's default agent** (rule 4, Q-S0066-2). `.claude-plugin/settings.json` holds `{"agent": "agk:steward"}`
   `(verify: the file's place in the plugin, the namespaced name and that the key applies to every session while the
   plugin is enabled)`. The plugin-level steward is `.claude/agents/steward.md` itself, already listed in
   `plugin.json`'s `agents` (ADR-0612), so there is one text and no copy to keep equal.
4. **No traceback outside a project** (rule 8). `steward.py`, `steward_daily.py`, `steward_evidence.py`,
   `steward_onboard.py` and `steward_owner.py` call `repo_root()` inside a handler: outside a git repository each
   prints `outside: no project here` (`common.OUTSIDE_PROJECT`) on stdout, exit 3 (nothing to do, not a refusal), and
   writes nothing.
5. **The first run** (rule 8, Q-S0066-3, Q-S0066-8). `steward.py first-run [--folder DIR]` prints `first-run: <step>`:
   `kit` (the kit's own repository), `project` (a repository with `agk.toml`), `adopt` (another repository), `greet`
   or `greeted`. Only `greet` writes: one line, the SHA-256 of the folder's resolved path (case folded on Windows and
   macOS) and the date, in `agk-greeted.txt` of the person's Claude folder (`CLAUDE_CONFIG_DIR`, else `~/.claude`,
   `(verify: the Claude folder per platform)`), never in the opened folder. The role file names, in one line, the plugin's copy of
   `docs/guides/steward-first-run.md` (a new verbatim guide, by the maintainers' answer on #1612 that keeps the role
   file's word budget), which reads `outside: no project here` and runs that command from the plugin's scripts
   folder, gives rule 8's three-line
   welcome for `greet`, the choice alone for `greeted`, the adopt offer, the kit's case or the project's state, and
   outside a project only reads and offers named skills on the person's yes.
6. **Split** (the brief's plan). Rule 3's default-branch check and its `SessionStart` hook are the brief's second pull
   request, from the default branch after this one merges, to keep each under about 300 changed lines.
7. **The default-branch check** (rule 3, the second pull request, Q-1583-3). `common.branch_check` reads where the
   steward was opened and changes nothing but, on a fetch, the remote-tracking branch. In the main folder, after one
   `git fetch origin <default branch>`, on the default branch and not behind `origin` it returns nothing; off it, or
   behind, one line `branch: <where>; fix: git switch <default branch> && git pull --ff-only`, and with uncommitted
   changes it names their count and asks to keep them or set them aside first. In a linked worktree it names the
   owner from an `agk-<session>` folder (else `another session`) and asks for the main folder; the steward's own
   `agk-steward` worktree goes on. Outside git or with no `origin` there is nothing to check. `steward.py start`
   runs it first and stops, exit 1, before any write; `steward.py branch` runs it again when the person asks the
   steward to act (`branch: ok`, else the line, exit 1). The role file names, in one line, the guide's new section,
   which runs the fix only on the person's yes and with no uncommitted change.
8. **The start hook** (rule 3). `.claude/hooks/branch_check.py`, a new verbatim hook, prints the same line on
   standard output with no fetch, and nothing on the default branch; it always exits 0 and gives no line to a kit
   start whose `AGK_AGENT` names another role. `common.with_agent`, the one writer of rule 2's agent line, also
   writes its `SessionStart` entry as the first entry of `hooks` in the project's copy, and `common.without_agent`
   takes it away with the agent line, so the kit's own copy holds neither and the manifest's `project_keys` names
   both (`agent`, `hooks.SessionStart`).

Protected path classes changed: `scripts/agk/` (`common.py`, `init.py`, `adopt.py`, `upgrade.py`, `doctor.py`,
`uninstall.py`, `steward.py`, `steward_daily.py`, `steward_evidence.py`, `steward_onboard.py`, `steward_owner.py`),
`kit/` (`kit/manifest.json`, which also lists the new guide, and the `gitattributes` template, which pins it LF), `.claude/` (`.claude/agents/steward.md`, one line),
`.claude-plugin/` (`settings.json`), `config/` (the steward's line in `config/rule-budget.txt`, 943 to 966 words) and, in the second pull request, 966 to 972 words, `tests/kit/` (`test_first_open.py`), `tests/kit_dev/`
(`test_init.py`, `test_upgrade.py`, `test_kit_manifest.py`, `test_distribution.py`, which now read the project's agent
line as the kit's) and `docs/adr/` (this file). The second pull request changes `scripts/agk/` (`common.py`, `steward.py`), `.claude/`
(`.claude/hooks/branch_check.py`, new, and `.claude/agents/steward.md`, one line), `kit/` (`kit/manifest.json` and the
`gitattributes` template, which pins the hook LF), `config/` (`config/rule-budget.txt`), `agk.toml` (the hook's test
map entry), `tests/kit/` (`test_first_open.py`) and `docs/adr/` (this file).

## Consequences

A project installed or upgraded by this release opens the steward on plain `claude`, with or without the plugin. A
project whose kept adapters predate ADR-0662 gets no `agent` until its adapters pass `--agent`, and is told so in one
line. A person who wants plain Claude sets their own `agent` in `.claude/settings.local.json` `(verify: the local
file overrides the project file for agent)`; `/agk:help` (build (e)) will say how. Rule 11 holds this build to a
release after build (a)'s.

## Residual

- 2026-11-21 (verify): that a `SessionStart` hook's standard output is shown to the person at session start, and that
  a kit start's `AGK_AGENT` reaches the hook's environment, are read from a recorded run (due 2027-01-31).

- 2026-11-20 (verify): the plugin's `settings.json` place and `agent` key, the namespaced name `agk:steward`, the
  precedence of a project setting over a plugin's default, the Claude folder per platform and how a plugin agent names
  its plugin's folder are read from a recorded run before this build lands (due 2027-01-31).
- 2026-11-20: outside an AGK project the steward's guard hook (`$CLAUDE_PROJECT_DIR/.claude/hooks/steward_guard.py`)
  is absent, so the plugin-level steward relies on its role text to read and offer only until SPEC-0071's plugin
  hooks are confirmed (due 2027-03-31).
- 2026-11-20: the clean layout (SPEC-0071) installs no `.claude/settings.json`; its steward comes from the plugin's
  default agent alone.
