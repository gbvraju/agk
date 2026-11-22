"""Tests of the foundation's basics (SPEC-0072 rule 4 as amendment 202 proposes; REQ-079;
brief #1594, ADR-0674).

On a sample web app, API service and report tool, `basics.py write` writes the ignore line, the
names-only example settings file, the startup check, the safe request log, the health address
(servers only), the README and `docs/deploy.md`; the environment file is ignored, a missing
setting stops the app naming the setting, an error with `ana@example.com` leaves the address out
of the log, the health address answers, the README's command runs, the report tool writes one run
line and exits non-zero on a failed run, an adopted project gets proposals and no file, and
`check_plan.py` refuses a first milestone with no slice brief. Invented data only (example.com);
fixtures in `tmp_path`; the only process started is the sample's own module; no network.
"""

from __future__ import annotations

import importlib.util
import io
import os
import re
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
AGK = KIT_ROOT / "scripts" / "agk"
sys.path.insert(0, str(AGK))

import basics  # noqa: E402
import check_plan  # noqa: E402
from gates import committed_secrets, environment_settings  # noqa: E402
from test_pins import record  # noqa: E402

STACK = "docs/adr/0002-stack-options.md"
LOCAL = "APP_ENV=local\nDATABASE_PATH=local.db\nPORT=8000\n"
NAME_LINE = re.compile(r"^[A-Z][A-Z0-9_]*=(<[^<>]+>)?$")
PACKAGE = {"web-app": "backend", "api-service": "api", "data-pipeline": "job"}


def git(root: Path, *args: str) -> str:
    done = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True, text=True, check=False
    )
    return done.stdout


def project(tmp: Path, work_type: str | None = "web-app", mode: str = "init") -> Path:
    root = tmp / "sample"
    (root / "docs" / "adr").mkdir(parents=True)
    shutil.copytree(KIT_ROOT / "config" / "playbooks", root / "config" / "playbooks")
    toml = f'default_branch = "main"\nmode = "{mode}"\n'
    if work_type:
        toml += f'\n[delivery]\nwork_type = "{work_type}"\n'
    (root / "agk.toml").write_text(toml, encoding="utf-8")
    (root / STACK).write_text(record(status="Accepted", chosen="Option A"), encoding="utf-8")
    shutil.copyfile(KIT_ROOT / "kit" / "templates" / "gitignore", root / ".gitignore")
    git(root, "init", "-q")
    return root


def written(tmp: Path, work_type: str) -> Path:
    root = project(tmp, work_type)
    assert basics.main(["write", "--root", str(root)]) == 0
    return root


def run_module(root: Path, *args: str, env: str = LOCAL) -> subprocess.CompletedProcess:
    (root / ".env").write_text(env, encoding="utf-8")
    clean = {k: v for k, v in os.environ.items() if k not in ("APP_ENV", "DATABASE_PATH", "PORT")}
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-m", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        env=clean,
        timeout=60,
    )


def readme_command(root: Path, label: str) -> list[str]:
    """The bash command of the README line that starts with LABEL, as an argument list."""
    text = (root / "README.md").read_text(encoding="utf-8")
    line = next(ln for ln in text.splitlines() if ln.startswith(label))
    command = re.search(r"`([^`]+)`", line).group(1).split()
    assert command[:2] == ["python3", "-m"], line
    return command[2:]


@pytest.mark.parametrize("work_type", sorted(PACKAGE))
def test_req079_the_environment_file_is_ignored_and_the_example_holds_names_only(
    tmp_path, work_type
):
    """REQ-079 AC3: answer 1 (a) and (b); the `secrets` and `environment-settings` steps pass."""
    root = written(tmp_path, work_type)
    (root / ".env").write_text(LOCAL, encoding="utf-8")
    assert git(root, "check-ignore", ".env").strip() == ".env"
    assert git(root, "check-ignore", ".env.example").strip() == ""
    lines = (root / ".env.example").read_text(encoding="utf-8").splitlines()
    names = [ln for ln in lines if ln.strip() and not ln.startswith("#")]
    assert names and all(NAME_LINE.match(ln) for ln in names), names
    assert b"\r\n" not in (root / ".env.example").read_bytes()
    git(root, "add", "-A")
    playbook = {}
    assert committed_secrets.check(root, playbook) == []
    assert environment_settings.check(root, playbook) == []


