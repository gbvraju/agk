---
name: design
description: Write the theme (the brand record and the design rules) and one static mockup of a product's first page from the kit's templates, for the owner to approve by a line. Writes files; never commits.
disable-model-invocation: true
argument-hint: "<mockup name, a lower-case slug> | inventory"
---

# /agk:design

`/agk:design <name>` writes `docs/design/theme.md` (when it does not exist yet) and the mockup folder
`docs/design/mockups/<date>-<name>/` with `index.html` (one static page: the tokens as one CSS block, a system font, no
script, no external request, placeholders in brackets) and `README.md`. Run it after the owner approved the vision.

An engine only drafts. If `[engines]` in `agk.toml` has a `design` key, it names a skill the session can see (`agk doctor`
reports it as present, absent or missing); use that skill to draft the brand record and the page. If the key is absent, use
the kit's template. Either way the text is written through the kit's template and passes `check_design.py`.
An engine never decides, never approves, and never edits a protected file by itself: the owner gives every brand value and its
source, and a value the owner did not give stays in brackets.

1. Fetch the default branch and make sure the work tree is clean; if it is not, stop and say so. Create the branch from the
   default branch, and write the files (the date comes from the clock, `date -u`):

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/design.py" write --name NAME [--theme-file DRAFT]
```

   `DRAFT` is the engine's draft of the theme, in the shape of the template (Brand with a source line per value, one token
   block, Contrast, Rules, Evidence). It is used only when `docs/design/theme.md` does not exist.
2. Fill the page and the brand record from what the owner gave, and from nothing else. A brand value without a source is
   not allowed; a value still unknown stays in brackets and is reported as at risk.
3. Take the screenshots when a headless browser exists (360 and 1280 px, light and dark); without one the script says so:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/design.py" screenshots --folder FOLDER
```

4. Check, and correct the files on a failure, at most three rounds, then stop and report:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/check_design.py"
```

   then run `make governance`. Both must pass. `design: the theme is not approved yet` is information, not a failure.
5. Last, say what the checks cannot check: that the page looks right, that the brand values are the owner's, and that the
   colours suit the product. The approval line is the owner's: the owner replaces `Approved: not yet` in the mockup's
   `README.md` by `Approved by <name> on <YYYY-MM-DD>`. The session must never write that line and never approve a mockup itself.
6. Print the next steps, with the requirement the design serves. A change of only `docs/design/` carries `Brief: none (design)`,
   which passes whether or not the repository has an open brief; add `--brief <n>` when the work answers one. The script prints
   the body as a file path and its text, only after the repository's own `check_pr_body.py` passed it; use the body unchanged.

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/engines.py" design-next-steps --req REQ-<n>
```

Do not commit or push, and do not open a pull request: the person or their session does.

## /agk:design inventory

`/agk:design inventory` lists every screen and state of the product before anything is drawn (SPEC-0037 rule 3), in
`docs/design/inventory.md`.

1. Fetch the default branch, make sure the work tree is clean (stop and say so if it is not), create the branch from the
   default branch, and write the skeleton. The script reads `docs/requirements.md` and the `Requirements:` lines of
   `docs/specs/`, writes one section per requirement with its specs filled and every other slot empty, refuses when the
   file exists, and never fills a slot:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/design.py" inventory
```

2. Fill the slots from the requirements and the specs, and from nothing else; if `[engines]` in `agk.toml` has a `design`
   key, its skill may draft them, and the session writes them into the file's shape. Each requirement gets its screens or
   `no screen: <reason>`; each screen gets its own section with its flow, its pattern (one of the kit's design standard),
   the screens it links to and a `State` line for `default`, the six required states and any state a spec names, each
   `yes` or `n/a: <reason>`. Never leave a required state out, and never take a name or a text from `private/` or
   `reference/`.
3. Check, and correct the file on a failure, at most three rounds, then stop and report. The check, not the session,
   decides that the inventory is complete; it names the rule and the screen of each problem:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/check_design.py"
```

4. Leave the agreement to the person. The person agrees the inventory with a comment on its pull request whose first line
   is `Approve: inventory <full head ID>`, from an account listed in `spec_approvers`; a session never posts that line,
   and nothing is drawn before it is there. Do not commit or push, and do not open a pull request: the person or their
   session does.
