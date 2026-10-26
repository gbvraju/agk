# Proposed spec amendments 80 (SPEC-0007; REQ-039)

Date: 2026-10-26 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0144. The path: `docs/specs/0007-metrics.md`.

1. **SPEC-0007 rule 13, governance on an edited description.** The first step of the partial run (`full_run.py`) lets the partial run decide when the latest full run of the head failed only in steps that read the body (the body file, the states of the pull requests, `check_specs`, `check_pr_mode` and the body shape): it prints `jobs <run id>` and exits 4, the workflow makes one more `GET` of `actions/runs/<id>/jobs`, and the script, called again with `--jobs`, passes when every failed step has the conclusion `failure` and is one of those steps. Any other failed step, a cancelled step, a run that was cancelled and an unreadable response still fail.