def test_req079_the_template_ignore_and_line_end_lines():
    """REQ-079 AC3: answer 1 (a) and answer 5 (LF line ends of the example file)."""
    templates = KIT_ROOT / "kit" / "templates"
    assert ".env" in (templates / "gitignore").read_text(encoding="utf-8").splitlines()
    attributes = (templates / "gitattributes").read_text(encoding="utf-8").splitlines()
    assert ".env.example text eol=lf" in attributes


@pytest.mark.parametrize("work_type", sorted(PACKAGE))
def test_req079_a_missing_setting_stops_the_app_naming_the_setting(tmp_path, work_type):
    """REQ-079 AC3: answer 1 (c) (the startup check names the setting, never a value)."""
    root = written(tmp_path, work_type)
    done = run_module(root, PACKAGE[work_type], "--check", env="APP_ENV=local\nPORT=8000\n")
    assert done.returncode != 0
    assert "DATABASE_PATH" in done.stderr or work_type == "data-pipeline"
    done = run_module(root, PACKAGE[work_type], "--check", env="DATABASE_PATH=local.db\n")
    assert done.returncode != 0 and "APP_ENV" in done.stderr
    assert "local.db" not in done.stderr


@pytest.mark.parametrize("work_type", ["web-app", "api-service"])
def test_req079_the_health_address_answers_and_the_readme_command_runs(tmp_path, work_type):
    """REQ-079 AC3: answer 1 (e) and (f); answer 3 (a web app and an API service)."""
    root = written(tmp_path, work_type)
    done = run_module(root, *readme_command(root, "Check it:"))
    assert done.returncode == 0, done.stderr
    assert '"status": "ok"' in done.stdout and '"database": "ok"' in done.stdout
    assert re.search(r"request_id=\w+ method=GET path=/health status=200", done.stderr)


def test_req079_a_request_id_is_never_read_as_personal_data():
    """REQ-079 AC3: answer 1 (d); brief #1655 (a random hex id was read as a phone number).

    The id stays random and 12 characters long, but is letters only, so the log's own guard
    (`scrub`) never changes it, and the log lines keep the id the user is shown.
    """
    source = KIT_ROOT / "kit" / "templates" / "skeleton" / "python" / "common" / "logs.py"
    spec = importlib.util.spec_from_file_location("skeleton_logs_1655", source)
    assert spec and spec.loader
    logs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(logs)
    ids = [logs.new_id() for _ in range(20000)]
    assert all(re.fullmatch(r"[a-z]{12}", one) for one in ids)
    assert all(logs.scrub(one) == one for one in ids)
    assert len(set(ids)) == len(ids)
    assert logs.scrub("call +44 20 7946 0000") == "call <phone>"


@pytest.mark.parametrize("work_type", ["web-app", "api-service"])
def test_req079_an_error_leaves_the_address_out_of_the_log(tmp_path, work_type):
    """REQ-079 AC3: answer 1 (d) (a plain message to the user, the detail only in the log)."""
    root = written(tmp_path, work_type)
    sys.path.insert(0, str(root))
    try:
        app = __import__(f"{PACKAGE[work_type]}.app", fromlist=["make_app"])
        logs = __import__(f"{PACKAGE[work_type]}.logs", fromlist=["setup"])
    finally:
        sys.path.remove(str(root))
    stream = io.StringIO()
    logs.setup(stream)

    def broken(settings, environ):
        raise ValueError("no booking for ana@example.com")

    wsgi = app.make_app({"DATABASE_PATH": str(root / "local.db")}, {"/bookings": broken})
    seen: list[str] = []
    body = b"".join(
        wsgi(
            {
                "PATH_INFO": "/bookings",
                "REQUEST_METHOD": "GET",
                "QUERY_STRING": "who=ana@example.com",
            },
            lambda status, headers: seen.append(status),
        )
    ).decode("utf-8")
    log = stream.getvalue()
    for name in [n for n in sys.modules if n.split(".")[0] == PACKAGE[work_type]]:
        del sys.modules[name]
    assert seen == ["500 Internal Server Error"]
    assert "ana@example.com" not in body and "ValueError" not in body and "request id" in body
    assert "ana@example.com" not in log and "ValueError" in log
    assert re.search(r"request_id=\w+ method=GET path=/bookings status=500", log)


