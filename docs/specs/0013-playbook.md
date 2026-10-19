# SPEC-0013: playbook (the method this kit was built with, as kit files)

- Status: Approved
- Owner: maintainers
- Requirements: REQ-020 (AC1, AC2, AC3)

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.
This is the fifth and last of the K4 specs of ADR-0021 (decision 2) and serves exit criterion g. It packages what SPEC-0009 to SPEC-0012
prove: the method of an architect session that writes decisions and reviews, an implementation session that builds and stops, and a person
who decides and merges. The points `Q-K4-80` to `Q-K4-109` are in `docs/runs/spec-0013-notes.md`; all are ruled (section Rulings) and the spec is set `Approved` on the maintainers' instruction of 2026-10-16. Claude Code and GitHub
facts not reconfirmed are marked `(verify)`. The repository facts quoted here were read on 2026-10-16 (`docs/runs/spec-0013-notes.md`).

## Rules

### The sequence

1. **The sequence of the playbook.** From a repository (a new one, or a fork) and a written problem statement:
   (1) `/agk:adopt` or `/agk:init` installs the kit (SPEC-0001, SPEC-0002); (2) `/agk:ruleset` phase 1 protects the default branch (rule 19);
   (3) `/agk:start "<problem statement>"` drafts the vision and the project charter for a person to approve by merging (rules 2 to 5);
   (4) the architect session (rules 6 to 13) writes the first spec and a brief, each merged by the person; (5) an implementation session builds
   from the brief in one pull request and stops; (6) the architect session reviews that pull request against the Approved text and posts the
   verdict; (7) the person merges; (8) `/agk:ruleset` phase 2 requires `governance` once it has run on the default branch (rule 19). Every
   decision in this sequence is a file or a comment in the repository itself, never in a chat.
2. **Which runs first.** `/agk:init` or `/agk:adopt` runs first. `/agk:start` refuses, with the instruction "run `/agk:init` or `/agk:adopt`
   first", when `agk.toml` is absent; it does not call either of them and installs nothing.

### `/agk:start`

3. **The form.** `/agk:start "<problem statement>"`: a quoted plain-language statement of at most 1,500 characters, in one or more
   paragraphs. A user-invoked skill, never invoked by the model on its own (SPEC-0005 rule 9). It stops before the commit, like SPEC-0012
   rule 13: the script `python3 ".../playbook.py" next-steps` prints the commit message, the push command and a pull request body.
4. **What it writes.** On a new branch `start/<slug>` from `origin/<default branch>`, exactly two files: (1) `constitution/vision.md`, the
   installed template (`TODO(maintainers)` placeholder) replaced by text with the headings `## What this is for`, `## Who it serves`,
   `## How success is measured`, `## Out of scope` and, optionally, `## Project rules` (every line there marked `<!-- project-specific -->`);
   (2) the project charter ADR `docs/adr/<next free>-project-charter.md` (`Status: Proposed`, the date from `date -u`) whose Decision
   has numbered items headed **Milestones** (each with a measurable exit criterion), **Non-goals** and **Done means**, and a `Protected
   classes:` line naming `constitution/`. `constitution/principles.md` is not edited: it is a verbatim file that the doctor compares with
   the kit's copy; project-specific rules go in `## Project rules` of the vision. The ruleset is not rewritten: the ADR-0001 that
   init or adopt installed already records it, and the charter cites it.
5. **The checks.** `python3 ".../playbook.py" check-start [--base REF]` fails with a message that names the rule, never the text:
   the two files are the whole difference from the base; the vision has no `TODO(maintainers)` and has the four headings; every line
   under `## Project rules` carries the marker; the ADR passes `check_adrs`, is `Proposed`, has the three headed items, each milestone
   line has the words `exit:` and a measurable statement (a digit, or `all`, `every`, `none`, `zero`), and its number is the next free
   number read from `origin/<default branch>` by `common.next_free_ids` (rule 25); `constitution/principles.md` is byte-identical to the base.
   Then `make governance`. At most three correction rounds. The model writes the vision and the charter; nothing else.
   What the checks cannot check: that the milestones are the right ones, which is the person's merge.

