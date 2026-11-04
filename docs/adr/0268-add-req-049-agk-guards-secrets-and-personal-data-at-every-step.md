# ADR-0268: Add REQ-049: AGK guards secrets and personal data at every step

- Status: Proposed
- Date: 2026-11-04
- Deciders: maintainers
- Related: SPEC-0042, SPEC-0005, SPEC-0013, SPEC-0030, SPEC-0041, REQ-048
- Requirements: REQ-049

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-04:

> AGK guards data at every step: an agent session cannot read secret files, raw logs or servers directly, reads logs only through a redacting reader, is stopped when a person pastes a secret or personal data into a message, and writes nothing out (pull request bodies, comments, field notes, evidence, personal-mode state) that carries a secret or personal data.

The brief is issue #538. The owner's direction, dated 2026-11-04 in the brief and quoted as data:
"can AGK doing data ratification or Guardrail to avoid server reads, secret reads from logs, even
somebody put direct logs, AGK should carefully use with PII and secrets exposure risk". It is
recorded in one row of `docs/runs/decisions-log.md`.

Today AGK scans commits for secrets (the `Secret scan` step of `.github/workflows/governance.yml`,
and `scripts/agk/prepush.py` when gitleaks is installed), keeps invented data in tests, and
principle 9 says there are no secrets in the repository or in an agent session.
`docs/guides/security.md` says plainly that this "is not a wall: the architect role can read any
file in the folder it is started in". Nothing guards what a session reads, what a person pastes
into it, or what AGK writes outside commits (pull request bodies, comments, records, reports).
Anything that reaches the conversation has already left the machine, so a guard has to act before
the read. The personal mode of brief #536 (REQ-048, SPEC-0041) reads unfamiliar customer code with
one developer and no reviewer, so this intake comes first.

The Claude Code facts the design rests on were read from the hooks reference
(`https://code.claude.com/docs/en/hooks`), the hooks guide (`https://code.claude.com/docs/en/hooks-guide`)
and the permissions page (`https://code.claude.com/docs/en/permissions`) on 2026-11-04 and are
listed in SPEC-0042 rule 2; what could not be confirmed there is marked `(verify)` in the spec.

## Decision

1. REQ-049 is added to `docs/requirements.md` as `planned`. SPEC-0042 is added as `Draft`.
   Merging this pull request approves the requirement as a proposal; it does not approve the
   spec, which stays `Draft` until the owner's own `Approve:` line approves it (SPEC-0032 rule 5).
2. The data guard has four layers, each a numbered rule of SPEC-0042: reads of secret files, raw
   logs, servers and the environment are denied before they happen by a PreToolUse hook,
   `.claude/hooks/data_guard.py` (layer 1); logs are read only through a redacting reader,
   `scripts/agk/guard_logs.py` (`agk logs`, layer 2); a message a person pastes with a secret or
   personal data is blocked by a UserPromptSubmit hook (layer 3); and every write AGK makes passes
   one function, `guard.scan_text`, first (layer 4). The governance workflow's secret scan stays
   as it is.
3. The guard is on by default in every new and adopted project and in personal mode, with no
   setting that turns it off or removes a built-in rule. The `[guard]` table of `agk.toml` may only
   add (patterns, paths, commands, allowed hosts) and name single files with a reason
   (`allow_paths`); a loosening entry counts only when it is also on the default branch as last
   fetched, so a branch cannot loosen its own guard (SPEC-0042 rule 1).
4. The guard is a second line after least privilege, not a wall: patterns lower the risk and
   cannot catch every secret or every name in free text, and a hook guards the tools of a Claude
   Code session, not other programs the person runs. The spec, the security guide and `doctor`
   say so (SPEC-0042 rule 16).
5. The builds of SPEC-0042 rule 18 will change these protected path classes: `.claude/`
   (`.claude/hooks/data_guard.py`, new; its registration in `.claude/settings.json`;
   `.claude/hooks/architect_guard.py` and `.claude/hooks/conductor_guard.py`, which scan comment
   bodies before a post), `scripts/agk/` (`guard.py` and `guard_logs.py`, new and installed;
   `check_pr_body.py`, `pr_body.py`, `prepush.py`, `evidence.py`, `minutes.py`, `metrics.py`,
   `facts.py`, `product_report.py`, `doctor.py` and `config.py`), `kit/` (`kit/manifest.json`, the
   commented `[guard]` table of `kit/templates/agk.toml` and `kit/templates/agk.adopt.toml`),
   `agk.toml` (the same commented table; nothing is turned off), `tests/kit/` (their tests),
   `constitution/` (principle 9, one clause, in build (f), merged by the owner by hand) and, only
   if the owner rules amendment 114 item 3 in, `.claude-plugin/` and `skills/` (the plugin
   shipping the data guard as its one hook, SPEC-0005 rule 7). Each build adds its own ADR naming
   the classes it changes and citing this one, because the protected-path check counts only an ADR
   added or changed in the same pull request. No build changes `.github/`, `agk.mk`, `CLAUDE.md`,
   `Makefile`, `pyproject.toml` or the ruleset files.
6. The changes to Approved text that the guard needs (principle 9, `docs/guides/security.md`,
   SPEC-0005 rule 7, and SPEC-0041's dependence on this guard) are proposed in
   `docs/runs/proposed-spec-amendments-114.md`; none of them is applied by this pull request.

## Consequences

The requirement is listed as planned, and the spec and this ADR wait for approval. No check, hook,
flow or setting changes in this pull request. Once the builds land, a session in a project with
AGK installed is denied reads that today succeed (secret files, raw logs, remote shells and
databases, the environment) and is pointed to `agk logs`; a person who pastes a secret has the
message blocked; and a pull request body, comment or record that carries a secret or personal data
is refused before it is written, naming the kind and the position, never the value. The personal
mode of SPEC-0041 depends on this guard and builds after it.

## Residual

None beyond SPEC-0042's residual. The intake checks cannot tell whether the detectors, the
denials or the limits are the right ones; that is the review of this pull request.
