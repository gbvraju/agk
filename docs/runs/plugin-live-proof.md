# Plugin live proof (criterion a of ADR-0015, SPEC-0005 rule 18)

Date: 2026-10-16 (from `date -u`). Run by the implementation agent in a cloud container (Claude Code 2.1.301), on the
maintainers' instruction, with the plugin installed from GitHub: release `v0.10.0`, commit `3a3686f`. Repository settings
were never changed. Outputs below are verbatim; session ids and temporary paths are as printed.

## Result

| Step | Result |
| --- | --- |
| 1 `v0.10.0` points at `3a3686f` | yes (a second tag `V0.10.0`, same commit, was still listed) |
| 2 marketplace add, install, list, details | done; installed version `0.10.0`; 8 skills; 0 agents, hooks, MCP and LSP servers |
| 3 attach `gbvraju/agk-plugin-proof` with push access | attached; the push check said **refused** |
| 4 `/agk:init` through Claude Code, no hand-copied file | done: 294 files; 283 of 283 verbatim files identical to the plugin cache copy |
| 5 `make governance` locally | all steps ok (the base-dependent checks skip outside CI) |
| 5 first commit pushed to `main` | **not done: `git push` was refused with HTTP 403** (the Claude GitHub App has no access to the repository). Local commit `124d92c`, not on GitHub |
| 5 `governance` green on GitHub for that push | **not done**: no push, so no run |
| Q-K3-72 tag pin | works with the CLI and with a user-scope settings entry; the project-scope committed form is not testable headless (below) |

Criterion a is therefore **not met yet**. The one missing piece is the first push to `gbvraju/agk-plugin-proof` and its
green `governance` run. The container needs the Claude GitHub App on that repository, or the maintainers push the
commit; nothing was worked around.

## Step 1: the tag

```
$ git ls-remote --tags https://github.com/gbvraju/agk
3a3686f0abce67a50e3f4d5b9e257825790f770a	refs/tags/V0.10.0
3a3686f0abce67a50e3f4d5b9e257825790f770a	refs/tags/v0.10.0
```

`v0.10.0` points at `3a3686f`, as briefed. The tag `V0.10.0` (capital V) was still listed at this check although the
maintainers reported it deleted. The marketplace clone below reports both tags on `3a3686f`.

## Step 2: add the marketplace, install, list, details

```
$ claude plugin marketplace add gbvraju/agk
Adding marketplace…Cloning via HTTPS: https://github.com/gbvraju/agk.git
Refreshing marketplace cache (timeout: 120s)…
Cloning repository (timeout: 120s): https://github.com/gbvraju/agk.git
Clone complete, validating marketplace…
Cleaning up old marketplace cache…
√ Successfully added marketplace: agk (declared in user settings)
exit 0

$ claude plugin install agk@agk
Installing plugin "agk@agk"...√ Successfully installed plugin: agk@agk (scope: user)
exit 0

$ claude plugin list
Installed plugins:

  > agk@agk
    Version: 0.10.0
    Scope: user
    Status: √ enabled

Synced from claude.ai:

  > cowork-plugin-management@synced
    Version: 0.2.2
    Path: /root/.claude/plugins/synced/d026a7c9-8ea3-4ad8-a9ed-15bafecc55b6_e3430248-467e-4a02-afd9-998e8e910983/cowork-plugin-management
    Status: √ loaded

exit 0

$ claude plugin details agk
agk 0.10.0
  Description: Workflow commands for repositories governed by agk.
  Source: agk@agk

Component inventory
  Skills (8)  adopt, brief, doctor, init, issue, review, spec, upgrade
  Agents (0)
  Hooks (0)
  MCP servers (0)
  LSP servers (0)

Projected token cost
  Always-on:   ~356 tok   added to every session

Per-component (rounded)
  component  always-on  on-invoke
  doctor           ~40       ~370
  spec             ~50       ~440
  review           ~50       ~420
  init             ~40       ~310
  brief            ~30       ~130
  adopt            ~40       ~290
  upgrade          ~50       ~310
  issue            ~50       ~280

  On-invoke cost is paid each time a skill or agent fires.
  Token counts are estimates and may differ from actual usage.
exit 0
```

