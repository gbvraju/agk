# Prototype {{version}}

A click-through prototype written by `design.py prototype` (`/agk:design prototype`, SPEC-0037 rule 4) from the kit's
design standard, `docs/design/theme.md` and the agreed `docs/design/inventory.md`, and from nothing else.

- Open `index.html` in a browser, from the files: no build step, no server, no network.
- Each page is `<screen>--<state>.html`, with a state bar of plain links to every state of its screen and plain links to
  the screens it links to; with the script off it still works by its links.
- `standard.css` is the kit's standard unchanged; `theme.css` is the theme block of `docs/design/theme.md`.
- `agk-prototype.js` is the kit's runtime, unchanged: keyboard access to the state bar and a demo mode. It makes no
  request and keeps no data. A project adds no script.
- `demo.md` holds the demo path of each flow, one sentence for the presenter per step.
- Every name, address, amount, date, phone number, email address and link comes from the kit's invented fixture set.

Sign-off is the person's line `Approve: design {{version}} <full head ID>` on this folder's pull request; a session never
posts it. Once signed off this folder is frozen: a change is a new version, never an edit in place. `screenshots/` is
written only by `design.py screenshots`.
