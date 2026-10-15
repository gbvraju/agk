# Notes on SPEC-0005 (distribution)

Date: 2026-10-15 (from `date -u`). Day-8 brief, item 2. The spec is a Draft; nothing here is implemented, and REQ-014 is
not added (`docs/requirements.md` is protected; an ADR adds it). The maintainers' direction was to recommend the hybrid
(law vendored in the repository and enforced by CI; the plugin carries the workflow commands), to compare A, B and C
honestly, to list eight commands, and to state that GitHub issues are intake only.

## Decisions taken in the draft (each is a numbered rule)

- Hybrid recommended: vendored law, plugin as the command surface, a lock as the anchor (rules 1-5).
- The repository works without the plugin (rule 2), because a cloud session does not load project-declared
  marketplaces.
- The plugin has no hooks, servers, monitors or `bin/` in K3, ships no second reviewer, and its commands that write are
  user-invoked (rules 7-9). Only `/agk:issue` writes outside the working tree (rule 10).
- One version for kit and plugin; this repository is the marketplace; releases are tags (rules 12-13).
- Team enablement is committed settings, printed not merged (rule 14); trust caveats are stated (rule 15).
- Issues are intake only (rule 17).

## The comparison: where the law lives

A: keep vendoring the checks; the plugin only drives init, adopt, doctor, brief and review.
B: the repository keeps configuration and the law (settings, workflow, ADRs, requirements); CI installs the checks at a
pinned kit version (a git SHA or a release artifact).
C: A plus a lock of versions and digests, plus the workflow commands, with B reserved as an opt-in profile.

| Criterion | A | B | C (recommended) |
| --- | --- | --- | --- |
| Can a pull request weaken a check? | Yes: it can edit the vendored check, and CI then runs the edited copy. What stops it is the protected path, an ADR, CODEOWNERS and the ruleset: human review | Not the check code: a pull request can change only the pin, one line in a protected workflow, which is visible and needs an ADR. This is the strongest position of the three | As A, plus after-the-fact detection: the doctor compares the lock and files with the plugin's manifest, an anchor outside the project. Detection, not prevention |
| Offline or air-gapped teams | Works | Needs a fetch at every CI run, or a mirror of the artifact | Works; the plugin is a one-time developer-side install |
| Supply-chain exposure | None at CI time | A remote dependency on every run: host availability, tag or SHA integrity, a token for a private source. A SHA or digest pin fixes content, not availability | None at CI time; the plugin install is a trust decision made once by each developer |
| Upgrade cost | High: file-level upgrade of about fifty vendored files (SPEC-0008), with edited files to detect | Low for the checks (one pin); the law files (settings, workflow, templates) still need an upgrade path | Medium: the lock makes the file-level upgrade mechanical (`/agk:upgrade`) |
| K2 finding (c): project scanners see kit code | Yes; mitigated by suppressions and exclude snippets (ADR-0010) | No: the kit code is not in the project tree | As A |
| Zero-touch on a product repository | Adopt writes owned files and marked blocks; the tree carries the kit | Fewest files in the tree | As A |
| Cloud sessions, which do not load project-declared marketplaces | Works | CI works; local checks need an install step in the session | Works |
| New things to build | Nothing for distribution | A package or release artifact, a pin mechanism, local and CI version parity | The lock, five commands, the plugin files |
| Proven live | K1 and K2 | No | A's proof plus the K3 proof of rule 18 |

Honest summary. B is better on tamper-resistance and on scanners, and worse on offline use, on supply-chain exposure
at every CI run, and on what must be built. C keeps A's proven, offline, dependency-free CI and adds a detection
anchor and the workflow commands, but it does not close the weakening gap of A: a reviewer-approved pull request can
still change a vendored check. Whether that is acceptable is for the maintainers (principle 1); rule 4 and the residual
keep B available.

## Proposed REQ-014 (for the ADR that adds it)

```
### REQ-014 — Install and run agk as a Claude Code plugin (K3)

- Acceptance: AC1 the plugin installs from the agk marketplace and `/agk:init` gives a repository with `governance` green on GitHub; AC2 each command runs the same script as the kit, and the plugin carries no hook, server or `bin/`; AC3 the repository's checks and CI work without the plugin; AC4 GitHub issues are intake only
- Status: planned
```

