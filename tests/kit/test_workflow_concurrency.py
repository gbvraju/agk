"""The edited governance run waits in its own group (found bug #1253, brief #1371, ADR-0576).

REQ-050: GitHub keeps one running and one pending run per concurrency group, and a newer pending
run replaces an older pending one whatever `cancel-in-progress` says (verify: GitHub's concurrency
documentation). When a push is followed within seconds by a description edit and
`ready_for_review`, an edited run in the full runs' group replaced the pending `ready_for_review`
full run after that run had cancelled the running `synchronize` one, and no full run of the head
was left. So no `edited` run may share a group with a full run of a pull request. The edited run
orders itself after the full run by its own `Latest full run` step (brief #1122, ADR-0480
decision 2).

The workflows are read as text and each `concurrency:` expression is evaluated here for invented
events, by a small evaluator of the expression subset the two blocks use (string literals,
property paths, `==`, `!=`, `!`, `&&`, `||`, parentheses and `format`). No network, no GitHub.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"
DEFAULT = "main"
PR = 4242
SHA = "e5" * 20
FULL_ACTIONS = ("opened", "synchronize", "reopened", "ready_for_review")

TOKEN = re.compile(
    r"\s*(?:(?P<str>'(?:[^']|'')*')|(?P<op>&&|\|\||==|!=|!|\(|\)|,)"
    r"|(?P<num>\d+)|(?P<name>[A-Za-z_][A-Za-z0-9_\-]*(?:\.[A-Za-z_][A-Za-z0-9_\-]*|\[\d+\])*))"
)


def tokens(expr: str) -> list[tuple[str, str]]:
    out, pos, expr = [], 0, expr.strip()
    while pos < len(expr):
        m = TOKEN.match(expr, pos)
        if not m or m.end() == pos:
            raise ValueError(f"cannot read the expression at {pos}: {expr[pos:pos + 20]!r}")
        kind = m.lastgroup
        out.append((kind, m.group(kind)))
        pos = m.end()
    return out


def truthy(value: object) -> bool:
    return value not in (None, False, 0, "")


def equal(a: object, b: object) -> bool:
    if isinstance(a, str) and isinstance(b, str):
        return a.lower() == b.lower()  # GitHub compares strings ignoring case
    return a == b


def text(value: object) -> str:
    return "" if value is None else str(value)


class Expr:
    """A recursive-descent evaluator: `||` < `&&` < `==`/`!=` < `!` < primary."""

    def __init__(self, expr: str, context: dict) -> None:
        self.toks, self.i, self.ctx = tokens(expr), 0, context

    def value(self) -> object:
        result = self.or_()
        if self.i != len(self.toks):
            raise ValueError(f"unread tokens: {self.toks[self.i:]}")
        return result

    def peek(self) -> str | None:
        return self.toks[self.i][1] if self.i < len(self.toks) else None

    def take(self, want: str | None = None) -> tuple[str, str]:
        tok = self.toks[self.i]
        if want is not None and tok[1] != want:
            raise ValueError(f"expected {want}, read {tok[1]}")
        self.i += 1
        return tok

    def or_(self) -> object:
        left = self.and_()
        while self.peek() == "||":
            self.take()
            right = self.and_()
            left = left if truthy(left) else right
        return left

    def and_(self) -> object:
        left = self.cmp()
        while self.peek() == "&&":
            self.take()
            right = self.cmp()
            left = right if truthy(left) else left
        return left

    def cmp(self) -> object:
        left = self.unary()
        while self.peek() in ("==", "!="):
            op = self.take()[1]
            right = self.unary()
            left = equal(left, right) if op == "==" else not equal(left, right)
        return left

    def unary(self) -> object:
        if self.peek() == "!":
            self.take()
            return not truthy(self.unary())
        return self.primary()

    def primary(self) -> object:
        kind, tok = self.take()
        if tok == "(" and kind == "op":
            inner = self.or_()
            self.take(")")
            return inner
        if kind == "str":
            return tok[1:-1].replace("''", "'")
        if kind == "num":
            return int(tok)
        if kind == "name" and self.peek() == "(":
            self.take("(")
            args = [self.or_()]
            while self.peek() == ",":
                self.take()
                args.append(self.or_())
            self.take(")")
            if tok != "format":
                raise ValueError(f"function {tok} is not in the subset")
            return re.sub(r"\{(\d+)\}", lambda m: text(args[1 + int(m.group(1))]), text(args[0]))
        if kind == "name":
            if tok in ("true", "false"):
                return tok == "true"
            if tok == "null":
                return None
            node: object = self.ctx
            for part in re.findall(r"[A-Za-z_][A-Za-z0-9_\-]*|\[\d+\]", tok):
                if part.startswith("["):
                    idx = int(part[1:-1])
                    node = node[idx] if isinstance(node, list) and idx < len(node) else None
                else:
                    node = node.get(part) if isinstance(node, dict) else None
            return node
        raise ValueError(f"unexpected token {tok}")


def evaluate(expr: str, context: dict) -> object:
    """A whole `${{ … }}` gives its value; text with embedded ones gives the joined text."""
    whole = re.fullmatch(r"\$\{\{(.*?)\}\}", expr.strip(), re.S)
    if whole:
        return Expr(whole.group(1), context).value()
    return re.sub(r"\$\{\{(.*?)\}\}", lambda m: text(Expr(m.group(1), context).value()), expr)


def concurrency(name: str) -> tuple[str, str]:
    """(group, cancel-in-progress) of the workflow's top-level `concurrency:` block."""
    body = (WORKFLOWS / name).read_text(encoding="utf-8")
    block = body.split("\nconcurrency:\n", 1)[1].split("\njobs:", 1)[0]
    group = re.search(r"(?m)^  group: (.+)$", block).group(1)
    cancel = re.search(r"(?m)^  cancel-in-progress: (.+)$", block).group(1)
    return group, cancel