def test_req079_the_report_tool_writes_one_run_line_and_fails_non_zero(tmp_path):
    """REQ-079 AC3: answer 3 (a data or report tool: no health address, one run line, exit code)."""
    root = written(tmp_path, "data-pipeline")
    assert not (root / "job" / "app.py").exists()
    done = run_module(root, *readme_command(root, "Run it:"))
    assert done.returncode == 0, done.stderr
    run_lines = [ln for ln in done.stderr.splitlines() if "run_id=" in ln]
    assert len(run_lines) == 1 and "status=ok" in run_lines[0] and "rows=3" in run_lines[0]
    assert "ana@example.com" not in done.stderr + done.stdout
    done = run_module(root, "job", "samples/missing.csv")
    run_lines = [ln for ln in done.stderr.splitlines() if "run_id=" in ln]
    assert done.returncode == 1 and len(run_lines) == 1 and "status=failed" in run_lines[0]


@pytest.mark.parametrize("work_type", sorted(PACKAGE))
def test_req079_the_readme_and_the_deploy_step(tmp_path, work_type):
    """REQ-079 AC3: answer 1 (f) and (g), answer 2 (a deploy is the person's own act) and `Q-2`."""
    root = written(tmp_path, work_type)
    readme = (root / "README.md").read_text(encoding="utf-8")
    for label in ("Run it:", "Run it (PowerShell):", "Test it:", "Test it (PowerShell):"):
        assert any(ln.startswith(label) for ln in readme.splitlines()), label
    deploy = (root / "docs" / "deploy.md").read_text(encoding="utf-8")
    assert "Where it runs: local only" in deploy
    assert "{{" not in readme + deploy


def test_req079_nothing_is_written_over_an_existing_file(tmp_path):
    """REQ-079 AC3: answer 1 (the foundation never writes over a project's own file)."""
    root = project(tmp_path)
    (root / "README.md").write_text("# My own readme\n", encoding="utf-8")
    assert basics.main(["write", "--root", str(root)]) == 0
    assert (root / "README.md").read_text(encoding="utf-8") == "# My own readme\n"
    assert (root / "docs" / "deploy.md").is_file()


def test_req079_adopt_proposes_each_missing_part_and_writes_nothing(tmp_path, capsys):
    """REQ-079 AC3: answer 4 (`mode = "adopt"`: one plain betterment per missing part)."""
    root = project(tmp_path, mode="adopt")
    before = sorted(p.relative_to(root) for p in root.rglob("*") if ".git" not in p.parts)
    assert basics.main(["write", "--root", str(root)]) == 0
    out = capsys.readouterr().out
    after = sorted(p.relative_to(root) for p in root.rglob("*") if ".git" not in p.parts)
    assert before == after
    assert "Your project has no health check. Shall I add one? Yes (recommended) · later" in out


def test_req079_a_tracked_environment_file_is_named_never_removed(tmp_path, capsys):
    """REQ-079 AC3: `Q-1` (a tracked environment file is named to the person, never removed)."""
    root = project(tmp_path)
    (root / ".env").write_text(LOCAL, encoding="utf-8")
    git(root, "add", "-f", ".env")
    assert basics.main(["write", "--root", str(root)]) == 0
    assert "a tracked environment file (path class: .env)" in capsys.readouterr().out
    assert git(root, "ls-files", ".env").strip() == ".env"


def test_req079_no_work_type_and_other_shapes_are_said_plainly(tmp_path, capsys):
    """REQ-079 AC3: answer 4 (`[delivery] work_type` picks the shape's parts)."""
    root = project(tmp_path, work_type=None)
    assert basics.main(["write", "--root", str(root)]) == 0
    assert capsys.readouterr().out.strip() == "basics: not run: no work type (setting: work_type)"
    assert not (root / "README.md").exists()
    other = project(tmp_path / "other", work_type="mobile")
    assert basics.main(["write", "--root", str(other)]) == 0
    out = capsys.readouterr().out
    assert "not written: basics: no skeleton for this work type yet (setting: work_type)" in out
    assert "wrote .gitignore" not in out and not (other / "README.md").exists()


# --- check_plan: the first milestone ends with one working slice ----------------------------------


def brief_file(root: Path, key: str, milestone: str, *lines: str) -> None:
    body = "\n".join([f"# {key}", "", f"Milestone: {milestone}", *lines]) + "\n"
    (root / f"docs/plan/briefs/{milestone}").mkdir(parents=True, exist_ok=True)
    (root / f"docs/plan/briefs/{milestone}/{key}.md").write_text(body, encoding="utf-8")


