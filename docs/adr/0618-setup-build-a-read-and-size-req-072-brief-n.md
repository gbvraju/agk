# ADR-0618: /agk:setup build (a): read the machine and the repository, size the builders, print the plan

- Status: Proposed
- Date: 2026-11-17
- Deciders: maintainers
- Related: SPEC-0065, ADR-0578, ADR-0577, ADR-0409, brief #1460, plan #661
- Requirements: REQ-072

## Context

SPEC-0065 (Approved) names eight builds of `/agk:setup` (rule 18); this is build (a): the machine read, the plan and
the sizing (rules 3, 5 and 6), `setup.py` with `status` and the `--json` table (rules 2 and 12), and the skill's first
form. ADR-0578 added REQ-072 and names only `docs/requirements.md`, so this build records its own classes here.

## Decision

1. **A kit-only helper, `scripts/agk/setup.py`**, run from the plugin root and never installed into a project, as
   `wsl.py` is (named in `tests/kit_dev/test_kit_manifest.py`'s kit-only list). Two forms: `plan` and `status`; `--json`
   prints `steps` (`step`, `result`, `note`), `pending`, `roles` and `builders`.
2. **It reads, never asks** (rule 3): the OS and version, total and available memory, cores, free disk, the
   administrator right, WSL, the tools and their versions (Python, git, GitHub CLI, Claude Code, Node.js, Podman,
   Docker, PowerShell), winget and its policy, a configured proxy (`configured` or `none`, never its address) and the
   clone's remote (`owner/name` only); and `execution`, `review_mode`, `[flow]`, `[capacity]`, `[autopilot]`,
   `config/reviewers.yaml`, `[team] members`, the lease (`conductor.py lease --show`), the running builders (one
   `session.py plan --json`) and a live steward from the steward's own cache, with no call.
3. **Sizing** (rule 6): (available memory less the `[capacity] profile`'s reserve of the total, else 25 percent) divided
   by `builder_memory_gb` (the project's value, the smaller of `[flow]` and `[capacity]`; else 4 GB with a Playwright
   configuration or a container file, else 3 GB), rounded down; capped by one builder per two cores, by `max_builders`
   and, in team mode, by `max_builders` less the running builders. The cap that applied and its reason are printed;
   `--builders N` may lower the figure and is refused above it. Unreadable memory gives 1 and says `memory unknown`.
4. **This build installs nothing and writes no file.** Each check row is `skipped` when met and `waiting` with what to
   install when not, so a second run changes nothing and a stopped run resumes at its first unmet step. The proof rows
   (rule 12) run `doctor.py`, `tests/kit/test_doctor.py` where present, one container start when the project uses
   containers and `session.py plan`; they are the last steps, after the person's yes (rule 5), so `status` runs them
   and `plan` lists them as `skipped` (not yet run) and runs none. Rule 7's minimum-version table starts in `setup.py` with Python 3.11 and Node.js 20.
5. **The skill** `skills/setup/SKILL.md` has the forms `/agk:setup` and `/agk:setup status`, user-invoked only
   (`disable-model-invocation: true`) until build (g) gives the steward its hand-off.

## Consequences

A person sees what the machine and the project hold and how many builders fit, with the reason, in one command that
changes nothing. Protected path classes changed: `scripts/agk/` (`setup.py`), `skills/` (`skills/setup/SKILL.md`),
`tests/kit/` (`test_setup_read.py`), `tests/kit_dev/` (`test_kit_manifest.py` lists the kit-only file,
`test_distribution.py` the new command) and `agk.toml` (the `[[testing.map]]` entries). No workflow, ruleset, required
check or secret changes.

## Residual

- 2026-11-17 (verify): `setup.py` has not run on native Windows or WSL 2; the pull request reports
  `Verified: (verify) run on Windows` until a person runs it.
- 2026-11-17 (verify): the winget policy key (`EnableAppInstaller` under the App Installer policies) and the small image
  of the container start (`hello-world`) are not read from their vendors' documentation.
- 2026-11-17: the proxy's test download (rule 3) is left to the builds that download, (c) and (e).
