# SPEC-0005: the five `(verify)` facts, checked against the current Claude Code documentation

Date: 2026-10-16 (from `date -u`). Checked while building the plugin (ADR-0019). Sources, all under
https://code.claude.com/docs/en/: `skills`, `settings`, `settings-reference`, `permissions`, `plugins/create-marketplace`
and `plugins/host-marketplace`. Installed CLI: Claude Code 2.1.301. A fact is *confirmed* when a page states it, *false*
when a page contradicts it, *not confirmed* when the pages are silent or show a different form. Nothing here is a guess:
where a page does not say, the fact stays `(verify)` and a question is open.

| # | Fact (SPEC-0005) | Result | Evidence | Where it goes |
| --- | --- | --- | --- | --- |
| 1 | Frontmatter key that turns off model invocation (rule 9) | **confirmed** | `skills`: "`disable-model-invocation`: Set to `true` to prevent Claude from automatically loading this skill. Use for workflows you want to trigger manually with `/name`." The invocation table lists "You can invoke: Yes; Claude can invoke: Not on its own." It also keeps the skill out of subagent preloads and out of scheduled-task prompts. | six writing skills set it; a test asserts it |
| 2 | `${CLAUDE_PLUGIN_ROOT}` in a permission rule (rule 16) | **not confirmed** for `settings.json`; **confirmed** for a skill's `allowed-tools` | `permissions` and `settings-reference` never mention the variable in a rule. `skills` says `${CLAUDE_PLUGIN_ROOT}` is "substituted only in plugin skills", in "the skill's markdown content, and Bash rules in the `allowed-tools` frontmatter", and that `allowed-tools` entries use permission-rule syntax and grant use of the tool for the turn. | Q-K3-73; amendment A in `docs/runs/proposed-spec-amendments-13.md`; no skill sets `allowed-tools` (a test asserts it) |
| 3 | `skills/<name>/SKILL.md` and `commands/<name>.md` give the same `/agk:<name>` (rule 6) | **confirmed** | `skills`: plugin skills are "namespaced as `/plugin-name:skill-name`"; "A file at `.claude/commands/deploy.md` and a skill at `.claude/skills/deploy/SKILL.md` both create `/deploy` and work the same way"; on a collision the skill wins. | the `(verify)` mark is removed by amendment D |
| 4 | The `github` source form with a `ref` in `extraKnownMarketplaces` (rule 14) | **not confirmed** | `settings-reference`, `extraKnownMarketplaces`: the `github` form is documented as `{"source": "github", "repo": "owner/name"}` and the `git` form as `{"source": "git", "url": ...}`; no `ref` is shown. The `strictKnownMarketplaces` source table does list `ref` ("a branch or tag") and `path` for `github` and `git`. `marketplace add` accepts `owner/repo#<ref>`. | Q-K3-72; amendment B; init and adopt print the entry with `ref` and the line "(verify)" |
| 5 | Auto-update default for a marketplace declared in settings (rule 13) | **confirmed** | `settings-reference`: "third-party marketplaces default to `false`" (official ones default to `true`); `autoUpdate` is an optional Boolean beside `source`. `host-marketplace`: "Background auto-update is off for your marketplace by default, and `marketplace.json` has no field to turn it on." | no change |

## Other things the build found

- `claude plugin validate .` (2.1.301) passes with one warning: "CLAUDE.md at the plugin root is not loaded as project
  context. To ship context with your plugin, use a skill." The repository's `CLAUDE.md` is the project's operating
  rules, not plugin context, so it stays; the warning is recorded in ADR-0019. The marketplace `source` validates as `"."`
  and as `"./"`; the spec's `"."` is kept.
- `host-marketplace`: when both `plugin.json` and the marketplace entry set `version`, `plugin.json` wins and `validate`
  reports the mismatch. The entry sets none (rule 13); a test asserts it.
- `validate` also advises a README line `/plugin install agk --marketplace gbvraju/agk` ("Claude Code 2.1.275 or later"). It
  is a different install form from the spec's `claude plugin install agk@agk`; the README uses the spec's, which the
  `create-marketplace` page documents. Not adopted.
- `settings-reference`: `extraKnownMarketplaces` and `enabledPlugins` in a repository's `.claude/settings.json` apply only
  after the user trusts the folder, and "still don't load in a cloud session" (rule 15 is confirmed). `claude plugin
  marketplace add <owner>/<repo> --scope project` writes the committed entry itself; the kit prints the entries instead
  (Q-K3-9).
- Not done: `claude plugin marketplace add` and `claude plugin install` against GitHub, and `/agk:init` in a fresh
  repository. They change the user's Claude Code configuration; they are the proof of rule 18, a maintainers' step.