### The architect role

6. **A session, not a subagent.** The architect is a role for a full session with the repository's context. It is defined by
   `.claude/agents/architect.md` (installed, verbatim, class `.claude/`) and started with `claude --agent architect`, which runs the main
   thread under that definition (read in the Claude Code documentation on 2026-10-16; the flag and the frontmatter fields are
   `(verify)` again at implementation). The experimental reviewer (ADR-0020) is unrelated and stays experimental.
7. **The skill.** `/agk:architect` (a plugin skill, user-invoked) prints how to start the session with `claude --agent architect`, checks
   the prerequisites read-only (`agk.toml` present, `gh auth status`, the default branch) and, in a session that could not be started that
   way, loads the same instructions into the current session and says plainly that the tool list and the guard of rule 9 are **not**
   enforced in that session (Q-K4-85).
8. **What the role does.** It (a) writes ADRs, specs, briefs, rulings and decisions-log rows as files, each on a branch and in a pull
   request that a person reviews and merges; (b) reviews every pull request of the implementation session against the Approved text,
   by reading the pull request, its diff and the CI results through `gh api` GET, without executing the pull request's code (Q-K4-86);
   (c) posts the verdict as a comment (rule 11); (d) records every decision in the repository: a `## Rulings` table in the notes file with
   a row for each `Q-` id, and a decisions-log row that names the id and says `ruled`; (e) never writes code it reviews: it writes no
   file outside `docs/` and `constitution/vision.md` (rule 9); (f) never merges, never enables auto-merge, never posts
   `Verdict: cleared` on a pull request it authored (a person reviews those), and never sets a spec `Approved` or an ADR `Accepted`
   except in a final commit that a person orders in the pull request.
9. **What the role file can enforce, and what only a person can.** *The file enforces:* the tool list (`tools:` is `Read, Grep, Glob, Edit,
   Write, Bash`); a `PreToolUse` guard hook (`.claude/hooks/architect_guard.py`, declared in the agent's frontmatter `hooks`, which a
   project subagent may carry and which needs a trusted folder, `(verify)`) that denies `Edit` and `Write` outside `docs/` and
   `constitution/vision.md`, and denies `Bash` unless the command is one of: a read-only `git` command, `gh api` with `--method GET` or
   no method, `gh api --method POST` to `repos/{o}/{r}/issues/{n}/comments`, `make governance`, or a script of `scripts/agk/` that
   the kit lists as read-only; and the project's deny rules (no merge, no force push). A test runs the guard with a table of commands and
   paths. *Only a person can supply:* attention; that every pull request is in fact brought to the architect; that a verdict is right;
   that the Approved text itself is good. Criterion g measures the package, not the person (ADR-0021 consequences). The check of rule 18
   shows the gaps afterwards; it prevents none.
10. **The decision records.** The role records a ruling in three places, the same shape for every question: the notes file's `## Rulings`
    table (a row that starts with the id), the decisions-log row (`Q-K4-1 ruled: ...`), and the spec or ADR text that the ruling changes.
    A question that has a row in the notes' `## Questions` table and none in `## Rulings` is open.
11. **The verdict convention, exactly.** The first line of the comment is `Verdict: cleared <sha>`, `Verdict: fix list` or `Verdict: rejected`,
    with `<sha>` at least 7 hex characters of the pull request's head at review time (the rule of `metrics.VERDICT`). No text follows on
    that line. A later commit needs a new `Verdict: cleared <new sha>` line. The findings, if any, follow the first line after a blank line.
    A test fills `kit/templates/playbook/verdict.md` and shows that its first line matches `metrics.VERDICT`.
