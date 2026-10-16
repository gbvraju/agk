# Notes on SPEC-0013 (playbook)

Date: 2026-10-16 (from `date -u`). Overnight brief 4, item B. The spec was written Draft and set **Approved** on the maintainers' rulings of 2026-10-16 (final commit of the pull request); nothing is implemented and no protected path is
changed by this pull request. It is the fifth and last of the K4 specs of ADR-0021 (decision 2) and serves REQ-020 and exit criterion g.
Every question below was raised with a conservative reading and has been ruled (section Rulings); none is open.

## What exists today (read on 2026-10-16, on `main` at 0c19763)

- **Installed layout.** `kit/templates/vision.md` becomes `constitution/vision.md` with a single `TODO(maintainers)` paragraph;
  `constitution/principles.md` is a verbatim file that the doctor compares with the kit's copy; `kit/templates/adr-0001.md` becomes
  `docs/adr/0001-adopt-agk.md`, which **already records the ruleset** (decision 3) and the reviewer model. So an "ADR-0001 with milestones,
  non-goals and the ruleset" cannot be drafted: ADR-0001 exists and is about adopting the kit. The brief's `docs/vision.md` is
  `constitution/vision.md` in the kit.
- **The role file.** The Claude Code documentation (read 2026-10-16, `code.claude.com/docs/en/sub-agents`): `claude --agent <name>` starts
  a session whose main thread takes that subagent's tool restrictions and model, a project subagent file may carry `hooks` in its
  frontmatter (they run only while that agent is active; they need a trusted folder), and `tools` is a list of tool names with no path
  scope. A plugin subagent ignores `hooks`, `mcpServers` and `permissionMode`; that is why the architect is a project file
  (`.claude/agents/`), not a plugin agent (SPEC-0005 rule 7 also says the plugin ships no agent).
- **The verdict convention.** `metrics.VERDICT` accepts `Verdict: cleared <hex sha of 4 to 40>`, `Verdict: fix list`, `Verdict: rejected`; the first
  line of a comment; `metrics.verdicts` reads them in time order. `merged_head_cleared` is `yes`, `no` or `unknown` (SPEC-0007 rule 8).
- **`check_specs.py`** fails an Approved spec that changed without a proposed-amendments file that names it. It reads no pull request body,
  no `Advances:` line and no `Q-` ids. `check_pr_body.py` reads `Advances:` and `Build-state row:` only.
- **`gh pr view`** appears in no installed kit text. The kit `CLAUDE.md` has no pull-request-state command at all; the repository's own
  operating rules say "check PR state before any push" without a command. (Search of the whole repository at 0c19763: no match.)
- **Skills.** The plugin has eight skills (SPEC-0005 rule 8). The tests assert exactly those eight (`tests/kit_dev/test_distribution.py`).
  `/agk:issue` is the only command that writes outside the working tree (SPEC-0005 rule 10).
- **Doctor.** `required-check-governance` is an `error` check (SPEC-0006 rule 5); the ruleset elements are a minimum, so a stricter ruleset is
  `ok`. The check has no notion of a phase.

## The three read-only analyses the brief asked for

**1. Merged before cleared.** Across the 51 merged pull requests of this repository (read through the REST API on 2026-10-16): the first
verdict line is on #33 (2026-10-15, 17:15 UTC). Before it, 31 merged pull requests have no verdict line, because the convention did not
exist (decisions-log row of 2026-10-15). Since #33, 20 were merged: **17 cleared at their merged head**; **#45** and **#50** have verdict lines
that name an earlier head (a final commit followed the last `cleared`, `merged_head_cleared = no`); **#46** has no verdict line
(`unknown`). The two pilot cases the brief names (a pilot pull request and one earlier in K2) are outside this repository's counts. The metrics
field already reports exactly this; rule 18 keeps it as the check and adds a line to "At risk" by amendment.

