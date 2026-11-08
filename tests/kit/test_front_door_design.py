"""Tests of `front_door.py` build (e): the review artifacts and the phase (SPEC-0048 1, 8, 9).

REQ-055 AC4 (rule 8): the design's review artifact is chosen by the discovery document's
`Screens:` line. With `no` the design names one `Demo: docs/runs/<file>` line whose file exists,
and nothing is run; with `yes`, and with `open` or no discovery document (read as `yes`), a
prototype version folder of SPEC-0037 exists. A `Walkthrough: <where>` line is judgement: it is
never opened and never stands in for the artifact. REQ-055 AC4 and AC7 (rules 1 and 9):
`front_door.py status` prints, from the files only and writing nothing, the phase each problem is
in and what it waits for, and never passes `waits for the go`, which is read from saved comments.
Every refusal names the rule and the file, never a value (rule 15). Fixtures in `tmp_path` only:
invented data (`example.com`), no network (a socket stub raises).
"""

from __future__ import annotations

import json
import socket
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = KIT_ROOT / "scripts" / "agk" / "front_door.py"
sys.path.insert(0, str(SCRIPT.parent))

TODAY = "2026-11-08"
SLUG = "orders-are-lost"
DESIGN = f"docs/design/architecture/{SLUG}.md"
DEMO = "docs/runs/orders-demo-1.md"
PLACE = "the owner's drive at example.com, folder walkthroughs"  # a value: never printed
LINK = "https://github.com/example/shop/issues/7"
IDS = [
    "users",
    "existing",
    "runs",
    "data",
    "scale",
    "compliance",
    "devices",
    "accessibility",
    "languages",
    "brand",
    "constraints",
    "success",
    "data-rules",
    "environments",
    "non-functional",
]


def write(tmp_path: Path, rel: str, text: str) -> Path:
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def discovery(tmp_path: Path, screens: str = "no") -> Path:
    """A discovery document written by `discovery-write` itself, so it passes rule 5."""
    import front_door

    issue = write(
        tmp_path,
        "in/issue.json",
        json.dumps(
            {
                "number": 7,
                "title": "Orders are lost",
                "html_url": LINK,
                "body": "Problem: Orders at example.com are lost when payment times out.",
                "labels": [{"name": "agk-problem"}],
            }
        ),
    )
    rows = [
        {"id": q, "answer": f"Invented answer for {q}.", "where": f"{LINK}#issuecomment-{n}"}
        for n, q in enumerate(IDS, 100)
    ]
    answers = write(tmp_path, "in/answers.json", json.dumps({"screens": screens, "answers": rows}))
    args = ["discovery-write", "--issue", str(issue), "--answers", str(answers)]
    assert front_door.main([*args, "--root", str(tmp_path)]) == 0
    return tmp_path / f"docs/discovery/{SLUG}.md"


def record(tmp_path: Path, accessed: str = "2026-10-01") -> Path:
    lines = ["# Research: Orders are lost", ""]
    for name in ("Alpha", "Beta"):
        url = f"https://{name.lower()}.example.com/docs"
        lines += [f"## Option: Queue {name}", "", f"- Source: {url} (accessed {accessed})", ""]
    lines += ["## Criteria", "", "| Criterion | Queue Alpha | Queue Beta |", "| --- | --- | --- |"]
    for c in (
        "capability fit",
        "cost",
        "licence",
        "data handling and residency",
        "maturity",
        "integration effort",
        "lock-in",
    ):
        lines.append(f"| {c} | invented | invented |")
    lines += ["", "## Recommendation", "", "Queue Alpha (proposal).", ""]
    return write(tmp_path, f"docs/research/{SLUG}.md", "\n".join(lines))


def design(tmp_path: Path, *extra: str) -> Path:
    lines = ["# Architecture: Orders are lost", "", f"Research: docs/research/{SLUG}.md", *extra]
    lines += ["", "```text", "shop api -> queue -> worker -> orders store", "```", ""]
    return write(tmp_path, DESIGN, "\n".join(lines))


def demo(tmp_path: Path, rel: str = DEMO) -> Path:
    return write(tmp_path, rel, "# Dry run on invented data\n\n- orders: 3 in, 3 out\n")


def prototype(tmp_path: Path, version: str = "v1") -> Path:
    folder = tmp_path / "docs" / "design" / "prototype" / version
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def run(tmp_path: Path, *args: str, date: str | None = TODAY):
    extra = ["--date", date] if date is not None else []
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), *args, *extra, "--root", str(tmp_path)],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )


def ready(tmp_path: Path, screens: str = "no") -> None:
    discovery(tmp_path, screens)
    record(tmp_path)


# --- rule 8: work without screens ----------------------------------------------------------------


def test_ac4_a_design_without_screens_and_its_demo_record_passes(tmp_path):
    """REQ-055 AC4: SPEC-0048 rule 8 (`Screens: no`: one `Demo:` line naming a run record)."""
    ready(tmp_path)
    design(tmp_path, f"Demo: {DEMO}")
    demo(tmp_path)
    proc = run(tmp_path, "check-design")
    assert proc.returncode == 0, proc.stdout
    assert "ok front-door: check-design (1 designs)" in proc.stdout