12. **Not a reviewer agent.** The role posts what a person-supervised session concluded; it does not claim to catch defects. The count
    of findings it misses is not measured by this kit (ADR-0021 decision 6: no model judges code quality); the human findings are recorded
    in `kit/templates/playbook/held-out-findings.md` form before the role sees them, when a measurement is wanted.
13. **Roles in a sequence.** The implementation session works from a brief, one pull request per item, checks the state of its pull
    request before each push, and stops; it never decides. The architect decides nothing the person has not approved by merging. The
    person decides and merges. (These are the rules of this repository's `CLAUDE.md`; the playbook installs them, it does not
    restate them.)

### The templates

14. **Where.** `kit/templates/playbook/` (kit-only, read from the plugin root by `/agk:architect`, which copies a template into the
    working tree only when asked). The files, each checked by a test that it exists and parses (rule 15):
    `brief-overnight.md`, `brief-day.md`, `rulings-table.md`, `verdict.md`, `live-proof-plan.md`, `held-out-findings.md`,
    `pilot-week-record.md` (the record of one weekly product report, SPEC-0011 rules 19 and 20).
15. **What parses means.** For each template the test checks: the file is UTF-8 Markdown; the required headings are present and in order;
    the only placeholders are from the closed set `{{repo}}`, `{{default_branch}}`, `{{next_req}}`, `{{next_adr}}`, `{{next_spec}}`,
    `{{branch_prefix}}`, `{{date}}`, `{{sha}}`, `{{n}}`; and none contains a literal `PR #<digits>`, `ADR-<digits>`, `REQ-<digits>` or
    `gh pr view`. Required headings: briefs: `## Rules block`, `## Items`, `## Report format`; the rules block contains the three
    sentences "Never merge.", "Never poll CI." and "Check the state of your pull request before every push." and the command
    `gh api repos/{{repo}}/pulls/{{n}}`; `rulings-table.md`: a table with the columns `Q`, `Ruling`, `Where`; `verdict.md`: the three
    first-line forms of rule 11; `live-proof-plan.md`: `## Preconditions`, `## Steps` (a table with columns `Step`, `Command`, `Expected`,
    `Recorded in`), `## Restore`, `## Result`; `held-out-findings.md`: a table with the columns `#`, `PR`, `Commit`, `Finding`, `Recorded on`,
    `Seen by a reviewer agent`; `pilot-week-record.md`: `## Week`, `## Answers from the report alone`, `## Marks`, `## Score`.