**2. Lifecycle rule (a): an implementation pull request advances a requirement with no Approved spec.** 51 of 51 merged pull requests carry an
`Advances:` line. 33 are docs-only (all changed paths under `docs/`) and are not checked. Of the 18 implementation pull requests, 13 would
pass. **5 would have failed**: #1 (REQ-001, REQ-002, REQ-003), #3 (REQ-001, REQ-002, REQ-003, REQ-005, REQ-008), #6 (REQ-001, REQ-003,
REQ-005), #9 (REQ-001, REQ-005, REQ-008) and #18 (REQ-005): every failure is "no spec names the requirement" (these requirements predate specs;
no draft spec was involved). In each of the five, an ADR in the tree at the merge commit names every advanced requirement, which is why
rule 23 exempts a requirement that no spec names and an ADR names. Without the exemption the rule would block any pull request that
advances REQ-001 to REQ-008, which have no spec.

**3. Lifecycle rule (b): a spec is Approved with an open question.** Counting an id as *asked* only where it starts a table row or a list
item (`| Q-...` or `- Q-...`) in the spec or its notes file, and as *ruled* when the notes have a `## Rulings` row starting with the id or the
decisions log has `<id> ruled`: **0 of the 11 Approved specs** (SPEC-0001 to SPEC-0011) has an open id. Two cruder definitions were
tried and rejected: counting every mention of an id and requiring a decisions-log row would flag 7 of 11 specs (the rulings of K1 to K3
live in notes `## Rulings` tables, not in the log: only 33 of the 115 ids have a log row); counting every mention with the Rulings rows
allowed still flags SPEC-0002 (its ids Q-K2-1 to Q-K2-6 are named in prose) and SPEC-0011 (an example id inside a code span in a table row).

## Decisions taken in the draft (each is a numbered rule)

- The method is packaged as: three plugin skills (`start`, `architect`, `ruleset`), one project agent file with a guard hook, kit-only templates
  and scripts, and two lifecycle rules in `check_specs.py` (rules 1, 6 to 9, 14 to 16, 19 to 24).
- `start` is a drafting skill that refuses to run before `init`/`adopt`, writes two files, edits no verbatim file (rules 2 to 5).
- The architect is a full session started with `claude --agent architect`; the file enforces a tool list and a path and command guard, and
  the spec says plainly what it cannot enforce (rules 6 to 9, 12).
- The verdict, the ruling shape and the decisions-log convention (`Q-... ruled`) are one convention in three places (rules 10, 11).
- Templates are closed in what they may contain: a closed set of placeholders, no typed pull request, ADR or requirement number, no
  `gh pr view` (rules 14 to 17).
- Merged-before-cleared stays a reporting field; nothing blocks (rule 18).
- `ruleset` is add-only, idempotent and two-phase, with the plan computed by a credential-free script and applied by the person's `gh` (rules 19 to 22).
- The lifecycle checks go into `check_specs.py` with explicit exemptions and a precise definition of "open" (rules 23 to 26).
- Criterion g is proved on a second fresh fork, with the record in the fork and the outcome here (rule 28).

## Options compared