@pytest.mark.parametrize(
    ("lines", "make", "why"),
    [
        ((), False, "no `Demo:` line"),
        ((f"Demo: {DEMO}",), False, "does not exist"),
        (("Demo: docs/notes/orders-demo-1.md",), True, "not a run record under `docs/runs/`"),
        (("Demo: docs/runs/../notes/orders-demo-1.md",), True, "not a run record"),
        ((f"Demo: {DEMO}", f"Demo: {DEMO}"), True, "one `Demo:` line"),
        (("Demo: docs/runs/",), True, "not a run record"),
    ],
)
def test_ac4_a_design_without_screens_and_without_its_demo_fails(tmp_path, lines, make, why):
    """REQ-055 AC4: SPEC-0048 rules 8 and 15 (a missing artifact fails, naming rule and file)."""
    ready(tmp_path)
    design(tmp_path, *lines)
    if make:
        demo(tmp_path)
        demo(tmp_path, "docs/notes/orders-demo-1.md")
    proc = run(tmp_path, "check-design")
    assert proc.returncode == 1
    assert f"FAIL front-door: rule 8: {DESIGN}" in proc.stdout
    assert why in proc.stdout


def test_ac4_a_walkthrough_alone_is_not_the_artifact(tmp_path):
    """REQ-055 AC4: SPEC-0048 rule 8 (a walkthrough is judgement, never the demo's stand-in)."""
    ready(tmp_path)
    design(tmp_path, f"Walkthrough: {PLACE}")
    proc = run(tmp_path, "check-design")
    assert proc.returncode == 1
    assert f"rule 8: {DESIGN}" in proc.stdout and "no `Demo:` line" in proc.stdout
    assert PLACE not in proc.stdout + proc.stderr


def test_ac4_a_walkthrough_beside_the_demo_is_noted_as_judgement(tmp_path):
    """REQ-055 AC4: SPEC-0048 rules 8 and 15 (noted for the conductor; its place never printed)."""
    ready(tmp_path)
    design(tmp_path, f"Demo: {DEMO}", f"Walkthrough: {PLACE}")
    demo(tmp_path)
    proc = run(tmp_path, "check-design")
    assert proc.returncode == 0, proc.stdout
    assert f"note front-door: rule 8: {DESIGN}: a `Walkthrough:` line is judgement" in proc.stdout
    assert PLACE not in proc.stdout + proc.stderr


def test_ac4_an_empty_walkthrough_line_fails(tmp_path):
    """REQ-055 AC4: SPEC-0048 rule 8 (`Walkthrough: <where it is kept>` names a place)."""
    ready(tmp_path)
    design(tmp_path, f"Demo: {DEMO}", "Walkthrough:   ")
    demo(tmp_path)
    proc = run(tmp_path, "check-design")
    assert proc.returncode == 1 and "names no place" in proc.stdout


def test_ac4_the_walkthrough_is_never_opened_and_the_demo_never_run(tmp_path, monkeypatch, capsys):
    """REQ-055 AC4: SPEC-0048 rules 8 and 16 (no check opens a walkthrough or runs a demo)."""
    import front_door

    ready(tmp_path)
    kept = write(tmp_path, "elsewhere/walkthrough.txt", "a recording's notes")
    design(tmp_path, f"Demo: {DEMO}", f"Walkthrough: {kept}")
    demo(tmp_path)
    opened: list[str] = []
    real = Path.read_text

    def spy(self, *a, **k):
        opened.append(str(self))
        return real(self, *a, **k)

    def refuse(*_a, **_k):
        raise AssertionError("a check ran or connected")

    monkeypatch.setattr(Path, "read_text", spy)
    monkeypatch.setattr(subprocess, "run", refuse)
    monkeypatch.setattr(subprocess, "Popen", refuse)
    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    assert front_door.main(["check-design", "--date", TODAY, "--root", str(tmp_path)]) == 0
    assert str(kept) not in opened and not any(p.endswith(DEMO) for p in opened)
    assert "ok front-door: check-design" in capsys.readouterr().out


# --- rule 8: work with screens, and `open` -------------------------------------------------------


@pytest.mark.parametrize("screens", ["yes", "open", None])
def test_ac4_a_design_with_screens_needs_a_prototype_version(tmp_path, screens):
    """REQ-055 AC4: SPEC-0048 rule 8 (`yes`, and `open` or no document read as `yes`)."""
    if screens is None:
        record(tmp_path)
    else:
        ready(tmp_path, screens)
    design(tmp_path)
    proc = run(tmp_path, "check-design")
    assert proc.returncode == 1
    assert f"rule 8: {DESIGN}" in proc.stdout and "no prototype version" in proc.stdout
    prototype(tmp_path)
    assert run(tmp_path, "check-design").returncode == 0