16. **Briefs name branches and read the numbers.** `python3 ".../playbook.py" brief --kind overnight|day --branch-prefix <p>` prints a brief
    skeleton in which `{{next_adr}}`, `{{next_req}}` and `{{next_spec}}` are the next free numbers read from `origin/<default branch>` by
    `common.next_free_ids` (rule 25), `{{repo}}` and `{{default_branch}}` come from `agk.toml` and `origin`, and branch names are `<p>/<slug>` for
    each item; a pull request number is never written in advance (the pilot's first brief said "PR #2" and "0002"; both were taken).
    The architect writes only the items.
17. **State of a pull request: GET, not GraphQL.** The kit's `CLAUDE.md` (verbatim, class `CLAUDE.md`) gains one line: "Check the state
    of a pull request with `gh api repos/{owner}/{repo}/pulls/{n}` (a GET); the GraphQL form of the command is blocked in cloud sessions."
    (Amended: the first wording named `gh pr view` and so failed the test below; `docs/runs/proposed-spec-amendments-24.md`.)
    A test fails if `gh pr view` appears in `CLAUDE.md`, in a template of rule 14, in a skill, in `.claude/agents/` or in a workflow. It
    does not appear in any of them today.
18. **Merged before cleared: reported, never blocked.** The metrics field `merged_head_cleared` (SPEC-0007 rule 8) already says, for each
    closed pull request, `yes`, `no` or `unknown` (a merged head is cleared when a `Verdict: cleared <sha>` comment names it). That field
    is the deterministic check; it reports after the fact in the week's metrics issue and blocks nothing. No new drift finding is
    added. The product report (SPEC-0011) lists such pull requests under "At risk" by the amendment in
    `docs/runs/proposed-spec-amendments-15.md` item 3, derived from the facts' `head` and `verdicts` of each merged pull request.

### `/agk:ruleset`

19. **The command.** `/agk:ruleset` is a user-invoked skill that applies the kit's ruleset and repository settings through the REST API
    with the caller's own `gh` login (the only credential, none stored), when the caller has admin rights on the repository. Without admin
    rights, without `gh`, or unauthenticated, it prints the exact text of the ruleset (from `kit/templates/branch-rules.txt`) and the
    path in the settings (`Settings > Rules > Rulesets`, and `Settings > General` for the two repository settings, `(verify)`), and does
    nothing else (exit 4). The kit-only script `python3 ".../ruleset.py" plan [--phase 1|2|auto] [--repo O/R] [--api-dir DIR]` reads with
    `gh api` GET (the repository, its rulesets and their detail, the runs of `governance.yml` on the default branch) and prints the plan;
    it writes nothing and holds no credential. The skill shows the plan (`--dry-run` is the default), asks, and only then runs the
    `gh api --method POST|PUT|PATCH --input FILE` commands that the plan prints, from payload files in a temporary directory.
20. **Rules of the plan.** *Idempotent:* after it is applied, a new plan is empty (`nothing to do`). *Add-only:* it creates the ruleset when
    none matches, and adds a missing rule or sets a missing repository setting; it never removes a rule, a setting or a bypass actor, and
    never loosens a value; a value stricter than the kit's (for example one required approval) is left as it is; a value looser than the
    kit's or a bypass actor is **reported** as a finding with its fix, and changes only with the flag `--tighten`, which the skill
    never passes on its own. *The ruleset* is the elements of ADR-0001 decision 3: active; no bypass actors; target `~DEFAULT_BRANCH`;
    restrict deletions; require linear history; require a pull request (0 approvals, dismiss stale approvals on push, `squash` the only
    allowed method); block force pushes; and, in phase 2, the required status check `governance`. *The repository settings:*
    `allow_auto_merge` and `delete_branch_on_merge` on. The desired ruleset is the file `kit/templates/ruleset.json` (kit-only).
21. **Two phases.** *Phase 1,* at adopt: every element above except the required status check. *Phase 2:* once the workflow `governance`
    has completed successfully at least once on the default branch (`GET repos/{o}/{r}/actions/workflows/governance.yml/runs` for
    the default branch with `status=success` returns one run or more), the plan adds the `required_status_checks` rule with the context
    `governance`. `--phase auto` (the default) picks the phase from that read. The reason is the first merge: a check that has never run
    cannot be required without blocking the pull request that is meant to produce it (`(verify)` against current GitHub behaviour:
    whether a required context that has never reported blocks a merge; the pilot's first day reported that it does). Before relying on
    phase detection, the implementation proves on the sandbox repository what GitHub does for a required check that has never run, and
    records the result (`Q-K4-101`).
22. **The doctor, by amendment at implementation.** The doctor (SPEC-0006) verifies the result. In phase 1 it correctly reports
    `required-check-governance` as failing; the printed fix of that check changes to name `/agk:ruleset` (phase 2). No check id is
    added or removed; `docs/runs/proposed-spec-amendments-15.md` item 4 has the text. `init` and `adopt` print one line pointing to
    `/agk:ruleset`; the branch-rules text they print stays.

### The lifecycle as checks

23. **An implementation pull request advances an Approved spec.** `check_specs.py` gains `--body FILE|-` (the governance job already
    passes the pull request body to the "PR body shape" step; it passes it here too). For a pull request whose diff touches any path
    outside `docs/` and `.github/ISSUE_TEMPLATE/` (an *implementation* pull request), each `REQ-nnn` on its `Advances:` line must be
    named by the `Requirements:` line of a spec whose `Status` is `Approved` at the head; otherwise `FAIL specs: REQ-nnn: no Approved spec
    names it`. A requirement that **no spec names** and that **an ADR names** (any status) is exempt: it predates specs. Without a
    body (outside CI) the rule prints a notice and is skipped, as the other diff checks. Docs-only pull requests are not checked.
24. **A spec is not Approved with an open question.** `check_specs.py` fails a spec whose `Status` is `Approved` at the head and whose
    status line is added or changed in the diff when it has an open `Q-` id: an id that *starts a table row or a list item* in the spec
    or in its notes file (`| Q-...` or `- Q-...`) and has neither a row starting with that id in the notes' `## Rulings` section nor a
    decisions-log row containing `<id> ruled`. Message: `FAIL specs: SPEC-nnnn: Q-... has no ruling`. Specs already Approved, unchanged
    in the diff, are not re-checked. An intake spec's `Q-S<spec>-<n>` ids in `## Open questions` (SPEC-0012 rule 10) count.
25. **Shared parser.** The ids and their state are found by `common.find_questions(root)`, extracted from the place where SPEC-0009's
    `questions` section would parse them, so that `facts.py` and `check_specs.py` read the same thing; and the next free numbers by
    `common.next_free_ids(root, ref)` (SPEC-0012 rule 2). A behaviour-preserving test shows `facts.py`'s `questions` unchanged.
26. **Fixtures.** `tests/kit/` (installed): repositories built in `tmp_path` for rule 23 (a docs-only pull request with `Advances:`; an
    implementation pull request that advances a requirement named by an Approved spec; by a Draft spec only; by no spec and an ADR; by
    no spec and no ADR; two requirements, one failing) and for rule 24 (Approved with an open id; with a `## Rulings` row; with a
    decisions-log row; a mention of an id in prose, which is not asked; a spec unchanged and already Approved). No test uses the network.

### Tests and proof

27. **Tests.** Kit-only (`tests/kit_dev/`): `test_playbook.py` (the templates of rules 14, 15, 17; `brief` fills the numbers and writes no
    literal pull request or ADR number; `check-start` over a good start and each failing case; the sentence of the architect file; the
    verdict template; the guard's command and path table), `test_ruleset.py` (recorded API fixtures: no ruleset; phase 1; phase 2;
    idempotence; add-only with a stricter value left alone, a looser value reported, a bypass actor reported; `--tighten`; no admin;
    no `gh`). Installed (`tests/kit/`): rules 23 to 26. The plugin's skill-count and forbidden-verb tests (SPEC-0005 rules 10 and 19) gain
    the skills `start`, `architect` and `ruleset` by the amendment in `docs/runs/proposed-spec-amendments-15.md` item 1.
28. **Proof of criterion g (the maintainers and sessions together; not done in this pull request).** A fresh fork of a small public
    repository is taken from a written problem statement to its first governed merged pull request with a `Verdict: cleared` line,
    using only the playbook (ADR-0021 decision 5g; decision 7 allows a second fresh fork or the same fork reset to upstream).
    **Which:** a second fresh fork (`Q-K4-100`); the maintainers pick its upstream at proof time, and it need not be in a third language;
    resetting the pilot fork would destroy the pilot's records that criteria a, c and d rely on.
    **The maintainers:** choose the upstream repository and create the fork; attach the sessions; write the problem statement
    (the one input); approve by merging; and decide. **The sessions:** run steps 1 to 7 of rule 1 in the fork's own sessions, under the
    fork's own `CLAUDE.md` and the playbook files, with no step taken from memory or from this repository's chat history; the architect
    session writes the spec, brief, rulings and verdict, and the implementation session builds and stops. **The record:** a file in the
    **fork's own repository**, `docs/runs/playbook-proof.md`, committed through a pull request, names each step of rule 1, the command or
    skill used, and the file or comment it produced (a link); this repository's `docs/runs/` records the outcome only, with the fork
    unnamed: met or not met, the date, and a link. A step done from memory, or a decision with no file or comment, makes the criterion not met.
    The date for criterion g stays the K4 date: the pilot's first week, 2026-12-01 (`Q-K4-100`).
29. **Installed files and classes.** Installed (verbatim): `.claude/agents/architect.md`, `.claude/hooks/architect_guard.py`, `CLAUDE.md`
    (one line), `scripts/agk/check_specs.py`, `scripts/agk/common.py`, the installed tests of rules 23 to 26. Plugin: `skills/start/SKILL.md`,
    `skills/architect/SKILL.md`, `skills/ruleset/SKILL.md`. Kit-only: `scripts/agk/playbook.py`, `scripts/agk/ruleset.py`,
    `kit/templates/playbook/`, `kit/templates/ruleset.json`, `tests/kit_dev/`. The classes touched are `.claude/`, `CLAUDE.md`,
    `scripts/agk/`, `skills/`, `tests/kit/`, `tests/kit_dev/` and `kit/`; the implementation pull request carries an ADR that names each.
    The kit version is bumped. `init` and `adopt` print one line pointing to `/agk:ruleset` (rule 22).
30. **Order.** Built last (ADR-0021 decision 7: intake and playbook by 2026-11-30), after SPEC-0012, whose id allocation it reuses.

## Tests

- Rules 1 to 5, 14 to 17, 27 (kit-only tests): `tests/kit_dev/test_playbook.py`, marker `REQ-020 AC1`.
- Rules 6 to 13 (the role file, the guard, the verdict template): the same file, marker `REQ-020 AC1`.
- Rules 19 to 22: `tests/kit_dev/test_ruleset.py`, marker `REQ-020 AC1`.
- Rules 23 to 26: `tests/kit/test_check_specs_lifecycle.py`, marker `REQ-020 AC1`; rule 18: the metrics fixtures of SPEC-0007, marker `REQ-020 AC2`.
- Rule 28: a record in the fork's repository and one line here, checked by the maintainers, not by a test (markers `REQ-020 AC1`, `REQ-020 AC2`,
  `REQ-020 AC3`).

## Proof

ADR-0021 exit criterion g: *the pilot fork is set up and run **using only the playbook**: from a written problem statement, through `/agk:start`,
the architect session, `/agk:init` or `/agk:adopt`, one Approved spec and one brief, to its first governed merged pull request with a
`Verdict: cleared` line, with every decision recorded in the pilot's own repository and no step taken from memory or from this repository's
chat history. The record names each step and the file or comment it produced.* Rules 1 to 13, 28 (REQ-020 AC1 to AC3).

## Residual

- 2026-10-16: the guard hook limits writes by path and `Bash` by command pattern; a determined session can still misuse an allowed `gh api`
  GET. The playbook is a discipline made visible, not a sandbox (due 2027-01-31).
- 2026-10-16: nothing makes the architect session review every pull request; `merged_head_cleared` shows the misses after the fact (due 2026-12-31).
- 2026-10-16: the `claude --agent` flag and the frontmatter `hooks` of a project subagent are read from the documentation of 2026-10-16 and are
  `(verify)` again when the role is built (due 2026-11-30).
- 2026-10-16: whether GitHub blocks a merge on a required check that has never reported is `(verify)` and decides how much phase 1 matters
  (due 2026-11-30).
- 2026-10-16: the rule that the architect never posts `Verdict: cleared` on a pull request it authored (rule 8) is a role rule that the guard does
  not enforce; a deterministic check that the author of a `Verdict: cleared` comment is not the author of the cleared commit is due
  2027-01-31 (K5) (`Q-K4-89`).
- 2026-10-16: the CODEOWNERS-markers fix in `adopt` (Q-PL-1) is a separate code pull request after these specs.
