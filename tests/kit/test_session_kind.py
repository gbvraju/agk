"""`session.py kind --brief N`: a brief's kind from its `Size:` and `Touches:` lines (SPEC-0045 rule 4).

REQ-052 AC2, brief #623 (build (b) of SPEC-0045, ADR-0289). The command reads one brief with a GET,
posts nothing and prints one line `kind: <kind>`: `design` for a missing, repeated or unreadable
`Size:` or `Touches:` line and for a glob that may match a design path; `small` for `Size: S` whose
globs match no protected class but the test folders; `build` otherwise; never `review` or
`mechanical`. A `gh` stub on `PATH`, saved briefs, no network. The tests were written first."""

from __future__ import annotations

from pathlib import Path

import pytest
from test_session import ISSUES, posts, session
from test_session import proj as session_proj  # noqa: F401  (the fixtures of test_session)
from test_session import stub as session_stub  # noqa: F401

KIT = Path(__file__).resolve().parents[2]
PROTECTED = (KIT / "config" / "protected-paths.txt").read_text(encoding="utf-8")


@pytest.fixture
def stub(request):
    return request.getfixturevalue("session_stub")


@pytest.fixture
def proj(request):
    found = request.getfixturevalue("session_proj")
    found.write("config/protected-paths.txt", PROTECTED)
    return found


def brief(size: str | None, touches: str | None, extra: str = "") -> str:
    lines = [
        'Sentence: "A thing happens for a person."',
        "Answers:",
        "1. Do it.",
        "Advances: REQ-052",
    ]
    lines += [f"Size: {size}"] if size is not None else []
    lines += [f"Touches: {touches}"] if touches is not None else []
    return "\n".join(lines) + "\n" + extra


def kind(proj, stub, body: str | None, number: int = 41):
    if body is not None:
        stub.serve(f"{ISSUES}/{number}", {"number": number, "state": "open", "body": body})
    return session(proj, stub, "kind", "--brief", str(number))


@pytest.mark.parametrize(
    ("size", "touches", "want"),
    [
        ("S", "tests/kit/test_example.py, tests/kit_dev/**", "small"),  # test folders only
        ("S", "docs/guides/example.md, tests/kit/**", "small"),  # unprotected and tests
        ("S", "scripts/agk/session.py, tests/kit/**", "build"),  # a protected class
        ("S", "agk.toml", "build"),
        ("M", "tests/kit/test_example.py", "build"),  # not S
        ("L", "docs/guides/example.md", "build"),
        ("S", "**", "design"),
        ("M", "docs/specs/0045-example.md", "design"),
        ("S", "docs/adr/*.md", "design"),
        ("S", "docs/requirements.md", "design"),
        ("M", "constitution/principles.md", "design"),
        ("S", ".github/workflows/example.yml", "design"),
        ("S", "config/reviewers.yaml", "design"),
        ("S", ".claude/hooks/example.py", "design"),
        ("M", "scripts/agk/merge_cleared.py", "design"),
        ("M", "scripts/agk/route.py", "design"),
        ("S", "scripts/agk/guard.py", "design"),  # a guard file
        ("M", "scripts/agk/guard_rules.json", "design"),
        ("M", "scripts/agk/*.py", "design"),  # may match a guard file (Q-S0045-4)
        ("M", "scripts/agk/", "design"),
        ("S", "docs/**", "design"),  # may match a spec
    ],
)
def test_the_kind_of_a_brief(proj, stub, size, touches, want):
    """REQ-052 AC2: rule 4, in order: design paths, then small, then build."""
    out = kind(proj, stub, brief(size, touches))
    assert out.returncode == 0, out.stdout + out.stderr
    assert out.stdout == f"kind: {want}\n"


@pytest.mark.parametrize(
    "body",
    [
        brief(None, "tests/kit/**"),  # no Size: line
        brief("S", None),  # no Touches: line
        brief("S", "tests/kit/**", "Size: S\n"),  # a repeated Size: line
        brief("S", "tests/kit/**", "Touches: tests/kit_dev/**\n"),  # a repeated Touches: line
        brief("XS", "tests/kit/**"),  # an unreadable Size: line (Q-S0045-3)
        brief("S", "tests/kit/**, "),  # an empty glob
        brief("S", ""),  # a Touches: line with no glob
    ],
)
def test_a_missing_repeated_or_unreadable_line_gives_design(proj, stub, body):
    """REQ-052 AC2: rule 4, the first case; nothing is lowered."""
    out = kind(proj, stub, body)
    assert out.returncode == 0, out.stdout + out.stderr
    assert out.stdout == "kind: design\n"


def test_a_brief_that_cannot_be_read_gives_design(proj, stub):
    """REQ-052 AC2: a brief that cannot be read gives the highest kind, never a lower one."""
    out = kind(proj, stub, None)  # nothing served: the GET fails
    assert out.stdout == "kind: design\n"
    assert out.returncode == 0


def test_an_unreadable_protected_list_gives_design(proj, stub):
    """REQ-052 AC2: without the protected list `small` cannot be shown, so nothing is lowered."""
    (proj.root / "config" / "protected-paths.txt").unlink()
    out = kind(proj, stub, brief("S", "tests/kit/**"))
    assert out.stdout == "kind: design\n"


def test_kind_only_gets_and_never_prints_review_or_mechanical(proj, stub):
    """REQ-052 AC2: GET only, posts nothing; `review` and `mechanical` are never a brief's kind."""
    for number, (size, touches) in enumerate(
        [("S", "tests/kit/**"), ("M", "agk.toml"), ("S", "**"), (None, None)], start=50
    ):
        out = kind(proj, stub, brief(size, touches), number)
        assert out.stdout.split()[1] not in ("review", "mechanical")
    assert posts(stub) == []
    assert {call[0] for call in stub.calls()} == {"GET"}


@pytest.mark.parametrize(
    "args",
    [
        ("kind",),
        ("kind", "--brief"),
        ("kind", "--brief", "x"),
        ("kind", "--brief", "4", "--pr", "5"),
    ],
)
def test_kind_usage_is_checked(proj, stub, args):
    """REQ-052 AC2: a wrong command line prints the usage and exits 2."""
    out = session(proj, stub, *args)
    assert out.returncode == 2
    assert "session.py kind --brief N" in out.stdout
