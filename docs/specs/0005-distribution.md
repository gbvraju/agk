# SPEC-0005: Distribution (plugin, marketplace, and where the law lives)

- Status: Approved
- Owner: maintainers
- Requirements: REQ-014 (to be added by ADR)

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.
The open points Q-K3-4 to Q-K3-11 were ruled on by the maintainers on 2026-10-15 (`docs/runs/spec-0005-notes.md`).
REQ-014 is not added by this spec: `docs/requirements.md` is protected, so an ADR adds it (proposed text in the notes).
Claude Code facts used here were read from https://code.claude.com/docs/en/plugins on 2026-10-15; a fact not
reconfirmed is marked `(verify)`. This spec is K3 criterion a of ADR-0015.

## Rules

### Where the law lives (the central decision)

1. **Recommendation: the hybrid (option C).** The law stays vendored in the repository and is enforced by CI: the
   checks, their tests, the workflows, `.claude/settings.json`, `config/`, the ADRs, the requirements, as installed by
   `agk init` and `agk adopt` today (SPEC-0001, SPEC-0002). The plugin carries the workflow commands and nothing that
   CI or the checks depend on. Options A (vendored, the plugin only drives init, adopt, doctor, brief and review) and B
   (the repository keeps configuration and the law only; CI installs the checks at a pinned kit version) are compared
   in `docs/runs/spec-0005-notes.md`; C is A plus the doctor comparison (rule 3) and the workflow commands (rule 8).
2. **The repository works without the plugin.** `make governance`, `make test`, the stop hook, the governance
   workflow and the installed `reviewer` subagent run with no plugin installed. The plugin is needed for the
   commands of rule 8 only. A cloud session may not have the plugin at all (rule 15), so nothing in the law may depend
   on it.
3. **The doctor comparison; no lock file.** `/agk:doctor` (SPEC-0006) compares every vendored file with the installed
   plugin's copy when the plugin version equals the version in `agk.toml`, and reports each difference; on a version
   mismatch it reports the mismatch and suggests `/agk:upgrade`. The plugin, outside the project tree, is the anchor.
   The kit keeps no lock file (it would be a second exception to principle 5); the version is already in `agk.toml`.
4. **What C does not claim.** A pull request can edit a vendored check; what stops a weakened check is the protected
   paths with an ADR, CODEOWNERS and the ruleset (human review), and, after the fact, the doctor comparison of rule 3, which detects a difference only when the plugin and `agk.toml`
   versions match.
   Option B would remove the check code from a pull request's reach and leave only the pin; K3 does not build it.
   The name of a future opt-in profile flag is reserved: `distribution = "pinned"` in `agk.toml` (not read in K3).
5. **Plugin and script are one code.** Every command that writes (rule 8) runs the script of the same name in
   `scripts/agk/` from the plugin root; the plugin has no logic of its own beyond prompts that call the scripts. A
   test installs a target through the script and through the plugin command's script call and compares the files.

### The plugin

6. **Layout.** The plugin root is the root of this repository: `.claude-plugin/plugin.json` (`name` `agk`, `version`
   equal to `kit_version` in `kit/manifest.json`), `skills/<command>/SKILL.md` for each command of rule 8, and the
   existing `scripts/agk/` and `kit/`. Claude Code copies only the plugin directory into its cache, so a plugin
   subdirectory could not reach `scripts/agk/` or `kit/`; a generated copy would be a generated file committed
   (principle 5). Commands are written as skills; `commands/` is the older format (a skill and a command file give the same name, and the
   skill wins on a collision; confirmed against the Claude Code documentation on 2026-10-16).
7. **Footprint.** The plugin ships no hook, no MCP or LSP server, no monitor and no `bin/` directory in K3. Installing
   a plugin trusts its hooks and `bin/`; the plugin asks for neither. The stop hook stays in the project's
   `.claude/hooks/`. `/agk:review` uses the project's `reviewer` subagent (installed by init and adopt); the plugin
   ships no copy of it, so there is no second `agk:reviewer`.