| Question | Option taken | Not taken, and why |
| --- | --- | --- |
| Architect as | a project agent file started with `--agent`, plus a fallback skill | a plugin agent (ignores `hooks`; SPEC-0005 rule 7: the plugin ships none); only a skill (no tool restriction at all) |
| Guard | a `PreToolUse` hook scoped in the agent's frontmatter | project-wide deny rules (they would restrict the implementation session too); a skill instruction (not enforced) |
| `start` and ADR-0001 | the next free ADR as the charter, ADR-0001 untouched | rewriting ADR-0001 (it exists, is Accepted in targets and records the ruleset); a second ruleset text |
| `principles.md` | not edited | edited with marked lines (the doctor compares the file with the kit and would report `vendored-differs`) |
| Merged before cleared | the existing metrics field plus a report line | a drift finding (the audit reads the repository, not pull requests, and D7 is taken by SPEC-0010); a blocking check (a verdict is a person's act) |
| Ruleset application | a credential-free plan script and the person's `gh` | a script that holds a token (SPEC-0005 rule 11); a GitHub App (a stored secret) |
| Ruleset change | add-only, stricter left alone, looser reported | replace to the kit's values (it could weaken a stricter ruleset); never touch an existing ruleset (no migration for the pilot) |
| Proof g | a second fresh fork | the pilot fork reset to upstream (loses the records criteria a, c, d need) |
| Lifecycle (a) | in `check_specs.py` with `--body` | in `check_pr_body.py` (the body check does not read specs; the brief names `check_specs`) |
| Lifecycle (b) | the narrow definition of open | any mention counts (flags SPEC-0002 and SPEC-0011 for example ids) |

## Questions raised (all ruled; see Rulings)

| Q | Question | Reading taken in the spec |
| --- | --- | --- |
| Q-K4-80 | Does `/agk:start` call `init`/`adopt`, or refuse until they have run? | refuses, with the instruction (rule 2) |
| Q-K4-81 | The brief says `docs/vision.md`; the kit has `constitution/vision.md`. | the kit's path (rule 4) |
| Q-K4-82 | The brief says `principles.md` "from the kit's template, with project-specific lines marked". | not edited; project rules in the vision, marked (rule 4) |
| Q-K4-83 | The brief says `ADR-0001` (milestones, non-goals, the ruleset). ADR-0001 exists and records the ruleset. | the next free ADR as a "project charter" with milestones, non-goals and done-means; the ruleset is cited (rule 4) |
| Q-K4-84 | Like the intake skill, `start` stops before the commit because of SPEC-0005 rules 8 and 10. | yes (rule 3); the same amendment as Q-K4-61 would let both commit |
| Q-K4-85 | `/agk:architect` cannot switch a running session into an agent. | the primary form is `claude --agent architect`; the skill is a fallback and says its restrictions are not enforced (rule 7) |
| Q-K4-86 | May the architect run the pull request's checks? Running them runs the pull request's code. | no: it reads CI results through `gh api` GET (rule 8) |
| Q-K4-87 | The guard's allowed paths and commands. | the lists in rule 9; frontmatter hooks need a trusted folder and are `(verify)` |
| Q-K4-88 | The architect posts comments with `gh api --method POST`: a writer outside the working tree. The forbidden-verb tests cover skills, not agent files. | accepted for the architect, limited by the guard to issue comments (rule 9) |
| Q-K4-89 | The architect never posts `Verdict: cleared` on a pull request it authored. | a rule of the role (rule 8); not enforced by the guard |
| Q-K4-90 | The architect does not set `Approved`/`Accepted` except in a final commit a person orders. | rule 8 |
| Q-K4-91 | The brief calls the role "a session definition, not a subagent" but stores it in `.claude/agents/`. | the file is a subagent definition used as a main session through `--agent` (rule 6) |
| Q-K4-92 | Are the templates installed into targets? | no: kit-only, read from the plugin root; copied on request (rule 14) |
| Q-K4-93 | What "parses" means for a template. | the list in rule 15 (headings, closed placeholders, no typed numbers) |
| Q-K4-94 | `playbook.py brief` fills numbers and branch names; the architect writes the items. | rule 16 |
| Q-K4-95 | The kit `CLAUDE.md` gains one line naming `gh api .../pulls/{n}`. It is a verbatim, protected file. | yes (rule 17); needs an ADR and a kit bump at implementation |
| Q-K4-96 | Merged-before-cleared: which check? | the metrics field, plus a line in "At risk" by amendment of SPEC-0011; never blocks; no new drift finding (rule 18) |
| Q-K4-97 | `/agk:ruleset` is a second command that writes outside the working tree (SPEC-0005 rule 10 says only `/agk:issue` does). | accepted with an amendment (`proposed-spec-amendments-15.md` item 1) |
| Q-K4-98 | The token: the person's `gh` login only; no stored secret. | yes (rule 19) |
| Q-K4-99 | Add-only: a looser value is reported and changes only with `--tighten`. | rule 20 |
| Q-K4-100 | Criterion g on a second fresh fork or on the pilot fork reset? | a second fresh fork (rule 28) |
| Q-K4-101 | Phase detection: a successful run of `governance.yml` on the default branch. | rule 21; `(verify)` the runs endpoint's `status=success` filter and behaviour for a never-run required check |
| Q-K4-102 | The doctor in phase 1. | stays strict; only the printed fix of `required-check-governance` changes (rule 22) |
| Q-K4-103 | Lifecycle (a) in `check_specs.py` with `--body`; "implementation" means a path outside `docs/` and `.github/ISSUE_TEMPLATE/`. | rule 23 |
| Q-K4-104 | The exemption for a requirement no spec names and an ADR names. | rule 23; the analysis shows it is needed for 5 of 18 past implementation pull requests |
| Q-K4-105 | "Open question" = asked in a table row or list item and not ruled by a `## Rulings` row or a log row. | rule 24; 0 of 11 Approved specs fail |
| Q-K4-106 | Only specs whose Approved status line is added or changed in the diff are checked. | rule 24 |
| Q-K4-107 | Shared parsers `common.find_questions` and `common.next_free_ids`. | rule 25; the first changes SPEC-0009's implementation text (amendment item 2) |
| Q-K4-108 | Three new skills change the eight-skill assertions of SPEC-0005. | amendment item 1 |
| Q-K4-109 | Where the criterion g record lives. | the fork's own repository; one outcome line here (rule 28) |

## Rulings (maintainers, 2026-10-16)

The default ruling is that every reading the draft took is accepted (`Q-K4-80` to `Q-K4-109`), with the clarifications below. The spec is set
`Approved` on the maintainers' instruction. No question is open.

| Q | Ruling | Where in the spec |
| --- | --- | --- |
| Q-K4-80 ruled | accepted: `/agk:start` refuses until `init`/`adopt` have run | rule 2 |
| Q-K4-81 ruled | accepted: the kit's path `constitution/vision.md` | rule 4 |
| Q-K4-82 ruled | accepted: `principles.md` not edited; project rules in the vision, marked | rule 4 |
| Q-K4-83 ruled | accepted: the next free ADR as a project charter; the ruleset is cited | rule 4 |
| Q-K4-84 ruled | accepted as **no**, as `Q-K4-61`: skills never commit, push or open a pull request; the script prints the commands and the body and the session runs them under its `CLAUDE.md`. The amendment item that would let skills commit is **withdrawn** (it is deleted from `proposed-spec-amendments-14.md`; see the notes of SPEC-0012) | rule 3 |
| Q-K4-85 ruled | accepted: `claude --agent architect` is primary; the skill is a fallback that says its restrictions are not enforced | rule 7 |
| Q-K4-86 ruled | accepted: the architect reads CI results through `gh api` GET and does not run the pull request's code | rule 8 |
| Q-K4-87 ruled | accepted: the guard's lists; frontmatter hooks `(verify)` | rule 9 |
| Q-K4-88 ruled | accepted: the architect posts issue comments only, limited by the guard | rule 9 |
| Q-K4-89 ruled | accepted **as a role rule** (not enforced by the guard) **plus a residual**: a deterministic check that the author of a `Verdict: cleared` comment is not the author of the cleared commit, due 2027-01-31 (K5) | rule 8; Residual |
| Q-K4-90 ruled | accepted: no `Approved`/`Accepted` except in a final commit a person orders | rule 8 |
| Q-K4-91 ruled | accepted: the file is a subagent definition used as a main session through `--agent` | rule 6 |
| Q-K4-92 ruled | accepted: templates kit-only, copied on request | rule 14 |
| Q-K4-93 ruled | accepted: what "parses" means | rule 15 |
| Q-K4-94 ruled | accepted: `playbook.py brief` fills numbers and branch names | rule 16 |
| Q-K4-95 ruled | accepted: the one `CLAUDE.md` line; ADR and kit bump at implementation | rule 17 |
| Q-K4-96 ruled | accepted: the metrics field plus an "At risk" line by amendment; never blocks; no new drift finding | rule 18; amendments-15 item 3 |
| Q-K4-97 ruled | accepted: `/agk:ruleset` is the second command that writes outside the working tree; the founder asked for it. The amendment (`proposed-spec-amendments-15.md` item 1) is **applied at implementation**, by the ADR of the SPEC-0013 implementation pull request, **not on the merge of these specs** (as `Q-K4-52`) | rule 19; amendments-15 item 1 |
| Q-K4-98 ruled | accepted: the person's `gh` login only; no stored secret | rule 19 |
| Q-K4-99 ruled | accepted: add-only; a looser value is reported and changes only with `--tighten` | rule 20 |
| Q-K4-100 ruled | accepted: a **second fresh fork**; the maintainers pick its upstream at proof time; it need not be in a third language; the date for criterion g stays the K4 date, the pilot's first week, 2026-12-01 | rule 28 |
| Q-K4-101 ruled | accepted **with the `(verify)`**: the implementation proves on the sandbox repository what GitHub does for a required check that has never run, before relying on phase detection, and records it | rule 21; Residual |
| Q-K4-102 ruled | accepted: the doctor stays strict in phase 1; only the printed fix changes | rule 22; amendments-15 item 4 |
| Q-K4-103 ruled | accepted: lifecycle (a) in `check_specs.py` with `--body` | rule 23 |
| Q-K4-104 ruled | accepted: the exemption for a requirement no spec names and an ADR names | rule 23 |
| Q-K4-105 ruled | accepted: the narrow definition of an open question | rule 24 |
| Q-K4-106 ruled | accepted: only specs whose Approved status line is added or changed are checked | rule 24 |
| Q-K4-107 ruled | accepted: shared parsers `common.find_questions` and `common.next_free_ids`. The SPEC-0009 amendment (`proposed-spec-amendments-15.md` item 2) is **applied at implementation** by the ADR of the SPEC-0013 implementation pull request | rule 25; amendments-15 item 2 |
| Q-K4-108 ruled | accepted: three new skills; the SPEC-0005 amendment (item 1) is **applied at implementation** by the same ADR, as `Q-K4-97` | rule 27; amendments-15 item 1 |
| Q-K4-109 ruled | accepted: the criterion g record lives in the fork; one outcome line here | rule 28 |

**Amendments.** `proposed-spec-amendments-15.md` keeps its five items, none applied by this pull request. Applied **at implementation** by the ADR of
the SPEC-0013 implementation pull request: item 1 (SPEC-0005, three skills; `/agk:ruleset` the second outside writer), item 2 (SPEC-0009, the
`questions` row), item 3 (SPEC-0011, the merged-before-cleared line), item 4 (SPEC-0006, the printed fix) and item 5 (SPEC-0001 and SPEC-0002, one
printed line). The commit amendment of `proposed-spec-amendments-14.md` is withdrawn (`Q-K4-84`, `Q-K4-61`); that file is edited by the SPEC-0012 pull request.

**The merged-before-cleared baseline.** The pull requests that the metrics field `merged_head_cleared` already reports are **#45** and **#50**
(`no`: the verdict names an earlier head) and **#46** (`unknown`: no verdict line). They are the baseline; no retroactive action is taken.

## Sibling specs touched (amendments in `docs/runs/proposed-spec-amendments-15.md`, applied at implementation, none by this pull request)

SPEC-0005 (three skills; `/agk:ruleset` as a second outside writer), SPEC-0009 (the questions parser is shared), SPEC-0011 ("At risk" gains
a merged-before-cleared line), SPEC-0006 (the printed fix of one check), SPEC-0001 and SPEC-0002 (one printed line). This pull request edits
none of those files.

## Proof plan

Criterion g (rule 28): a second fresh fork, a written problem statement, the sequence of rule 1, a record in the fork naming each step and the
file or comment it produced. The maintainers choose the upstream, create the fork, write the statement, merge and decide; the sessions
run the steps; the agent of this repository records the outcome only. The mechanical parts (templates, `check-start`, the guard table,
`ruleset.py` plans, the lifecycle checks) are tested without a model or the network (rules 27, 26).

## Decisions-log rows (for the maintainers' log; not edited in this pull request)

| Date | Decision | Reason | Recorded in | By |
| --- | --- | --- | --- | --- |
| 2026-10-16 | SPEC-0013 playbook Approved (drafted: `/agk:start`, the architect role as a project agent file started with `claude --agent architect` and a guard hook, kit-only templates and scripts, `/agk:ruleset` (add-only, two-phase), two lifecycle checks in `check_specs.py`, criterion g on a second fresh fork with the record in the fork) | REQ-020; ADR-0021 decision 2 and 5g | `docs/specs/0013-playbook.md` | agent |
| 2026-10-16 | Q-K4-80 to Q-K4-109 ruled: every reading of the draft accepted; Q-K4-84 no (skills never commit); Q-K4-89 role rule plus a residual (author check, due 2027-01-31, K5); Q-K4-97, Q-K4-107, Q-K4-108 amendments-15 items 1 and 2 applied at implementation by the SPEC-0013 implementation ADR; Q-K4-100 second fresh fork, upstream picked at proof time, criterion g date 2026-12-01; Q-K4-101 accepted with `(verify)`, proven on the sandbox first | maintainers' rulings of 2026-10-16 | `docs/runs/spec-0013-notes.md` (Rulings), `docs/specs/0013-playbook.md` | reviewer |