Installed record (`~/.claude/plugins/installed_plugins.json`), the cache the plugin runs from:

```
{
  "version": 2,
  "plugins": {
    "agk@agk": [
      {
        "scope": "user",
        "installPath": "/root/.claude/plugins/cache/agk/agk/0.10.0",
        "version": "0.10.0",
        "installedAt": "2026-10-16T10:44:15.659Z",
        "lastUpdated": "2026-10-16T10:44:15.659Z",
        "gitCommitSha": "3a3686f0abce67a50e3f4d5b9e257825790f770a"
      }
    ]
  }
}
```

Installed version: **0.10.0** (required: 0.10.0). Skills: **8** (`adopt`, `brief`, `doctor`, `init`, `issue`, `review`,
`spec`, `upgrade`); no agents, hooks, MCP servers or LSP servers. Installed from commit
`3a3686f0abce67a50e3f4d5b9e257825790f770a`.

## Step 3: the proof repository

`gbvraju/agk-plugin-proof` was attached with `add_repo` (access `push`). The attach result carried `push_check: refused`
and this text: "Claude doesn't have GitHub access to gbvraju/agk-plugin-proof for your organization. An org admin can
install the Claude GitHub App at https://github.com/apps/claude/installations/select_target ...". The clone
(`git clone https://github.com/gbvraju/agk-plugin-proof`) printed "warning: You appear to have cloned an empty repository."

## Step 4: `/agk:init` through Claude Code

Each run is `claude -p` in the empty clone. The nested Claude Code inherited this conversation's session id from the
environment at first (run 1); the later runs unset `CLAUDE_CODE_SESSION_ID` and pass their own `--session-id`
(`19b511b5-77cd-4808-b8b3-581c3a6993c5`).

### Run 1: no flags (the inherited session id)

Command: `claude -p "/agk:init" --output-format json`

Permission denials reported by Claude Code: `[{"tool_name": "Bash", "tool_use_id": "toolu_011cignPzmC7y7y7DP7BuL2T", "tool_input": {"command": "python3 \"/root/.claude/plugins/cache/agk/agk/0.10.0/scripts/agk/init.py\" . --dry-run", "description": "Preview kit installation (dry run)"}}]`

Result text, verbatim:

```
The dry-run command needs your approval before it can run, and I can't preview the install without it. The command was:

```
python3 "/root/.claude/plugins/cache/agk/agk/0.10.0/scripts/agk/init.py" . --dry-run
```

If you approve it, I'll run it and show you the output. I'll only do the real install after you agree to what the preview shows.
```

### Run 2: no flags, own session

Command: `claude -p "/agk:init" --session-id 19b511b5-77cd-4808-b8b3-581c3a6993c5 --output-format json`

Permission denials reported by Claude Code: `[{"tool_name": "Bash", "tool_use_id": "toolu_01WL9waf23KAYDn9AxAMh3g7", "tool_input": {"command": "python3 \"/root/.claude/plugins/cache/agk/agk/0.10.0/scripts/agk/init.py\" . --dry-run", "description": "Preview kit installation (dry run)"}}]`

Result text, verbatim:

```
The dry-run command needs your approval before it can run, and I haven't run it. It previews the kit installation in `/home/user/agk-plugin-proof` and writes nothing.

The command is:

```
python3 "/root/.claude/plugins/cache/agk/agk/0.10.0/scripts/agk/init.py" . --dry-run
```

Once you approve it, I'll show you the output. I'll run the real install only after you agree to it.
```

### Run 3: answer "yes" in the continued session, no flags