8. **The commands.** Namespaced `/agk:<command>`. A command that writes does not commit, push or merge, and never sets
   a spec `Approved` or an ADR `Accepted` (principle 6).

   | Command | What it runs | Writes | Network |
   | --- | --- | --- | --- |
   | `/agk:init` | `init.py .` (SPEC-0001) | new files in the repository | none |
   | `/agk:adopt` | `adopt.py .` (SPEC-0002) | owned files and marked blocks | none |
   | `/agk:doctor` | the SPEC-0006 script | nothing (report) | read-only `gh api` for settings it must check |
   | `/agk:upgrade` | the SPEC-0008 script | vendored files | none |
   | `/agk:spec` | `new_spec.py spec` (a Draft spec), `new_spec.py requirement` (a requirement proposal with its ADR draft), or, for one plain-language sentence, `intake.py` (SPEC-0012): a requirement, a Draft spec and an ADR stub on a new branch | new files | none (`--from-issue N`: the command reads the issue with `gh issue view`, read-only, and passes the text to the script with `--issue N --issue-text FILE`; the script never reads an issue) |
   | `/agk:issue` | the command renders an issue from a template and runs `gh issue create` | one GitHub issue | write, after asking |
   | `/agk:brief` | `new_spec.py brief`: a brief from `docs/briefs/TEMPLATE.md` | one file | none |
   | `/agk:ruleset` | `ruleset.py plan` (SPEC-0013 rules 19 to 21), then the person's `gh` applies the plan | one branch ruleset and two repository settings, after asking | read-only `gh api` for the plan; write, after asking |
   | `/agk:architect` | `playbook.py architect` (SPEC-0013 rule 7): prints how to start the architect session and checks the prerequisites | nothing | read-only `gh auth status` |
   | `/agk:review` | `review_context.py`, the `reviewer` subagent, `check_review_report.py` (SPEC-0003) | local files, never committed | none |

   `/agk:review` stays advisory: its output is never an approval and human review stays required (K2 ruling).
9. **User-invoked.** The commands that write (init, adopt, upgrade, spec, issue, brief, ruleset) are not invoked by the model on
   its own: each skill sets the frontmatter that turns off model invocation `(verify: disable-model-invocation)`.
10. **Two writers outside the tree.** `/agk:issue` and `/agk:ruleset` are the only commands that write outside the working tree, and each
    asks before it does. A test reads every skill and fails on `git push`, `git commit`, `gh pr`, `gh issue close`,
    `gh issue comment`, on `gh issue create` in any skill but `issue` and on `gh api --method POST|PUT|PATCH` in any skill but `ruleset`.
11. **Scripts are stdlib only, no network** (as SPEC-0001 rule 3), except where the table of rule 8 says otherwise; the
    network use of `/agk:doctor` and the issue reads are done by the command with the user's own `gh`, never by a
    script that holds a credential.

### The marketplace

12. **Where.** This repository is the marketplace: `.claude-plugin/marketplace.json` (`name` `agk`, an `owner`, one
    plugin entry `agk` whose `source` is `"."`, the repository root). Users add it with
    `claude plugin marketplace add gbvraju/agk` and install with `claude plugin install agk@agk`.
    `claude plugin validate .` passes (one warning: `CLAUDE.md` at the plugin root is not loaded as plugin context).
13. **Versions.** One number: the kit version. A release is a git tag `vX.Y.Z` on the default branch with the same
    version in `kit/manifest.json` and `.claude-plugin/plugin.json` (a test compares them). The entry sets no `version`
    of its own, so the manifest version wins. The default is no auto-update for a third-party marketplace
    `(verify: autoUpdate default)`, so an installed version changes only when the user updates.

### Team enablement

14. **Committed settings.** A team enables the plugin through `.claude/settings.json`: an `extraKnownMarketplaces`
    entry for `agk` (a `github` source with `ref` set to the release tag) and `"agk@agk": true` under `enabledPlugins`.
    `.claude/` is a protected class, so a change needs an ADR. Init and adopt print the two entries after a run (print
    only, as the scanner exclusions; adopt does not merge JSON, SPEC-0002 residual).
15. **Trust caveats, stated in the README.**
    - A project-scope plugin loads only after the user accepts the workspace trust dialog for the folder, and each
      collaborator installs it on their own machine.
    - A cloud session does not add the marketplaces a repository lists under `extraKnownMarketplaces`, so the plugin
      is absent there; rule 2 is why that is acceptable.
    - A plugin runs with the user's privileges; this one ships no hook, server or `bin/` (rule 7) and its scripts are
      the ones in this repository.
    - An agent that edits `.claude/settings.json` could point `extraKnownMarketplaces` at another source; the file is a
      protected class and its edit is an `ask` rule in `.claude/settings.json`.
