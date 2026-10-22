# Review checklist

Answer every question in the verdict's `Checklist:` lines, with evidence or `n/a`. One question for each kind of the catch log (`docs/runs/architect-catches-N.md`, the list of kinds in its header), at
most fifteen. This file changes only by a pull request whose decision record cites a row of a catch log; no question is added from opinion.

1. `wrong-assumption`: which assumption of the change did you check against the record, and what did the record say?
2. `false-declaration`: does every declaration (`Behaviour: unchanged`, a count, a status) match the change? Show the line and the evidence.
3. `test-proves-less`: for each criterion, what would a passing test still allow? Name the case it does not cover.
4. `stale-claim`: does any text or output claim something the current head no longer does? Quote the claim and the head.
5. `fragile-code`: does any behaviour depend on the ending, the order or the spelling of a string? Name it.
6. `security`: credentials, redirects, origins, permissions, what is logged: what did you read, and what could a stranger do?
7. `vendored-file-change`: does the change touch a verbatim kit file? If so, is the kit bump, the hash and the ADR there?
8. `scope-rule`: is every changed path and rule inside what the Approved text and the brief name? List what is not.
9. `process-order`: tests first and shown failing, then proof, then the verdict, then a person merges: which step is out of order?
10. `kit-defect`: does the change work around a kit gap in the project? Write the generic residual instead.
11. `cost`: what does the change add per run (a request, a file read, minutes)? Is it measured or left as a residual?
12. `late-discovery`: is there a fact found after the intake that should have been asked at the intake? Which question would have exposed it?
