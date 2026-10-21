# SPEC-0019: The weekly report publishes the facts it was rendered from

- Status: Approved
- Owner: reviewer group (a team from config/reviewers.yaml)
- Requirements: REQ-026

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.
Written by the intake of one sentence (SPEC-0012): "The weekly product report also publishes the facts document it was rendered from, as a downloadable file of the workflow run, so a reader outside the
repository can use the same numbers." It is the fourth item that ADR-0060 decision 4 allows before the friends launch. The maintainers answered three questions before it was written: "a reader outside the
repository" is a person or program that is not a checkout, reading with GitHub access to the repository (on a public repository anyone signed in, on a private one those who can read it), with no anonymous
download, no sharing mechanism and no new public place for a private repository; the artifact is the byte-identical `facts.json` the report was rendered from, with no filtering and no added fields, named
`agk-facts-<week>`, kept 90 days, and the artifact of the latest run for a week is the one used; the issue, its label, the report and the metrics workflow are unchanged with no new permission, and the issue is
written first, then the upload, which fails the run when the file is missing or empty, the issue already written staying.

## Rules

1. **One artifact per run.** After the step that writes the issue, the `product-report` workflow has a step that uploads the facts as a workflow artifact named `agk-facts-<week>`, `<week>` being the week label of
   the report (`2026-W42`, the label of the issue title; the first line of the report names it). The artifact holds one file, `facts.json`.
2. **The same file.** The file is the facts document that `product_report.py` read for that report, byte for byte: it is the path the workflow wrote with `facts.py`, uploaded as it is, not regenerated, filtered,
   renamed inside the artifact or given another field.
3. **The step.** The upload action is pinned by a full commit SHA with its tag in a comment, like the checkout (SPEC-0011 rule 17); the path is that one file and no pattern; `retention-days` is 90, stated in the
   workflow; `if-no-files-found` is `error`. The step comes after the step that writes the issue, and the week label reaches it from the report step as a step output (Q-S0019-2).
4. **A failed upload fails the run.** A missing or empty facts file, or an upload that errors, fails the run; the issue already written is not changed or removed. A run for which the issue could not be written does
   not upload (the earlier step failed).
5. **A re-run.** A re-run of the workflow for the same week produces the artifact again under the same name, and the artifact of the latest run is the one used; the upload replaces an artifact of that name in the
   same run and the workflow deletes no other artifact (Q-S0019-1).
6. **Access is GitHub's.** The artifact is readable by those who can read the repository's workflow runs: on a public repository anyone signed in to GitHub, on a private one those who can read it, and by the API
   with a token that can. There is no anonymous download, no sharing mechanism, no release, no page and no other place; the workflow publishes the file nowhere but as a workflow artifact.
7. **No new permission, no new write.** The `permissions` block is what SPEC-0011 rule 15 gave (`contents`, `pull-requests`, `checks` and `actions` read, `issues` write); the workflow commits and pushes nothing and
   writes nothing to the repository but the issue and the label as before.
8. **Nothing else changes.** `facts.py`, `product_report.py`, the report, the issue and its label, the inbox output and the metrics workflow are byte-identical to before. The workflow's header comment says the
   facts are also uploaded, and its "only writes" sentence names the artifact (SPEC-0011 rule 15 is amended for that).
9. **How it changes.** The workflow is a verbatim kit file, so the build is a kit change: a bump, the hashes, and an ADR that names the protected classes it touches. SPEC-0011 is Approved; the build changes it by an
   amendment file `docs/runs/proposed-spec-amendments-N.md`, applied by that ADR. The security guide's account of what each workflow may write gains a line for the artifact.
10. **The test.** A test reads the workflow file and fails when the upload step is missing, comes before the step that writes the issue, uploads anything but that one file, names the artifact otherwise than
    `agk-facts-<week>`, omits the 90-day retention or `if-no-files-found: error`, is not pinned by a full commit SHA, or when the permissions differ from rule 7. No network is used.

## Tests

- Rules 1 and 3: the workflow has one upload step, after the issue step, named from the week label, uploading `facts.json`; REQ-026 AC1.
- Rule 2: the path of the upload is the path the workflow wrote with `facts.py` and read with `product_report.py`; the workflow run against a stub `gh` and a fixture holds the same bytes in the uploaded path as in
  the report's input; REQ-026 AC2.
- Rule 3: order, a single file with no pattern, 90 days, `if-no-files-found: error`, a pinned SHA; REQ-026 AC3.
- Rule 4: the shell body run with the facts file removed before the upload: the upload step's condition is not skipped and the issue step's output is kept; the workflow fails when the file is missing; REQ-026 AC4.
- Rule 5: the upload step replaces an artifact of the same name and no step deletes an artifact; REQ-026 AC5.
- Rules 6 and 7: the permissions equal those of rule 7; no `git commit`, no `git push`, no step other than the upload publishes the file; REQ-026 AC6.
- Rule 6: the workflow has no release, page, gist or sharing step, and nothing makes the artifact public; REQ-026 AC7.
- Rule 8: the report, the inbox output and the metrics workflow equal those before the change; REQ-026 AC8.

## Proof

REQ-026 AC1 to AC3: *each weekly run keeps the facts it rendered.* Rules 1 to 3. REQ-026 AC4 and AC5: *a week cannot pass without its facts, and a re-run does not leave two.* Rules 4 and 5. REQ-026 AC6 and
AC7: *nothing new is written or opened.* Rules 6 and 7. REQ-026 AC8: *only the upload is new.* Rule 8. The first scheduled run after the build is merged shows the artifact on its run page, and the maintainers
download it and compare it with the report of that week.

## Residual

- 2026-10-21: the facts name pull request titles, requirement titles and file paths; on a private repository they are readable by everyone who can read the repository, which is the repository's own audience (due 2026-12-31).
- 2026-10-21: the artifact is kept 90 days and a reader who needs an older week has the metrics issue and the report issue only (due 2026-12-31).

## Open questions

- Q-S0019-1 What does the upload action do when the same run (a re-run attempt) uploads an artifact of a name that already exists? The criteria assume that setting the action's overwrite option replaces it
  and that nothing else is deleted. This is a behaviour of the upload action and is marked (verify) until the pinned version is read.
  **Ruled** (maintainers, 2026-10-21): as read. The upload step sets the action's overwrite option, so a re-run attempt of the same run replaces the artifact of that name; the workflow deletes nothing. A new run has its own artifact, and "the latest run" is chosen by the reader by run time. The overwrite behaviour is checked at the build against the README of the pinned version, which is quoted in the build's pull request.
- Q-S0019-2 Which version of the upload action is pinned, and how does the week label reach its step? The criteria assume a current major version of the upload action pinned by a full commit SHA that a person
  looks up when the build is made (no network in a check), and a step output written by the report step. The SHA is (verify).
  **Ruled** (maintainers, 2026-10-21): as read. The current major release of `actions/upload-artifact`, pinned by its full commit SHA with the tag in a comment, looked up at the build (`git ls-remote` on github.com/actions/upload-artifact is allowed) and shown in the build's pull request. The week label is a step output of the report step.