def test_ac4_a_demo_does_not_stand_in_for_a_prototype(tmp_path):
    """REQ-055 AC4: SPEC-0048 rule 8 (`open` is `yes`, the artifact with more to review)."""
    ready(tmp_path, "open")
    design(tmp_path, f"Demo: {DEMO}")
    demo(tmp_path)
    proc = run(tmp_path, "check-design")
    assert proc.returncode == 1 and "no prototype version" in proc.stdout


def test_ac4_a_folder_that_is_not_a_version_is_not_a_prototype(tmp_path):
    """REQ-055 AC4: SPEC-0048 rule 8 (a version folder is `docs/design/prototype/v<n>/`)."""
    ready(tmp_path, "yes")
    design(tmp_path)
    prototype(tmp_path, "draft")
    assert run(tmp_path, "check-design").returncode == 1
    prototype(tmp_path, "v0")
    assert run(tmp_path, "check-design").returncode == 1


# --- rules 1 and 9: the phase, from the files only -----------------------------------------------


def status(tmp_path: Path, *args: str):
    return run(tmp_path, "status", *args)


def test_ac4_status_names_each_phase_in_rule_1_order(tmp_path):
    """REQ-055 AC4: SPEC-0048 rule 1 (each phase starts when the one before has its record)."""
    lines = []
    lines.append(status(tmp_path, SLUG).stdout.strip())
    discovery(tmp_path)
    lines.append(status(tmp_path, SLUG).stdout.strip())
    record(tmp_path)
    lines.append(status(tmp_path, SLUG).stdout.strip())
    design(tmp_path)
    lines.append(status(tmp_path, SLUG).stdout.strip())
    design(tmp_path, f"Demo: {DEMO}")
    demo(tmp_path)
    lines.append(status(tmp_path, SLUG).stdout.strip())
    assert lines == [
        f"{SLUG}: phase 2 discovery; waits for docs/discovery/{SLUG}.md",
        f"{SLUG}: phase 3 research; waits for docs/research/{SLUG}.md",
        f"{SLUG}: phase 4 design; waits for {DESIGN}",
        f"{SLUG}: phase 4 design; waits for its review artifact (rule 8)",
        f"{SLUG}: phase 5 the go; waits for the go",
    ]


def test_ac4_status_waits_for_a_record_that_fails_its_check(tmp_path):
    """REQ-055 AC4: SPEC-0048 rules 1, 5 and 6 (a record that fails is not the phase's record)."""
    path = discovery(tmp_path)
    path.write_text(path.read_text(encoding="utf-8").replace("## Answers", "## Other"), "utf-8")
    out = status(tmp_path, SLUG).stdout
    assert "phase 2 discovery; waits for the discovery document to pass check-discovery" in out
    discovery_again = tmp_path / "again"
    discovery(discovery_again)
    record(discovery_again, accessed="2026-01-01")
    out = status(discovery_again, SLUG).stdout
    assert "phase 3 research; waits for the research record to pass check-research, fresh" in out


def test_ac7_status_never_passes_the_go_and_writes_nothing(tmp_path):
    """REQ-055 AC7: SPEC-0048 rules 9 and 13 (the go is read from saved comments, build (f))."""
    ready(tmp_path, "yes")
    design(tmp_path)
    prototype(tmp_path)
    write(tmp_path, "docs/runs/comment.md", "Approve: SPEC-0099\n")
    before = sorted(p.as_posix() for p in tmp_path.rglob("*"))
    proc = status(tmp_path)
    assert proc.returncode == 0
    assert proc.stdout == f"{SLUG}: phase 5 the go; waits for the go\n"
    assert sorted(p.as_posix() for p in tmp_path.rglob("*")) == before


def test_ac4_status_lists_every_discovery_document_by_default(tmp_path):
    """REQ-055 AC4: SPEC-0048 rule 1 (one line per problem, from `docs/discovery/`)."""
    ready(tmp_path)
    write(tmp_path, "docs/discovery/another-problem.md", "# Discovery: another\n")
    proc = status(tmp_path)
    assert proc.returncode == 0
    assert proc.stdout.splitlines() == [
        "another-problem: phase 2 discovery; waits for the discovery document to pass"
        " check-discovery",
        f"{SLUG}: phase 4 design; waits for {DESIGN}",
    ]
    (tmp_path / "empty").mkdir()
    assert status(tmp_path / "empty").stdout == "ok front-door: no discovery document\n"


@pytest.mark.parametrize("args", [(), ("Not A Slug",), ("../up",)])
def test_ac4_status_needs_the_date_and_a_slug_shape(tmp_path, args):
    """REQ-055 AC4: SPEC-0048 rules 6 and 15 (`--date` from `date -u`; a slug is a file name)."""
    if args:
        proc = status(tmp_path, *args)
    else:
        proc = run(tmp_path, "status", date=None)
    assert proc.returncode == 2 and "usage" in proc.stderr
