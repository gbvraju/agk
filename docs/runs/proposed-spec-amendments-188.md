# Proposed spec amendments 188 (SPEC-0005; REQ-014)

Date: 2026-11-19 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0651 (brief #1551), which stays `Proposed` for the maintainers' decision. The path: `docs/specs/0005-distribution.md`.
Brief #1551 reserved amendment 188. This file proposes the lines and does not edit the spec. Build (a) applies them word
for word, on a person's `Approve: SPEC-0005` on its pull request; no session posts it.

The sentence (brief #1551): "The distribution spec says what the plugin really ships, its hooks and its agents with the
personal-mode reviewer, and states its contexts, so item 5 of amendment 113 and the hook patch apply, and no other
amended spec hits the Contexts rule unseen."

## Why

Measured on the default branch at 3c383bd3 (2026-11-19), the brief's figures reproduced (session rule 19):

- `.claude-plugin/plugin.json` registers 2 hook events (`PreToolUse` with `onFailure: block`, and `Stop`, each running
  `.claude/hooks/plugin_hooks.py`) and lists 7 agents: `architect`, `architect-review`, `conductor`, `drift-auditor`,
  `personal-reviewer`, `shadow` and `steward`. Rule 7 says the plugin ships no hook and no copy of the reviewer.
- Amendment 113 item 5 applied to rule 7 on a probe tree: `check_specs.py` prints
  `FAIL specs: spec 'docs/specs/0005-distribution.md' Contexts section: rule 4: no section`.
- `kit/manifest.json` lists `.claude/agents/personal-reviewer.md` under `verbatim` and `.claude/agents/reviewer.md`
  under `experimental` (installed only with `experimental_reviewer = true`, `common.experimental_enabled`). Rule 7 says
  the reviewer is "installed by init and adopt".

Amendment 142 item 2 (`check_specs.py` `contexts_failures`) refuses any change to an Approved spec without a
`## Contexts` section. SPEC-0005 has none, and amendment 113 (2026-11-04) is older than the rule and supplies none. So
build (i) of SPEC-0041 left item 5 out (Q-1507-1 on #1550), and the owner ruled it goes to a later build (2026-11-19,
quoted as data in brief #1551). Q-1518-1 (#1519) proposed a one-line hook patch to the same rule and was never answered.
Item 5 also keeps "the plugin still ships no hook", which ADR-0612 decision 1 has since made untrue. This amendment
replaces both patches with one text written from the code.

## Items

1. **A `## Contexts` section (new).** Placed after `## Tests` and before `## Residual`, as the other Approved specs place
   it. Each entry is one line, since `check_specs.py` joins the section's lines and cuts them at top-level semicolons,
   and no entry carries a semicolon outside brackets:

   ```
   ## Contexts

   - kit: this repository is the plugin root and the marketplace (rules 6 and 12), its checks, tests and stop hook run without the plugin (rule 2), and `tests/kit_dev/test_distribution.py` pins the plugin's footprint (rule 19)
   - github: a project's law is vendored and enforced by CI with no plugin (rules 1 and 2), a team enables the plugin through `.claude/settings.json` (rule 14), and a cloud session runs without it (rule 15)
   - local: a laptop session loads the plugin after the folder's trust dialog (rule 15), its hooks and agents run from the plugin as rule 7 lists them, and an installed project's checks still run without it (rule 2)
   - personal: the law lives in the sidecar and its checks run from the plugin's scripts, so personal mode needs the plugin (rules 1 and 2), a command commits to the sidecar only (rule 8), and the personal-mode reviewer comes from the plugin (rule 7)
   - stacks: not applicable: the plugin and the installed files are the same whatever a project's stacks, and no test or build step of a stack changes
   ```

2. **Rule 7, the footprint, rewritten.** It replaces amendment 113 item 5 and Q-1518-1's patch. The rule becomes:

   "7. **Footprint.** The plugin ships no MCP or LSP server, no monitor and no `bin/` directory. Its only hooks are the
   `PreToolUse` and `Stop` hooks of `.claude-plugin/plugin.json`, each running `.claude/hooks/plugin_hooks.py`. That
   script runs the data guard and the stop check only for a project that does not register them itself, and a guarded
   role agent's guard whenever the session runs that agent (ADR-0612 decisions 1 and 2, ADR-0641 decision 3). Its
   agents are the files `plugin.json` lists under `agents`, each named `agk:<name>`: the six role agents of ADR-0612
   decision 1 and, for personal mode, where the product has no `.claude/agents/`, `personal-reviewer`, which reads only,
   is advisory and experimental (SPEC-0041 rule 17, `Q-S0041-10`), and which a team-mode session does not use. In an
   installed project the hooks stay in `.claude/hooks/`. `/agk:review` uses the project's `reviewer` subagent, installed
   only with `experimental_reviewer = true`, and the plugin lists no `reviewer.md`, so there is no second
   `agk:reviewer`."

3. **Rule 15, third bullet.** "A plugin runs with the user's privileges; this one ships no hook, server or `bin/`
   (rule 7) and its scripts are the ones in this repository." becomes "A plugin runs with the user's privileges. This
   one ships the two hooks of rule 7 and no server, monitor or `bin/`, and its scripts are the ones in this repository."

4. **Rule 19, the test list.** "the plugin ships none of the components of rule 7" becomes "every hook command of
   `plugin.json` runs `plugin_hooks.py`, its `agents` list is exactly the files rule 7 names, with no `reviewer.md`, and
   it ships no server, monitor or `bin/`". This also replaces amendment 113 item 9's "checks the plugin ships no hook".
   The rest of rule 19 is unchanged.

5. **Amendment 113's record.** Build (a) adds one line at the end of `docs/runs/proposed-spec-amendments-113.md`:
   "Item 5 and its item 9 test line: replaced by amendment 188 items 2 and 4." Q-1518-1 is answered by the owner, not by
   this amendment (Q-1551-2).

6. **Unchanged:** rules 1 to 6, 8 to 14, 16 to 18, 20 and 21; the `## Tests` lines (rule 7 and rule 19 stay under
   `REQ-014 AC2`); the Residual; SPEC-0030 and amendment 142's rule. Build (a) adds the `## Contexts` heading and the
   five lines of item 1, and changes only the sentences items 2 to 4 name.

## The build

Build (a), filed later by the `brief` skill with its own Settings section and `Depends-on:` this intake (brief #1551)
and brief #1507, tests first, about 200 changed lines or fewer, with ADR-0651's protected classes (`scripts/agk/`,
`tests/kit/`, `tests/kit_dev/`, `skills/`) and no `Covered-by:`:

- apply items 1 to 5 word for word;
- `docs/guides/reference.md`, the trust bullet "This one ships no hook, server, monitor or `bin/`" (line 1025 at
  3c383bd3; the brief says line 1017), to rule 15's new bullet;
- `skills/review/SKILL.md`, step 3's "This plugin ships no reviewer.", to: the team reviewer is the project's, and the
  plugin's `personal-reviewer` is for personal mode;
- `scripts/agk/check_specs.py`, the message for a missing section: `spec '<path>' Contexts section: rule 4 (amendment
  142): no section, add one with kit, github, local, personal and stacks as the spec template lists them`, naming
  `docs/specs/TEMPLATE.md` only when that file exists in the repository, and "the spec template" otherwise (a
  plugin-layout project or a sidecar). It names the rule and the path, never the spec's text. No rule changes;
- `tests/kit_dev/test_distribution.py` pins items 1 to 4 and the footprint, and `tests/kit/test_brief_contexts.py` the
  message;
- one `changelog.d` fragment, since `check_specs.py` and `skills/review/SKILL.md` are installed files.

The records `docs/runs/spec-0005-notes.md` and `docs/runs/spec-0013-notes.md` say the old footprint; they are records and
stay as written.

## Tests (build (a))

Invented trees, `example.com` only, no network:

- a fixture SPEC-0005 amended with item 1's section passes `check_specs.py`, and the same change without it fails with
  the missing-section message: a replay of #1550's failure;
- item 1's five lines pass `contexts_problems` exactly as written, and a semicolon added outside brackets fails;
- a heading `## Contexts (2026-11-19)` still counts as the section;
- `plugin.json` with an agent that rule 7 does not name fails, naming it; with `reviewer.md` fails; with a hook
  command other than `plugin_hooks.py` fails, as ADR-0641 decision 3's test does;
- the message, in a project fixture with no SPEC-0030 file and in one with its own SPEC-0030, names the template and
  the five contexts and never the spec's text, and in a fixture with no `docs/specs/TEMPLATE.md` it names "the spec
  template";
- a Draft spec with a merger record (`approval_records`) flipped to Approved still needs the section;
- an Approved spec untouched since before the rule still passes.

Marker `REQ-014 AC2`.

## The settings, each with its impact, traced

| Setting | Impact |
| --- | --- |
| `[kit] layout` `installed` or `plugin` | the same check runs vendored or from the plugin, and the message's template name follows the build's rule |
| `forge = "files"` (personal mode) | the sidecar's specs meet the same rule; `personal.py confirm` sets a sidecar spec Approved, so its next amendment needs the section too, with the same message |
| `experimental_reviewer` | true installs `reviewer.md` for `/agk:review` in team mode; rule 7 now says so and no longer says "installed by init and adopt" |
| `review_mode` solo or team, `spec_approvers` | unchanged; applying amendment 188 needs an `Approve: SPEC-0005` line from a listed approver, in solo mode the one person's confirmed line |
| `[flow] plan_issue`, `Wave:` | this brief and build (a) are Wave 4, beside brief #1507 |
| `brief_code_paths` | build (a) names two code paths, `scripts/agk/check_specs.py` and `skills/review/SKILL.md` |
| `pr_mode` | unchanged |
| `enabledPlugins`, `extraKnownMarketplaces` in `.claude/settings.json` | unchanged; rule 14 stands |

No workflow, ruleset, required check or secret changes, and no GitHub API call is added.

## Customer projects

A project's own Approved specs meet the rule on their next amendment, as the kit's do. Build (a) makes the message say
how to fix it in the project's own words. A project's `kit` context is always `not applicable` with a reason, as
`docs/guides/getting-started.md` shows for a brief. No project file is rewritten by the upgrade.

## Questions (brief #1551), each with the reading this proposal takes

- Q-1551-1: the other 15 blocked specs' sections. Reading: not in this brief. One later intake writes them in one
  amendment, starting from the texts that amendments 158 and 160 already carry and the briefs' `Contexts:` lines. Until
  then each waiting amendment stays unapplied, never applied without the section.
- Q-1551-2: Q-1518-1 on #1519 is unanswered. Reading: it stays open for the owner. Item 2 is the text that settles it,
  and the owner's `Approve: SPEC-0005` on build (a) is that answer. No session posts a `Maintainer answer:` for it.
- Q-1551-3: should `doctor.py` or `upgrade.py` warn about a project's Approved specs without the section? Reading: no,
  not here. The rule bites only on the next amendment, and a warning on 51 kit specs and every project's older specs
  would be noise until the intake of Q-1551-1 lands. Revisit with it.
- Q-1551-4: should a brief-time warning (`check_brief.py`, never failing) name an Approved spec in `Touches:` with no
  section? Reading: not here. Its rule belongs in SPEC-0030 rule 4, which has no section either and waits on amendment
  142's own text. Proposed with Q-1551-1's intake.
- Q-1551-5: #1550 put `personal-reviewer.md` in the manifest's `verbatim` list, so every installed team-mode project gets
  an unused personal-mode agent, while the team `reviewer.md` is opt-in. Reading: rule 7 states only what the plugin
  ships and says nothing the manifest contradicts. Whether installed projects carry the file is for the owner. If it
  moves out of `verbatim`, this amendment is unchanged.
- Q-1551-6: priority. Reading: 2. Nothing a project runs is broken, but 18 amendment files wait on the same rule, and
  build (a) unblocks the first.