def pull_types(name: str) -> list[str]:
    body = (WORKFLOWS / name).read_text(encoding="utf-8")
    on = body.split("\non:\n", 1)[1].split("\n\n", 1)[0]
    m = re.search(r"(?m)^  pull_request:\n    types: \[([^\]]*)\]", on)
    return [t.strip() for t in m.group(1).split(",")] if m else []


def event(name: str, action: str | None = None, ref: str = DEFAULT) -> dict:
    ev: dict = {"repository": {"default_branch": DEFAULT}}
    if name == "pull_request":
        ev.update(action=action, pull_request={"number": PR})
    if name == "merge_group":
        ev.update(action="checks_requested")
    return {"github": {"event_name": name, "ref_name": ref, "sha": SHA, "event": ev}}


def run_of(name: str, ctx: dict) -> tuple[object, bool]:
    group, cancel = concurrency(name)
    return evaluate(group, ctx), truthy(evaluate(cancel, ctx))


def test_the_evaluator_reads_the_subset():
    """REQ-050: the evaluator of this file follows GitHub's `&&`/`||` value rules and `format`."""
    ctx = {"github": {"a": "x", "n": 7}}
    assert evaluate("${{ github.a == 'X' && 'yes' || 'no' }}", ctx) == "yes"
    assert evaluate("${{ github.missing || github.n }}", ctx) == 7
    assert evaluate("${{ format('g-{0}-{1}', github.n, github.none) }}", ctx) == "g-7-"
    assert evaluate("${{ !(github.a != 'x') }}", ctx) is True
    assert evaluate("plain", ctx) == "plain"
    with pytest.raises(ValueError):
        evaluate("${{ github.a = 'x' }}", ctx)


def test_no_edited_run_shares_a_group_with_a_full_run():
    """REQ-050: brief #1371 answer 1 and 2 (found bug #1253): the governance `edited` run is in a
    group of its own per pull request, so it can never replace a pending full run of the head."""
    full = {run_of("governance.yml", event("pull_request", a))[0] for a in FULL_ACTIONS}
    edited, _ = run_of("governance.yml", event("pull_request", "edited"))
    assert full == {f"governance-{PR}-code"}
    assert edited == f"governance-{PR}-edited"
    assert edited not in full


def test_full_runs_cancel_each_other_and_edited_runs_cancel_only_edited_runs():
    """REQ-050: brief #1371 answer 1: the full runs keep `governance-<pr>-code` and their cancel
    rule; `cancel-in-progress` is true among the edited runs, whose group holds no other run."""
    for action in FULL_ACTIONS + ("edited",):
        assert run_of("governance.yml", event("pull_request", action))[1] is True, action


def test_the_default_branch_push_group_is_unchanged():
    """REQ-050: brief #1371 answer 2 (brief #621, ADR-0302): every push to the default branch
    shares one fixed group and a running push run is never cancelled."""
    assert run_of("governance.yml", event("push")) == (f"governance-{DEFAULT}-code", False)
    queue = run_of("governance.yml", event("merge_group"))
    assert queue == (f"governance-{SHA}-code", False)


def test_the_proof_runs_share_no_group_with_a_run_that_can_replace_them():
    """REQ-050: brief #1371 answer 1: `proof.yml` runs on no `edited` event, so every run in a
    pull request's proof group is a full run of that pull request; it is left unchanged."""
    assert "edited" not in pull_types("proof.yml")
    groups = {run_of("proof.yml", event("pull_request", a))[0] for a in pull_types("proof.yml")}
    assert groups == {f"proof-{PR}"}


def test_every_governance_pull_request_type_is_covered():
    """REQ-050: the cases above name every `pull_request` type of the governance workflow, so a
    new type cannot slip into a group unchecked."""
    assert set(pull_types("governance.yml")) == set(FULL_ACTIONS) | {"edited"}


def test_the_edited_run_waits_well_above_a_slow_full_run():
    """REQ-050: brief #1371 (fix list 1 on #1374): with its own group the edited run's only order
    after the full run is its step `Latest full run`, whose bound counts from the edited run's
    start, so it polls every 30 seconds for at most 45 minutes, well above a full run of 17
    minutes, and fails closed after that."""
    body = (WORKFLOWS / "governance.yml").read_text(encoding="utf-8")
    step = body.split("      - name: Latest full run\n", 1)[1].split("\n      - name: ", 1)[0]
    attempts = re.search(r"for attempt in \$\(seq 0 (\d+)\); do", step)
    sleep = re.search(r'\[ "\$attempt" -lt (\d+) \] && sleep (\d+)', step)
    assert attempts and sleep and attempts.group(1) == sleep.group(1)
    minutes = int(sleep.group(1)) * int(sleep.group(2)) / 60
    assert minutes == 45
    assert f"did not finish in {int(minutes)} minutes" in step
    assert step.rstrip().endswith("exit 1")
