# Proposed spec amendments 105 (SPEC-0007; REQ-016)

Date: 2026-11-01 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for ADR-0239
(brief #447), which stays `Proposed` for the maintainers' decision. The path: `docs/specs/0007-metrics.md`. The number 105 is
the next free one. It needs a person's `Approve: SPEC-0007`; no session posts it. It records in the spec what `metrics.py` already
does since brief #427 (ADR-0232, Q-427-5); nothing in the script changes with it.

1. **SPEC-0007 rule 14, body shape**, gains, after "with the fields of rules 2 to 9 as columns": "and, after `tests_after` and
   before the CI fields of ADR-0209, the two columns `project_test_seconds` (the whole seconds of the `Project tests` step of
   the last governance run of the head that ran it) and `proof_seconds` (the whole seconds of the last `proof` job of the head
   that ran), each `unknown` when it cannot be read and `-` for a pull request closed unmerged", and gains, after the
   `closed in window: N; recorded: N; unknown cells: N` line: "then the line
   `backstop escapes: <n> (#<pr> <merge sha>, ...); red pushes not escapes: <n> (...); unknown: <n> (#<pr>, ...)`, where an
   escape is a failed governance run on the push of the merge commit to the base branch after the head's last proof job ended
   `proven` and its latest governance run ended `success`, then the line
   `over budget (budget_seconds <b>): <n> (#<pr> run <id> <s>s, ...); unknown: <k>`, each governance run of the window's pull
   requests (their commits and, when merged, the push of the merge commit) whose `Project tests` step took longer than
   `[testing] budget_seconds` (300 when unset), once each; a refused setting gives `over budget: unknown (<refusal>)`, naming
   the setting."
2. **SPEC-0007 rule 20, fixtures**, gains, after the list of saved responses: "and, for the columns and lines of rule 14 from
   brief #427, the run responses `runs-SHA.json` and `run-jobs-ID.json`", and gains, at the end of its cases: "the seconds of the
   last run that ran the step or the job; a step that cannot be read, that never ran, or whose runs cannot be read (`unknown`);
   a pull request closed unmerged (`-`); one escape and one red push that is not one; a red push after a failed governance run
   (not an escape); a green push; an escape that cannot be read; a red run of another branch or event (not a push); a run over
   the default budget; a budget read from the `[testing]` table; runs whose steps cannot be read (counted `unknown`); a bad
   budget setting (named, never guessed); and nothing in these lines blocks." The cases are those of
   `tests/kit/test_metrics_testing.py`, which builds them in `tmp_path` from the `files` fixture.
