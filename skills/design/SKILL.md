---
name: design
description: List every screen and state of a product (the inventory), then write a prototype version of them to click through, from the kit's design standard and the theme, for the person to sign off by a line. Writes files; never commits.
disable-model-invocation: true
argument-hint: "prototype | inventory"
---

# /agk:design

`/agk:design inventory` lists every screen and state before anything is drawn; `/agk:design prototype` then draws them
as a prototype version to click through (SPEC-0037). `/agk:design <name>` no longer writes a mockup folder: `design.py
write` refuses, naming rule 12 and pointing to `/agk:design prototype`, and writes nothing. The existing folders of
`docs/design/mockups/` are only read and checked, as before.

An engine only drafts. If `[engines]` in `agk.toml` has a `design` key, it names a skill the session can see (`agk doctor`
reports it as present, absent or missing); use that skill to draft the brand record and the inventory's slots. If the key
is absent, use the kit's templates. Either way the text is written in the kit's shape and passes `check_design.py`.
An engine never decides, never approves, and never edits a protected file by itself: the owner gives every brand value and
its source, and a value the owner did not give stays in brackets.

## /agk:design prototype

`/agk:design prototype` writes the next version folder `docs/design/prototype/v<n>/` (`v1`, `v2` and so on, never
overwritten) from the kit's design standard, `docs/design/theme.md` and the agreed `docs/design/inventory.md`, and from
nothing else: `index.html` (the flows and the start of each demo path), one page `<screen>--<state>.html` for each screen
and state, `standard.css`, `theme.css`, the kit's runtime `agk-prototype.js` unchanged, `demo.md` (one sentence for the
presenter per step) and `README.md`. Every page has a state bar of plain links to every state of its screen and plain
links to the screens it links to, so it works by clicking, opened from the files, with no build step and no server.

1. Fetch the default branch and make sure the work tree is clean; if it is not, stop and say so. Create the branch from the
   default branch, and write the version:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/design.py" prototype
```

   It refuses, naming rule 3, when the inventory's digest has no `inventory` row in `docs/design/signoffs.md` (the
   person's `Approve: inventory` line comes first). With no `docs/design/theme.md` it writes one on the standard from
   the kit's template, with the evidence line set to the version; an old-format theme is moved onto the standard, its
   five tokens kept in value and its brand record, source lines and evidence line carried over unchanged.
2. Do not edit the pages, `standard.css` or `agk-prototype.js`, and add no script. Every name, address, amount, date,
   phone number, email address and link on a page comes from the kit's invented fixture set, never from `private/`,
   `reference/` or a real record. Fill the brand record from what the owner gave, and from nothing else; a value still
   unknown stays in brackets and is reported as at risk.
3. `screenshots/` in a version folder is written only by `design.py screenshots`, never by hand. Where a headless
   browser is found, `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/design.py" screenshots --version v<n>` writes one
   screenshot of each page at each breakpoint, in light and dark, and `screenshots/reflow.json` (`ok` or `sideways`);
   without one it says so and every entry reads `not run`, never passed.
4. Check, and correct the theme on a failure, at most three rounds, then stop and report:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/check_design.py"
```

   then run `make governance`. Both must pass. `design: the theme is not approved yet` is information, not a failure.
5. Last, say what the checks cannot check: that the pages look right, that the brand values are the owner's, and that the
   colours suit the product. Sign-off is the person's: a comment on the pull request whose first line is
   `Approve: design <version> <full head ID>`, from an account listed in `spec_approvers`. A session never posts that
   line and never approves a version itself; once signed off a version is frozen, and a change is a new version.
6. Print the next steps, with the requirement the design serves. A change of only `docs/design/` carries `Brief: none (design)`,
   which passes whether or not the repository has an open brief; add `--brief <n>` when the work answers one. The script prints
   the body as a file path and its text, only after the repository's own `check_pr_body.py` passed it; use the body unchanged.

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/engines.py" design-next-steps --req REQ-<n>
```

Do not commit or push, and do not open a pull request: the person or their session does.

## A UI build against its signed-off version

The builder of a UI brief (one with a `Screens:` line) compares each named screen and state with the signed-off version
before it marks its pull request ready (SPEC-0037 rule 11). It needs `render` in the `[design]` table of `agk.toml`, the
project's command that writes the built page of a screen and state into `AGK_DESIGN_OUT`:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/design_compare.py" --version v<n> --screens "<screen>/<state>, ..."
```

It prints `<screen>/<state> match` or `<screen>/<state> drift: structure, tokens, pixels` (the kinds found), ending
`; pixels: not run` without a headless browser, and exits 0 on drift: put each line in the pull request body as a
`Design match:` line and leave the judgement to the conductor. A build that changes no screen named by a `Screens:` line
runs none.

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