Command: `claude -p "yes" --resume 19b511b5-77cd-4808-b8b3-581c3a6993c5 --output-format json`

Permission denials reported by Claude Code: `[{"tool_name": "Bash", "tool_use_id": "toolu_01FsdEuqsVMSNXZ28kbLEjHU", "tool_input": {"command": "python3 \"/root/.claude/plugins/cache/agk/agk/0.10.0/scripts/agk/init.py\" . --dry-run", "description": "Preview kit installation (dry run)"}}]`

Result text, verbatim:

```
The dry run was blocked again, so I still haven't run it. Your "yes" in chat didn't clear it, because the approval has to come through the tool-permission prompt.

You could approve the prompt when it appears. Or you could run the command yourself in the terminal and paste the output here:

```
python3 "/root/.claude/plugins/cache/agk/agk/0.10.0/scripts/agk/init.py" . --dry-run
```

If the prompt never shows up, your permission mode may be set to deny this command. In that case, adding an allow rule for it in your settings should fix it.
```

### Run 4: continued session, first allow rule

Command: `claude -p "yes" --resume 19b511b5-77cd-4808-b8b3-581c3a6993c5 --allowedTools 'Bash(python3 *scripts/agk/init.py *)' --output-format json` (the skill quotes the script path, so this rule did not match)

Permission denials reported by Claude Code: `[{"tool_name": "Bash", "tool_use_id": "toolu_019xETpBM2NWWdHzHAAvGGwZ", "tool_input": {"command": "python3 \"/root/.claude/plugins/cache/agk/agk/0.10.0/scripts/agk/init.py\" . --dry-run", "description": "Preview kit installation (dry run)"}}]`

Result text, verbatim:

```
The dry run is blocked a third time. Each attempt returned "This command requires approval", and nothing has run. The tool-permission prompt isn't reaching you, and your "yes" in chat doesn't count as approval.

Here are two ways to get past it:

1. **Run it yourself.** Run this in the repo and paste the output here:
   ```
   python3 "/root/.claude/plugins/cache/agk/agk/0.10.0/scripts/agk/init.py" . --dry-run
   ```
2. **Add an allow rule.** I can add a permission rule for this script to `.claude/settings.json` through the `update-config` skill. That would be a change to your settings, so I won't do it unless you ask.

I'm not going to retry the same command again. Tell me which option you want.
```

### Run 5: continued session, matching allow rule: the dry run

Command: `claude -p "yes" --resume 19b511b5-77cd-4808-b8b3-581c3a6993c5 --allowedTools 'Bash(python3 *scripts/agk/init.py* *)' --output-format json`

Permission denials reported by Claude Code: `[]`

Result text, verbatim:

```
The dry run worked. The installer would create 294 files and write nothing else. I haven't installed anything yet.

**What it would create**
- **Agents and hooks:** `.claude/agents/` (`drift-auditor.md`, `reviewer.md`), `.claude/hooks/stop_check.py` and `.claude/settings.json`.
- **GitHub files:** `CODEOWNERS`, three issue templates, a PR template, and three workflows (`drift-audit`, `governance`, `metrics`).
- **Governance docs:** `constitution/`, `docs/adr/` (including `0001-adopt-agk.md`), `docs/specs`, `docs/briefs`, `docs/requirements.md`, `docs/build-state.md` and the run log.
- **Config and root files:** `agk.toml`, `agk.mk`, `Makefile`, `pyproject.toml`, `CLAUDE.md`, `.gitignore` and `config/` (neutrality, protected paths, reviewers).
- **Checker scripts:** about 17 scripts in `scripts/agk/`, including `doctor.py`, `drift_audit.py` and `metrics.py`.
- **Kit tests and fixtures:** `tests/kit/`, which is most of the 294 files.

**Notices from the installer**
- **Placeholder reviewer:** `config/reviewers.yaml` maps `maintainers` to the placeholder `@REPLACE-ME`. `.github/CODEOWNERS` also has a placeholder, since `doctor` has a fixture for it.
- **Workflow permissions:** `drift-audit.yml` and `metrics.yml` can write GitHub issues with the workflow token (`issues: write`). Delete either file if you don't want that.
- **Unverified plugin `ref`:** the plugin settings entry below uses a `ref` field on a `github` source. The installer says the docs don't list it for `extraKnownMarketplaces`, so verify it before relying on it.

**Manual steps (the installer configures none of them)**
- **Branch ruleset on `main`:**
  - Active, with no bypass.
  - Targets the default branch.
  - Restricts deletions.
  - Requires linear history.
  - Requires a pull request: 0 approvals, dismiss stale approvals, squash merge only.
  - Blocks force pushes.
  - Requires the status check `governance`.
- **Repository settings:** allow auto-merge, and auto-delete head branches.
- **Scanner exclusions:** if you run bandit, flake8, pylint or mypy over the whole tree, exclude `scripts/agk`, `tests/kit` and `.claude/hooks`. The installer prints the exact flags for each tool.
- **Plugin settings:** to let a team enable the plugin, add these two keys to `.claude/settings.json`. That is a protected path, so the change needs an ADR.
  ```
  "extraKnownMarketplaces": {"agk": {"source": {"source": "github", "repo": "gbvraju/agk", "ref": "v0.10.0"}}}
  "enabledPlugins": {"agk@agk": true}
  ```

I'll run the real install, which writes the 294 files, only if you tell me to. I won't commit, push or merge, and I won't set any spec to `Approved` or any ADR to `Accepted`.

Do you want me to run the install?
```

### Run 6: "yes, run the install": the real run

Command: `claude -p "yes, run the install" --resume 19b511b5-77cd-4808-b8b3-581c3a6993c5 --allowedTools 'Bash(python3 *scripts/agk/init.py* *)' --output-format json`

Permission denials reported by Claude Code: `[]`

Result text, verbatim:

```
The install finished. It created 294 files in `/home/user/agk-plugin-proof`, as the dry run said it would. I haven't committed, pushed or merged anything, and I haven't set any spec to `Approved` or any ADR to `Accepted`. I also haven't applied any of the settings below.

**Placeholder reviewer.** `config/reviewers.yaml` maps `maintainers` to the placeholder `@REPLACE-ME`. Replace it with real handles. The `.github/CODEOWNERS` it created has a placeholder too.

**Branch ruleset.** Set this up by hand on GitHub for `main`:
- Active, with no bypass.
- Targets the default branch.
- Restricts deletions.
- Requires linear history.
- Requires a pull request: 0 approvals, dismiss stale approvals, squash merge only.
- Blocks force pushes.
- Requires the status check `governance`.

**Repository settings.** Allow auto-merge, and auto-delete head branches.

**Scanner exclusions.** If you run bandit, flake8, pylint or mypy over the whole tree, exclude `scripts/agk`, `tests/kit` and `.claude/hooks`. The flags:
- **bandit:** `bandit -r . -x ./scripts/agk,./tests/kit,./.claude/hooks`
- **flake8:** `flake8 --extend-exclude scripts/agk,tests/kit,.claude/hooks`
- **pylint:** `[tool.pylint.main] ignore-paths = ['^scripts/agk/.*$', '^tests/kit/.*$']` and `ignore = ['.claude']`
- **mypy:** `[tool.mypy] exclude = ['^scripts/agk/', '^tests/kit/', '^\.claude/hooks/']`

**Plugin settings.** To let a team enable the plugin, add these two keys to `.claude/settings.json`. That is a protected path, so the change needs an ADR. Each collaborator also has to trust the folder and install the plugin on their own machine. A cloud session doesn't load it.
```
"extraKnownMarketplaces": {"agk": {"source": {"source": "github", "repo": "gbvraju/agk", "ref": "v0.10.0"}}}
"enabledPlugins": {"agk@agk": true}
```
The installer says the docs don't list the `ref` field for `extraKnownMarketplaces`, so verify it first.

**Workflow permissions.** `drift-audit.yml` and `metrics.yml` can write GitHub issues with the workflow token (`issues: write`). Delete either file if the repository must not allow that.
```