def plan_root(tmp_path: Path, work_type: str | None = "web-app") -> Path:
    root = project(tmp_path, work_type)
    (root / "docs/plan").mkdir(parents=True, exist_ok=True)
    (root / "docs/plan/milestones.md").write_text(
        "# Milestones\n\n### M1 Foundation\n\n### M2 Orders\n", encoding="utf-8"
    )
    return root


def test_req079_check_plan_refuses_a_first_milestone_without_a_slice_brief(tmp_path):
    """REQ-079 AC3: answer 2 (`check_plan.py` refuses an `M1` with no slice brief)."""
    root = plan_root(tmp_path)
    brief_file(root, "B1", "M1", "Kind: foundation")
    brief_file(root, "B2", "M2", "Depends-on: B1")
    assert check_plan.slice_brief_problems(root) == [
        "SPEC-0072 rule 4: docs/plan/briefs: the first milestone has no Kind: slice brief"
        " after the foundation (setting: work_type)"
    ]


def test_req079_check_plan_accepts_a_slice_brief_after_the_foundation(tmp_path):
    """REQ-079 AC3: answer 2 (the foundation brief and one first-slice brief in `M1`)."""
    root = plan_root(tmp_path)
    brief_file(root, "B1", "M1", "Kind: foundation")
    brief_file(root, "B2", "M1", "Depends-on: B1", "Kind: slice")
    assert check_plan.slice_brief_problems(root) == []
    assert check_plan.foundation_problems(root) == []


def test_req079_check_plan_holds_nothing_without_a_work_type_or_a_foundation(tmp_path):
    """REQ-079 AC3: answer 2 (only a work-type plan with its foundation brief is read)."""
    root = plan_root(tmp_path, work_type=None)
    brief_file(root, "B2", "M1")
    assert check_plan.slice_brief_problems(root) == []
    assert check_plan.slice_brief_problems(plan_root(tmp_path / "empty")) == []


def test_req079_render_writes_the_kind_line_of_the_slice_brief():
    """REQ-079 AC3: answer 2 (`plan-intake` proposes the first slice; render writes it)."""
    import plan_intake
    from test_foundation_kind import foundation_plan

    data = foundation_plan()
    data["briefs"][1]["slice"] = True
    assert "\nKind: slice\n" in plan_intake.brief_text(data, data["briefs"][1])
    assert "Kind: slice" not in plan_intake.brief_text(data, data["briefs"][0])


def pack_entry() -> dict:
    """The `python-pyproject` entry the API service's playbook carries (brief #1683)."""
    import check_playbooks

    playbook = KIT_ROOT / "config" / "playbooks" / "api-service.toml"
    packs = check_playbooks.standard(playbook, KIT_ROOT)[1]
    return next(e for e in packs if e["stack"] == "python-pyproject")


@pytest.mark.parametrize("own", [False, True])
@pytest.mark.parametrize("crlf", [False, True])
@pytest.mark.parametrize("work_type", sorted(PACKAGE))
def test_req079_the_written_skeleton_passes_the_standards_pack(tmp_path, work_type, crlf, own):
    """REQ-079 AC4: brief #1683 answers 1, 3 and 4: each shape the foundation writes, with the
    stack's `pyproject.toml`, passes `python_pack.run` with no failure line; with
    `project_lint_paths` set or unset, and with Windows line ends."""
    from gates import python_pack

    root = written(tmp_path, work_type)
    stack = KIT_ROOT / "kit" / "templates" / "stacks" / "python-pyproject" / "pyproject.toml"
    text = stack.read_text(encoding="utf-8").replace("{{project}}", "sample")
    (root / "pyproject.toml").write_text(text, encoding="utf-8")
    if own:
        toml = (root / "agk.toml").read_text(encoding="utf-8")
        line = f'project_lint_paths = ["{PACKAGE[work_type]}/**"]\n'
        (root / "agk.toml").write_text(line + toml, encoding="utf-8")
    found = python_pack.files(root, python_pack.patterns(root))
    assert {rel.split("/")[0] for rel, _ in found} == {PACKAGE[work_type]}
    if crlf:
        for rel, _ in found:
            path = root / rel
            path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    steps = python_pack.run(root, pack_entry())
    assert [s for s, _ in steps] == ["floor", "lint", "format", "type"]
    assert [line for _, lines in steps for line in lines] == []