## Claude Code facts used (read on 2026-10-15)

From https://code.claude.com/docs/en/plugins (overview), `/plugins/components`, `/plugins/loading`,
`/plugins/security`, `/plugins/create-marketplace` and `/plugins/marketplace-reference`:

- A plugin is a directory with an optional manifest at `.claude-plugin/plugin.json`; components are skills, agents,
  hooks, MCP servers and others; a skill runs as `/<plugin>:<skill>`.
- `commands/` is the older format; skills supersede it for new work; `commands/<file>.md` becomes `/<plugin>:<file>`.
- `${CLAUDE_PLUGIN_ROOT}` is the plugin's install directory (per version); `${CLAUDE_PLUGIN_DATA}` survives updates.
- Installed copies live under `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`; files outside the plugin
  directory are not copied.
- A marketplace is a repository or directory with `.claude-plugin/marketplace.json` (required: `name`, `owner`,
  `plugins`; an entry needs `name` and `source`). A `source` may be a relative path (`"."` is the marketplace root), or
  `github`, `url`, `git-subdir` with `ref` and `sha` pins, `npm`, `archive`, `command`.
- The manifest version wins over the entry version; an unchanged version string keeps users on the cached copy.
- Users run `claude plugin marketplace add <owner>/<repo>` and `claude plugin install <name>@<marketplace>`;
  `claude plugin validate` checks a plugin or a marketplace.
- A project can list `extraKnownMarketplaces` and `enabledPlugins` in the committed `.claude/settings.json`; each
  collaborator still installs on their own machine; a relative-path plugin needs no install record.
- A cloud session does not add marketplaces listed in `extraKnownMarketplaces`.
- A plugin runs code with the user's privileges (hooks, monitors, MCP and LSP servers, `bin/` on the shell's PATH);
  skills, commands and agents enter Claude's context as instructions; third-party marketplaces do not auto-update by
  default.

## Facts to verify before the spec is Approved (`(verify)`)

- The skill frontmatter key that turns off model invocation (`disable-model-invocation`) and its effect on `/agk:` use.
- Whether `${CLAUDE_PLUGIN_ROOT}` can appear in a permission rule, to avoid an approval prompt per script run.
- That the brief's `commands/` layout and a `skills/` layout both give `/agk:<name>`.
- The exact `github` source form in `extraKnownMarketplaces` with a `ref` (the page example shows the `git` form).
- The auto-update default for a marketplace added from a repository declared in settings.

## Questions for maintainers

- **Q-K3-4:** where the lock lives and its format (new `config/` file, or fields in `agk.toml`); it is SPEC-0008's, but
  SPEC-0006 and this spec depend on it.
- **Q-K3-5:** plugin root = the root of this repository (the draft) or a `plugin/` subdirectory. A subdirectory would need
  a generated copy of `scripts/agk/` and `kit/` (the cache copies only the plugin directory), and generated files are
  not committed (principle 5).
- **Q-K3-6:** skills (`skills/<command>/SKILL.md`, the draft) or `commands/` as in the brief. The documentation calls
  `commands/` the older format.
- **Q-K3-7:** `/agk:review` uses the project's installed `reviewer` subagent (the draft). The alternative is a plugin
  agent `agk:reviewer`, which would duplicate the installed one.
- **Q-K3-8:** this repository as the marketplace (the draft), or a separate marketplace repository that lists a pinned
  release of this one.
- **Q-K3-9:** init and adopt print the settings entries (the draft). The alternative is to template
  `.claude/settings.json` with the release tag, which turns a verbatim file into a template (SPEC-0001 rules 7 and 8).
- **Q-K3-10:** approval friction. If a permission rule cannot name the plugin script path, each command asks once per
  session; is that acceptable for K3?
- **Q-K3-11:** the issue templates (`.github/ISSUE_TEMPLATE/`) and an `Issue: #N` line in the pull request template are
  protected changes; confirm the line is wanted and whether `check_pr_body.py` should require it (the draft: it does
  not).