### Approval-friction evidence (Q-K3-73)

- Headless, with no flag, the first command the skill runs (`init.py . --dry-run`) is **denied**, three times (runs 1 to 3).
  Answering "yes" in a continued session does not clear it: Claude Code said the approval "has to come through the
  tool-permission prompt".
- It ran only with a command-line allow rule for the plugin's own script,
  `--allowedTools 'Bash(python3 *scripts/agk/init.py* *)'` (the first, narrower pattern in run 4 did not match because the
  skill quotes the path). That one flag was needed, for the dry run and the real run alike.
- With the flag: no further prompt and no denial in runs 5 and 6. The skill asked once for agreement between the dry run
  and the real run, as written.
- In an interactive session the same denial would be a prompt, once per command. No `allowed-tools` was set (Q-K3-73 ruled).

### Nothing copied by hand

The tree was created by the plugin's `init.py`, run from the cache path `/root/.claude/plugins/cache/agk/agk/0.10.0`.

```
find . -path ./.git -prune -o -type f -print | wc -l     (includes generated __pycache__)
295
verbatim files 283, differing from the cache copy: 0
git ls-files | wc -l
294
```

## Step 5: governance and the first commit

`make governance` in the clone, before the commit:

```
python3 scripts/agk/check_protected_changes.py
protected-changes: no base ref available outside CI; skipped
python3 scripts/agk/check_requirements.py
ok requirements (3 requirements)
python3 scripts/agk/check_adrs.py
adrs: no base ref available outside CI; immutability check skipped
ok adrs (1 ADRs)
python3 scripts/agk/check_specs.py
specs: no base ref available outside CI; skipped
python3 scripts/agk/check_neutrality.py
ok neutrality (0 tokens)
python3 scripts/agk/check_build_state.py
build-state: no base ref available outside CI; skipped
python3 scripts/agk/check_kit_tests.py
ok kit-tests (no kit/manifest.json here; nothing to check)
python3 scripts/agk/reviewers.py --check
ok reviewers
python3 scripts/agk/reviewers.py --check-codeowners
ok reviewers (.github/CODEOWNERS matches)
```

First commit, made locally on `main` with the Claude trailers: `124d92c chore: install agk 0.10.0 with /agk:init from the
plugin` (294 files). The push, verbatim:

```
$ git push -u origin HEAD
remote: Claude doesn't have GitHub access to gbvraju/agk-plugin-proof for your organization. An org admin can install the Claude GitHub App at https://github.com/apps/claude/installations/select_target, or reconnect GitHub from claude.ai settings (https://claude.ai/customize/connectors?auth_start=github&auth_start_force=1) to re-link an existing installation
fatal: unable to access 'https://github.com/gbvraju/agk-plugin-proof/': The requested URL returned error: 403
```

No second attempt and no other route. The commit exists only in the container's clone.

## Q-K3-72: does a tag pin work?

### The CLI form

