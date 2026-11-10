"""`session.py kind --brief N`: a brief's kind from its `Size:` and `Touches:` lines.

SPEC-0045 rule 4.

`session.py fallback` (SPEC-0053 rule 4, REQ-060, brief #763, ADR-0344) is at the end of this file.

REQ-052 AC2, brief #623 (build (b) of SPEC-0045, ADR-0289). The command reads one brief with a GET,
posts nothing and prints one line `kind: <kind>`: `design` for a missing, repeated or unreadable
`Size:` or `Touches:` line and for a glob that may match a design path; `small` for `Size: S` whose
globs match no protected class but the test folders; `build` otherwise; never `review` or
`mechanical`. A `gh` stub on `PATH`, saved briefs, no network. The tests were written first."""

from __future__ import annotations

import socket
import subprocess  # nosec B404 - the tests stub it, nothing is run
from pathlib import Path

import pytest
import session as session_script
from test_session import ISSUES, posts, session
from test_session import proj as session_proj  # noqa: F401  (the fixtures of test_session)
from test_session import stub as session_stub  # noqa: F401

# The kit's protected classes (`config/protected-paths.txt`), saved: a copied tree may lack it.
PROTECTED = "\n".join(
    [
        "# Protected path classes.",
        "constitution/",
        "config/",
        ".claude/",
        ".github/",
        "docs/requirements.md",
        "CLAUDE.md",
        "scripts/agk/",
        "Makefile",
        "pyproject.toml",
        "agk.mk",
        "agk.toml",
        "tests/kit/",
        "kit/",
        "tests/kit_dev/",
        ".claude-plugin/",
        "skills/",
    ]
)


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


# --- the next provider (SPEC-0053 rule 4, REQ-060, brief #763) ---------------------------------

ALPHA, BETA, GAMMA = "alpha-1", "beta-2", "gamma-3"
LISTS = f'[models.providers]\nstrongest = ["{ALPHA}", "{BETA}"]\nmid = ["{GAMMA}"]\n'
ENDPOINT = "https://alpha.example.com"
ODD = "turbo-x"  # an invented value that a refusal must never echo
TIERS = {
    "design": "strongest",
    "review": "strongest",
    "build": "strongest",
    "small": "mid",
    "mechanical": "mid",
}


def project(tmp_path: Path, text: str | None) -> Path:
    if text is not None:
        (tmp_path / "agk.toml").write_text(text, encoding="utf-8")
    return tmp_path


def tree(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


@pytest.fixture
def fallback(tmp_path, monkeypatch, capsys):
    """Run `session.py fallback` on `tmp_path`: no socket, no process, and no file changes."""

    def fail(*_args, **_kwargs):
        raise AssertionError("fallback reached the network or a process")

    monkeypatch.setattr(socket, "socket", fail)
    monkeypatch.setattr(socket, "create_connection", fail)
    monkeypatch.setattr(subprocess, "run", fail)
    monkeypatch.setattr(subprocess, "Popen", fail)
    monkeypatch.setattr(session_script, "repo_root", lambda: tmp_path)

    def run(text: str | None, *args: str) -> tuple[int, str]:
        project(tmp_path, text)
        before = tree(tmp_path)
        code = session_script.main(["fallback", *args])
        assert tree(tmp_path) == before
        return code, capsys.readouterr().out.strip()

    return run


@pytest.mark.parametrize("kind", TIERS)
def test_no_table_leaves_no_provider_for_every_kind(fallback, kind):
    """REQ-060 AC1: rule 4, with no list for the tier there is no fallback."""
    assert fallback(None, "--kind", kind) == (
        1,
        f"no provider left: {kind} {TIERS[kind]}",
    )


def test_after_with_no_list_for_the_tier_leaves_no_provider(fallback):
    """REQ-060 AC1: rule 4, no list for the tier is `no provider left`, not a refused option."""
    assert fallback('default_branch = "main"\n', "--kind", "build", "--after", ALPHA) == (
        1,
        "no provider left: build strongest",
    )


def test_fallback_prints_the_first_label_with_the_effort(fallback):
    """REQ-060 AC3: rule 4, the first label of the kind's tier, on the one line."""
    assert fallback(LISTS, "--kind", "build") == (0, f"fallback: build strongest medium {ALPHA}")


def test_fallback_prints_the_next_label_after_the_one_that_failed(fallback):
    """REQ-060 AC3: rule 4, `--after` gives the next label of the same list."""
    assert fallback(LISTS, "--kind", "build", "--after", ALPHA) == (
        0,
        f"fallback: build strongest medium {BETA}",
    )


def test_fallback_of_a_small_kind_prints_its_own_tier_only(fallback):
    """REQ-060 AC3: rules 2 and 4, a `mid` kind prints a `mid` label, never a `strongest` one."""
    code, out = fallback(LISTS, "--kind", "small")
    assert (code, out) == (0, f"fallback: small mid low {GAMMA}")
    assert ALPHA not in out and BETA not in out


def test_fallback_follows_a_tier_the_table_moved(fallback):
    """REQ-060 AC3: rule 2, the tier and effort are the kind's as the `[models]` table sets them."""
    text = f'[models]\nbuild = {{ tier = "mid", effort = "high" }}\n{LISTS}'
    assert fallback(text, "--kind", "build") == (0, f"fallback: build mid high {GAMMA}")


def test_fallback_of_a_review_stays_on_strongest_at_high(fallback):
    """REQ-060 AC6: rules 2 and 8, the review floor holds on a fallback."""
    assert fallback(LISTS, "--kind", "review", "--after", ALPHA) == (
        0,
        f"fallback: review strongest high {BETA}",
    )


def test_fallback_of_a_design_keeps_its_tier_and_effort(fallback):
    """REQ-060 AC6: rule 8, a `design` session stays on its tier at its effort."""
    assert fallback(LISTS, "--kind", "design") == (0, f"fallback: design strongest high {ALPHA}")


def test_no_label_after_the_last_leaves_no_provider(fallback):
    """REQ-060 AC4: rules 4 and 7, one line naming the kind and the tier, exit 1."""
    assert fallback(LISTS, "--kind", "build", "--after", BETA) == (
        1,
        "no provider left: build strongest",
    )


def test_a_list_of_one_label_has_no_fallback(fallback):
    """REQ-060 AC4: rule 3, the one label has nothing after it."""
    assert fallback(LISTS, "--kind", "small", "--after", GAMMA) == (
        1,
        "no provider left: small mid",
    )


def test_an_unknown_kind_is_refused_naming_the_option(fallback):
    """REQ-060 AC4: rule 4, exit 2, naming `--kind` and never the value."""
    code, out = fallback(LISTS, "--kind", ODD)
    assert code == 2
    assert "--kind" in out and ODD not in out


@pytest.mark.parametrize("after", [ODD, GAMMA])
def test_an_after_label_outside_the_tier_list_is_refused(fallback, after):
    """REQ-060 AC4: rule 4, an unknown label and another tier's label, exit 2, value not named."""
    code, out = fallback(LISTS, "--kind", "build", "--after", after)
    assert code == 2
    assert "--after" in out and after not in out


def test_a_malformed_table_stops_the_fallback_naming_the_setting(fallback):
    """REQ-060 AC2: rule 3, `fallback` prints no label from a table that is refused."""
    code, out = fallback(f'[models.providers]\nmid = ["{ENDPOINT}"]\n', "--kind", "small")
    assert code == 2
    assert "setting: models.providers.mid" in out and ENDPOINT not in out
