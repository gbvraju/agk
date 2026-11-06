"""session.py next never offers a parked brief (brief #615, ADR-0301; REQ-037).

A brief is parked when it has the label `agk:parked` or a `Parked:` line in its body. `next` skips
it with `skip #<n>: parked` and offers the next free brief. The label is created only when missing,
by the router's `Labels.ensure`, with one POST. Saved responses only; invented data."""

from __future__ import annotations

import pytest
import route
from test_session import ISSUES, Stub, issue, listing, posts, session
from test_session_flow import brief
from test_session_plan import free


@pytest.fixture
def stub(tmp_path):
    return Stub(tmp_path)


@pytest.fixture
def proj(repo, stub):
    repo.git("remote", "add", "origin", "https://github.com/acme/widgets.git")
    return repo


def nxt(proj, stub):
    return session(proj, stub, "next", "--session", "s-me")


def test_a_brief_with_the_parked_label_is_skipped(proj, stub):
    parked = {**issue(4, brief("docs/a.md")), "labels": [{"name": "agk:parked"}]}
    listing(stub, [parked, issue(5, brief("docs/b.md"))])
    free(stub, 4, 5)
    out = nxt(proj, stub)
    assert "skip #4: parked" in out.stdout.splitlines()
    assert out.returncode == 0 and "brief #5" in out.stdout and "brief #4" not in out.stdout
    assert posts(stub) == []


def test_a_brief_with_a_parked_line_is_skipped(proj, stub):
    listing(stub, [issue(4, brief("docs/a.md") + "Parked: waiting for the owner\n")])
    free(stub, 4)
    out = nxt(proj, stub)
    assert "skip #4: parked" in out.stdout.splitlines()
    assert out.returncode == 1 and "no brief" in out.stdout


def test_an_unparked_brief_is_offered_and_a_word_in_prose_does_not_park(proj, stub):
    listing(stub, [issue(4, brief("docs/a.md") + "This is not Parked: here, only prose.\n")])
    free(stub, 4)
    out = nxt(proj, stub)
    assert out.returncode == 0 and "brief #4" in out.stdout and "parked" not in out.stdout


def test_the_parked_label_is_created_once_when_missing(monkeypatch):
    posted = []
    monkeypatch.setattr(route, "listing", lambda endpoint: [{"name": "agk-brief"}])
    monkeypatch.setattr(route, "write", lambda endpoint, *a, method="GET": posted.append((method, endpoint, a)))
    labels = route.Labels("acme/widgets")
    labels.ensure("agk:parked")
    labels.ensure("agk:parked")
    assert [(m, e) for m, e, _ in posted] == [("POST", "repos/acme/widgets/labels")]
    assert "name=agk:parked" in posted[0][2]


def test_the_parked_label_is_not_created_when_present(monkeypatch):
    posted = []
    monkeypatch.setattr(route, "listing", lambda endpoint: [{"name": "agk:parked"}])
    monkeypatch.setattr(route, "write", lambda *a, **k: posted.append(a))
    route.Labels("acme/widgets").ensure("agk:parked")
    assert posted == []