```
HOME=/tmp/claude-0/proofa/home1 (fresh); cwd=/home/user/agk-plugin-proof
$ claude plugin marketplace add gbvraju/agk#v0.10.0
Adding marketplace…Cloning via HTTPS: https://github.com/gbvraju/agk.git
Refreshing marketplace cache (timeout: 120s)…
Cloning repository (timeout: 120s): https://github.com/gbvraju/agk.git (ref: v0.10.0)
Clone complete, validating marketplace…
Cleaning up old marketplace cache…
√ Successfully added marketplace: agk (declared in user settings)
exit 0

$ claude plugin marketplace list
Configured marketplaces:

  > anthropic-plugin-directory
    Source: Built in (Anthropic Directory)

  > agk
    Source: GitHub (gbvraju/agk@v0.10.0)

exit 0

$ claude plugin install agk@agk
Installing plugin "agk@agk"...√ Successfully installed plugin: agk@agk (scope: user)
exit 0

$ claude plugin list
Installed plugins:

  > agk@agk
    Version: 0.10.0
    Scope: user
    Status: √ enabled


--- settings written
{
  "extraKnownMarketplaces": {
    "agk": {
      "source": {
        "source": "github",
        "repo": "gbvraju/agk",
        "ref": "v0.10.0"
      }
    }
  },
  "enabledPlugins": {
    "agk@agk": true
  }
}
--- known_marketplaces
{
  "agk": {
    "source": {
      "source": "github",
      "repo": "gbvraju/agk",
      "ref": "v0.10.0"
    },
    "installLocation": "/tmp/claude-0/proofa/home1/.claude/plugins/marketplaces/agk",
    "lastUpdated": "2026-10-16T10:47:19.946Z"
  }
}--- cloned head
3a3686f0abce67a50e3f4d5b9e257825790f770a grafted, HEAD, tag: v0.10.0, tag: V0.10.0
```

`claude plugin marketplace add gbvraju/agk#v0.10.0` works: the clone is at `v0.10.0` (`3a3686f`), and Claude Code itself
wrote `{"source": "github", "repo": "gbvraju/agk", "ref": "v0.10.0"}` under `extraKnownMarketplaces` in the user settings,
and the same source in `known_marketplaces.json`. That is the entry `agk init` prints.

### The settings-file form

```
HOME=/tmp/claude-0/proofa/home2 (fresh), user-scope settings.json holds the printed entries; cwd=scratch dir
$ claude plugin marketplace list
Configured marketplaces:

  > anthropic-plugin-directory
    Source: Built in (Anthropic Directory)

exit 0

$ claude plugin list
No plugins installed. Use `claude plugin install` to install a plugin.

$ claude -p "reply with the word ok" (starts a session; marketplaces declared in settings register at startup)
Warning: no stdin data received in 3s, proceeding without it. If piping from a slow command, redirect stdin explicitly: < /dev/null to skip, or wait longer.
ok
exit 0

$ claude plugin marketplace list (after a session start)
Configured marketplaces:

  > anthropic-plugin-directory
    Source: Built in (Anthropic Directory)

  > agk
    Source: GitHub (gbvraju/agk@v0.10.0)

$ claude plugin list
Synced from claude.ai:

  > cowork-plugin-management@synced
    Version: 0.2.2
    Path: /tmp/claude-0/proofa/home2/.claude/plugins/synced/d026a7c9-8ea3-4ad8-a9ed-15bafecc55b6_e3430248-467e-4a02-afd9-998e8e910983/cowork-plugin-management
    Status: √ loaded

cache
installed_plugins.json
known_marketplaces.json
marketplaces
synced
3a3686f0abce67a50e3f4d5b9e257825790f770a grafted, HEAD, tag: v0.10.0, tag: V0.10.0
```

A user-scope `settings.json` holding the printed entries was read: after a session start the marketplace `agk` was
registered as `GitHub (gbvraju/agk@v0.10.0)` and cloned at `3a3686f` (tag `v0.10.0`). The entry with `ref` is accepted
there. The headless start did not install the plugin (`claude plugin list` shows only the synced plugin).

**Not tested:** the project-scope form, a committed `.claude/settings.json` in the proof repository. The documentation says
such entries apply only after the user accepts the workspace trust dialog, and that a `-p` or SDK session does not count as
accepting it; a headless run cannot answer the dialog. That form, and whether `enabledPlugins` then loads the plugin, needs
an interactive session by a maintainer. Q-K3-72 is therefore answered for the CLI and the user-scope settings, and still
open for the committed project-scope file.