16. **Approval friction.** In K1 and K2 each kit script run from outside the project needed an approval. The plugin
    changes this only if a permission rule can name the plugin's script path `(verify: ${CLAUDE_PLUGIN_ROOT} in a
    permission rule)`; otherwise each command asks once per session, which is accepted and recorded as a residual. The
    spec does not promise zero prompts.

### Intake

17. **GitHub issues are intake only.** Decisions, requirements, specs and ADRs live in the repository and nowhere
    else. An issue may propose, ask or report; it decides nothing. Concretely: (a) no requirement, spec rule or
    decision exists only in an issue or a comment; (b) `/agk:spec --from-issue N` copies the text into a repository
    file and records `N` there as a reference, and the file, not the issue, is what is reviewed; (c) a pull request that
    implements work from an issue may link it with a line `Issue: #N` in its body (optional: `check_pr_body.py` does
    not require it); (d) no check, workflow or command reads
    an issue to decide anything, closing an issue changes no status, and `/agk:issue` links the REQ and spec ids it was
    given in the issue body but leaves their status alone; (e) the drift-audit issue (SPEC-0004) is a report, not an
    authority. The issue templates (`.github/ISSUE_TEMPLATE/`, installed verbatim) and the optional `Issue:` line in the
    pull request template are protected changes made in the implementation PR with an ADR.

### Proof

18. **Proof plan (criterion a of ADR-0015).** From a fresh repository: add the marketplace, install the plugin, run
    `/agk:init`, push, and see `governance` green on GitHub with no file copied by hand. The run, the commands and the
    green result are recorded in `docs/runs/`, as for K1 and K2.
19. **Tests, no network.** `tests/kit_dev/test_distribution.py` (kit-only: the plugin is not installed into projects):
    the plugin manifest and marketplace file parse and carry the required keys; `plugin.json` version equals
    `kit_version`; there is one skill per command of rule 8 with a name that gives `/agk:<command>`; each skill names the
    script it runs and the script exists; rule 5 (same files from script and plugin call); rule 10 (forbidden verbs);
    the plugin ships none of the components of rule 7; `claude plugin validate .` runs when the `claude` CLI is
    installed and is skipped otherwise.
20. **Protected classes.** The implementation PR adds `.claude-plugin/` and `skills/` to
    `config/protected-paths.txt` and `config/reviewers.yaml` (the plugin's law at the repository root) and carries an
    ADR that names each class and adds REQ-014. They are not installed into projects.
21. **Order.** SPEC-0006 (doctor), SPEC-0007 (metrics) and SPEC-0008 (upgrade) are written Draft and Approved on their
    own; the commands `/agk:doctor` and `/agk:upgrade` are listed here and implemented with those specs.

## Tests

- Rules 5-7, 10, 13, 19: `tests/kit_dev/test_distribution.py`, marker `REQ-014 AC2`.
- Rules 12, 13: `claude plugin validate .` (skipped without the CLI), marker `REQ-014 AC1`.
- Rules 2, 17: the repository's own checks without the plugin, and the absence of an issue read in any script or
  workflow, marker `REQ-014 AC3`, `REQ-014 AC4`.
- Rule 18: a record in `docs/runs/`, checked by the maintainers, not by a test.

## Residual

- 2026-10-15: option B (pinned external checks) is not built; revisit if the doctor comparison proves too weak
  (due 2026-12-01).
- 2026-10-15: five facts were marked `(verify)` and were checked when the plugin was built (`docs/runs/spec-0005-verify-facts.md`,
  2026-10-16): the frontmatter key for user-only invocation, skills against commands giving the same name, and the
  auto-update default are confirmed; `${CLAUDE_PLUGIN_ROOT}` is confirmed in a skill's `allowed-tools` but not in a
  `settings.json` permission rule (Q-K3-73: no pre-approval in K3); the `github` source form with `ref` in
  `extraKnownMarketplaces` is not confirmed there and is decided by the criterion-a live proof (Q-K3-72) (due 2026-11-30).
- 2026-10-15: each command may ask for approval once per session, because a permission rule may not be able to name
  the plugin's script path (rule 16); revisit when the `(verify)` fact is checked (due 2026-11-30).
- 2026-10-15: the doctor comparison detects a changed vendored file only when the plugin version equals the version in
  `agk.toml` (rule 3) (due 2026-11-30).
