"""Every session the kit starts names its agent (SPEC-0066 rules 5 and 11, build (a); brief #1582).

REQ-073 AC4. Both adapters pass `--agent "$AGK_AGENT"` beside `--model` and `--effort`, and
refuse to start, naming the setting, when `AGK_AGENT` is not set. Every kit start sets
`AGK_AGENT`: builders `builder`, `launch.py role` the role, the conductor's own starts
`conductor` and its reviewers `architect-review`. The cloud task texts name their agent on their
first line, `.claude/agents/builder.md` gives a builder start a role to name, and a scan of the
kit's start paths fails on a `claude` start without `--agent`. `doctor.py` warns, naming
`flow.launch_adapter`, about a project's own adapter that does not pass it. A `claude` test
double records its arguments; no network, no model, invented data only.
"""

from __future__ import annotations

import ast
import json
import os
import re
import shutil
import stat
import subprocess  # nosec B404 - fixed argument lists only, no shell
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
POSIX = ROOT / "kit" / "templates" / "start-session-local.sh"
WINDOWS = ROOT / "kit" / "templates" / "start-session-windows.ps1"
OWN_WINDOWS = ROOT / "scripts" / "start-session-windows.ps1"
RUNTIME = ROOT / "kit" / "templates" / "runtime"
GUIDES = ROOT / "docs" / "guides"
STARTERS = ("launch.py", "conductor.py", "autopilot.py")
AGENTS = {"builder.txt": "builder", "conductor.txt": "conductor", "launcher.txt": "conductor"}


# --- the scan of the kit's start paths ----------------------------------------------------------

START = re.compile(r"(?<![\w./-])claude(?=[ \t])[^\n`|;]*")


def unnamed_starts(text: str) -> list[str]:
    """Each `claude ... -p` start in TEXT (a script, or a guide's code) that names no agent."""
    found = (m.group(0) for m in START.finditer(text))
    return [cmd for cmd in found if re.search(r"\s-p\b", cmd) and "--agent" not in cmd]


def guide_code(text: str) -> str:
    """A guide's fenced code and its inline code spans: where a documented command stands."""
    fenced = re.findall(r"```[^\n]*\n(.*?)```", text, re.S)
    spans = re.findall(r"`([^`\n]+)`", re.sub(r"```.*?```", "", text, flags=re.S))
    return "\n".join([*fenced, *spans])


def start_paths() -> dict[str, str]:
    """The kit's start paths and their text: the adapters, the runtime texts, the starters and
    every guide's documented commands (SPEC-0066 rule 5)."""
    paths = [POSIX, WINDOWS, OWN_WINDOWS, *sorted(RUNTIME.glob("*.txt"))]
    paths += [ROOT / "scripts" / "agk" / name for name in STARTERS]
    found = {p.relative_to(ROOT).as_posix(): p.read_text(encoding="utf-8") for p in paths}
    for guide in sorted(GUIDES.glob("*.md")):
        found[guide.relative_to(ROOT).as_posix()] = guide_code(guide.read_text(encoding="utf-8"))
    return found


def test_the_scan_fails_on_a_claude_start_without_an_agent():
    """REQ-073 AC4: the check of the scan itself, on invented lines."""
    assert unnamed_starts('claude "${flags[@]}" -p "$prompt"') != []
    assert unnamed_starts("& claude @flags -p $prompt") != []
    assert unnamed_starts('claude -p "Run exactly this command"') != []
    assert unnamed_starts('claude --agent "${11}" "${flags[@]}" -p "$prompt"') == []
    assert unnamed_starts("& claude --agent $Agent @flags -p $prompt") == []
    assert unnamed_starts('claude -p --agent conductor "/agk:review-pass"') == []
    assert unnamed_starts("claude --agent steward") == []  # interactive, not a -p start
    assert unnamed_starts("python3 scripts/agk/setup.py claude -version") == []


def test_every_kit_start_path_names_its_agent():
    """REQ-073 AC4: no adapter, runtime text, starter or documented example starts `claude`
    without `--agent` (SPEC-0066 rule 5)."""
    bad = {path: found for path, text in start_paths().items() if (found := unnamed_starts(text))}
    assert bad == {}


def adapter_starts(path: Path) -> list[ast.FunctionDef]:
    """The functions of PATH that call the adapter with a session's environment."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        body = ast.unparse(fn)
        if "subprocess.run(" in body and "AGK_SESSION" in body:
            out.append(fn)
    return out


@pytest.mark.parametrize("name", STARTERS)
def test_every_start_of_the_starters_sets_the_agent(name):
    """REQ-073 AC4: each function of launch.py, conductor.py and autopilot.py that hands the
    adapter a session also hands it `AGK_AGENT`."""
    path = ROOT / "scripts" / "agk" / name
    missing = [fn.name for fn in adapter_starts(path) if "AGK_AGENT" not in ast.unparse(fn)]
    assert missing == []


def test_the_conductors_own_starts_set_the_conductor_agent():
    """REQ-073 AC4: the watchdog's and the supervisor's conductor jobs run as `conductor`, its
    reviewers as `architect-review` (Q-S0066-4: `AGK_ROLE` keeps its meaning)."""
    import conductor

    starts = {fn.name: ast.unparse(fn) for fn in adapter_starts(Path(conductor.__file__))}
    conducting = [body for body in starts.values() if "AGK_ROLE='conductor'" in body]
    assert len(conducting) == 2, sorted(starts)
    for body in conducting:
        assert "AGK_AGENT='conductor'" in body
    assert conductor.REVIEW_AGENT == "architect-review"
    assert "AGK_AGENT=REVIEW_AGENT" in starts["start_reviewer"]


def test_personal_mode_starts_no_session_of_its_own():
    """REQ-073 AC4: in personal mode (`forge = "files"`) the personal scripts start no
    `claude`; the autopilot's builder jobs there go through `launch.start_with`."""
    for path in sorted((ROOT / "scripts" / "agk").glob("personal*.py")):
        text = path.read_text(encoding="utf-8")
        assert unnamed_starts(text) == [], path.name
        assert adapter_starts(path) == [], path.name


# --- launch.py: every start sets AGK_AGENT ------------------------------------------------------


class Seen:
    def __init__(self):
        self.calls: list[dict] = []

    def __call__(self, words, **kw):
        self.calls.append({"words": words, "env": kw["env"], "input": kw["input"]})
        return subprocess.CompletedProcess(words, 0, "", "")


def test_a_builder_start_names_the_builder_agent(monkeypatch, tmp_path):
    """REQ-073 AC4: `launch.start_with` (the builders and fix jobs, the autopilot's too)
    hands the adapter `AGK_AGENT=builder`, beside today's variables."""
    import launch

    seen = Seen()
    monkeypatch.setattr(launch.subprocess, "run", seen)
    monkeypatch.setattr(launch, "show_jobs", lambda root: False)
    monkeypatch.setattr(launch, "has_process", lambda worktree: False)
    code = launch.start_with("adapter-example", [("cb-example-1", 7, None)], ["build it"],
                             root=tmp_path, jobs=[("fix", 8)])  # fmt: skip
    assert code == 0
    env = seen.calls[0]["env"]
    assert env["AGK_AGENT"] == "builder" and env["AGK_SESSION"] == "cb-example-1"
    assert env["AGK_JOB_KIND"] == "fix"


@pytest.mark.parametrize("role", ["steward", "conductor"])
def test_a_role_start_names_its_agent_and_the_prompt_says_so(monkeypatch, tmp_path, role):
    """REQ-073 AC4: `launch.py role` hands `AGK_AGENT=<role>`, and `ROLE_PROMPT` says which
    agent the session runs as instead of asking it to start itself."""
    import launch

    seen = Seen()
    monkeypatch.setattr(launch.subprocess, "run", seen)
    monkeypatch.setattr(launch, "show_jobs", lambda root: False)
    monkeypatch.setattr(launch, "has_process", lambda worktree: False)
    monkeypatch.setattr(launch, "memory_allows", lambda root: True)
    monkeypatch.setattr(launch, "live_conductors", lambda root: [])
    monkeypatch.setattr(launch, "conductor_refusal", lambda root: None)
    args = ["role", "--role", role, "--session", "cb-example-2", "--adapter", "adapter-example"]
    assert launch.role_main(args, root=tmp_path) == 0
    call = seen.calls[0]
    assert call["env"]["AGK_AGENT"] == role and call["env"]["AGK_ROLE"] == role
    assert "Start the role with" not in call["input"]
    assert f"`{role}` agent" in call["input"]
    assert f".claude/agents/{role}.md" in call["input"]


# --- the POSIX adapter, with a claude double ----------------------------------------------------


def git_in(where: Path, *args: str) -> str:
    done = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=where, check=True, capture_output=True, text=True
    )
    return done.stdout


@pytest.fixture
def posix(tmp_path):
    """A clone with an origin, the POSIX adapter in it, and a `claude` double on PATH."""
    if shutil.which("bash") is None:
        pytest.skip("needs bash")
    origin, work = tmp_path / "origin.git", tmp_path / "proj"
    git_in(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    git_in(tmp_path, "clone", "-q", str(origin), str(work))
    for args in (
        ["config", "user.email", "t@example.invalid"],
        ["config", "user.name", "t"],
        ["config", "commit.gpgsign", "false"],
        ["commit", "-q", "--allow-empty", "-m", "first"],
        ["push", "-q", "origin", "HEAD:main"],
    ):
        git_in(work, *args)
    (work / "start-session-local.sh").write_text(POSIX.read_text(encoding="utf-8"), "utf-8")
    fake = tmp_path / "bin"
    fake.mkdir()
    claude = fake / "claude"
    claude.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$CLAUDE_SEEN"\nexit 0\n', "utf-8")
    claude.chmod(claude.stat().st_mode | stat.S_IXUSR)
    drop = ("DISPLAY", "WAYLAND_DISPLAY", "AGK_MODEL", "AGK_EFFORT", "AGK_AGENT")
    env = {k: v for k, v in os.environ.items() if k not in drop}
    env.update(PATH=f"{fake}{os.pathsep}{env['PATH']}", AGK_SESSION="cb-example-3",
               CLAUDE_SEEN=str(tmp_path / "seen.txt"))  # fmt: skip
    return {"work": work, "env": env, "worktree": tmp_path / "agk-cb-example-3", "tmp": tmp_path}


def start_posix(posix, **extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["bash", str(posix["work"] / "start-session-local.sh")], cwd=posix["work"],
        input="build it", text=True, env={**posix["env"], **extra}, capture_output=True,
        timeout=60,
    )  # fmt: skip


def seen_args(posix) -> list[str]:
    exit_file = posix["worktree"] / ".agk-session-exit"
    for _ in range(300):
        if exit_file.exists() and "ended_utc=" in exit_file.read_text(encoding="utf-8"):
            break
        time.sleep(0.1)
    return (posix["tmp"] / "seen.txt").read_text(encoding="utf-8").splitlines()


@pytest.mark.parametrize(
    "extra, expected",
    [
        ({"AGK_AGENT": "builder"}, ["--agent", "builder", "-p", "build it"]),
        (
            {"AGK_AGENT": "architect-review", "AGK_MODEL": "example-mid-1", "AGK_EFFORT": "low"},
            ["--agent", "architect-review", "--model", "example-mid-1", "--effort", "low",
             "-p", "build it"],
        ),  # fmt: skip
    ],
)
def test_the_posix_adapter_passes_the_agent(posix, extra, expected):
    """REQ-073 AC4: `--agent "$AGK_AGENT"` beside `--model` and `--effort`."""
    done = start_posix(posix, **extra)
    assert done.returncode == 0, done.stderr
    assert seen_args(posix) == expected


def test_the_posix_adapter_refuses_without_an_agent_naming_the_setting(posix):
    """REQ-073 AC4: no `AGK_AGENT`: one line naming the setting, exit 1, nothing started."""
    done = start_posix(posix)
    assert done.returncode == 1
    lines = done.stderr.strip().splitlines()
    assert len(lines) == 1 and "(setting: AGK_AGENT)" in lines[0]
    assert not posix["worktree"].exists()
    assert not (posix["tmp"] / "seen.txt").exists()


def test_the_posix_adapter_uses_no_gnu_only_flag():
    """REQ-073 AC4: the agent lines are POSIX shell, so the adapter runs on macOS as on WSL."""
    lines = [ln for ln in POSIX.read_text(encoding="utf-8").splitlines() if "agent" in ln.lower()]
    assert lines
    for line in lines:
        assert not re.search(r"\b(?:readlink -f|sed -i|grep -P|date -d)\b", line), line


# --- the Windows adapter ------------------------------------------------------------------------


def wrapper_of(script: str) -> str:
    found = re.search(r"@'\n(.*?)\n'@", script, re.S)
    assert found, "the adapter writes no wrapper"
    return found.group(1)


@pytest.mark.parametrize("path", [WINDOWS, OWN_WINDOWS])
def test_the_windows_adapter_passes_the_agent_and_refuses_without_one(path):
    """REQ-073 AC4: the wrapper takes the agent as an argument before the optional model and
    effort, starts `claude --agent $Agent`, and the adapter refuses without `AGK_AGENT`."""
    script = path.read_text(encoding="utf-8")
    wrapper = wrapper_of(script)
    params = "param($Worktree, $PromptFile, $LongTemp, $Session, $Brief, $Agent, $Model, $Effort)"
    assert wrapper.splitlines()[0] == params
    assert "& claude --agent $Agent @flags -p $prompt" in wrapper
    head = script[: script.find("$prompt = [Console]::In.ReadToEnd()")]
    assert "$env:AGK_AGENT" in head and "(setting: AGK_AGENT)" in head and "exit 1" in head
    tab = script[script.find("wt -w 0 new-tab") :]
    assert "$brief $agent @extra" in tab
    assert "$session, $brief, $agent)" in tab


def test_the_guide_shows_the_windows_adapter_as_installed():
    """REQ-073 AC4: the guide's copy of the adapter carries the same agent lines."""
    guide = (GUIDES / "getting-started.md").read_text(encoding="utf-8")
    assert "& claude --agent $Agent @flags -p $prompt" in guide
    assert "(setting: AGK_AGENT)" in guide


@pytest.mark.skipif(shutil.which("pwsh") is None, reason="needs PowerShell 7 (pwsh)")
def test_the_windows_wrapper_passes_the_agent_when_run(tmp_path):
    """REQ-073 AC4: the wrapper, run under pwsh with the `claude` double, passes the agent."""
    wrapper = wrapper_of(WINDOWS.read_text(encoding="utf-8"))
    wrapper = re.sub(r"\$env:Path = .*?\n.*?\n", "", wrapper, count=1)
    run = tmp_path / "run.ps1"
    run.write_text(wrapper, encoding="utf-8")
    (tmp_path / "prompt.txt").write_text("build it", encoding="utf-8")
    (tmp_path / "job.txt").write_text("kind=build", encoding="utf-8")
    fake = tmp_path / "bin"
    fake.mkdir()
    claude = fake / "claude"
    claude.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$CLAUDE_SEEN"\n', "utf-8")
    claude.chmod(claude.stat().st_mode | stat.S_IXUSR)
    env = {**os.environ, "PATH": f"{fake}{os.pathsep}{os.environ['PATH']}",
           "CLAUDE_SEEN": str(tmp_path / "seen.txt")}  # fmt: skip
    subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["pwsh", "-NoProfile", "-File", str(run), str(tmp_path), str(tmp_path / "prompt.txt"),
         str(tmp_path), "cb-example-4", "9", "builder"],
        env=env, capture_output=True, text=True, timeout=60,
    )  # fmt: skip
    seen = (tmp_path / "seen.txt").read_text(encoding="utf-8").split()
    assert seen[:2] == ["--agent", "builder"]


# --- the cloud task texts and the builder agent -------------------------------------------------


@pytest.mark.parametrize("name, agent", sorted(AGENTS.items()))
def test_each_cloud_task_text_names_its_agent_on_its_first_line(name, agent):
    """REQ-073 AC4: the first line names the agent and its file, with the cloud's own way of
    setting it marked (verify) (Q-S0066-5)."""
    first = (RUNTIME / name).read_text(encoding="utf-8").splitlines()[0]
    assert first.startswith(f"Agent: {agent} (`.claude/agents/{agent}.md`"), first
    assert "(verify" in first
    assert (ROOT / ".claude" / "agents" / f"{agent}.md").is_file()


def test_the_builder_agent_refers_to_its_rules_and_ships_verbatim():
    """REQ-073 AC4: `.claude/agents/builder.md` names the builder's rules by reference (the
    session rules, SPEC-0061 rule 7, the task text), never a second copy, and the kit ships it."""
    text = (ROOT / ".claude" / "agents" / "builder.md").read_text(encoding="utf-8")
    front = text.split("---")[1]
    assert re.search(r"^name: builder$", front, re.M)
    assert re.search(r"^description: .+", front, re.M)
    for ref in ("config/session-rules.md", "SPEC-0061 rule 7", "kit/templates/runtime/builder.txt",
                "Report: <head> handing over: <reason>", "Who: AGK builder"):  # fmt: skip
        assert ref in text, ref
    assert "permissionMode" not in front and "bypass" not in text.lower()
    assert len(text.splitlines()) <= 40  # by reference, not a copy of the rules
    rules = (ROOT / "config" / "session-rules.md").read_text(encoding="utf-8")
    long_rules = [ln for ln in rules.splitlines() if len(ln) > 200]
    assert not any(ln in text for ln in long_rules)
    manifest = json.loads((ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert ".claude/agents/builder.md" in manifest["verbatim"]


# --- doctor.py: a project's own adapter without --agent -----------------------------------------


def project_with(tmp_path: Path, adapter_text: str) -> Path:
    root = tmp_path / "proj"
    (root / "scripts").mkdir(parents=True)
    (root / "agk.toml").write_text(
        '[flow]\nauto_start = true\nlaunch_adapter = "bash scripts/own-adapter.sh"\n', "utf-8"
    )
    (root / "scripts" / "own-adapter.sh").write_text(adapter_text, encoding="utf-8")
    return root


def test_doctor_warns_about_an_own_adapter_that_names_no_agent(tmp_path):
    """REQ-073 AC4 (Q-1582-1, the brief's recommendation): a warning naming the setting, never
    a refusal, and never the command."""
    import doctor

    root = project_with(tmp_path, '#!/bin/sh\nclaude -p "$(cat)"\n')
    got = doctor.launch_adapter_result(root)
    assert got.status == "fail" and "(setting: flow.launch_adapter)" in got.message
    assert "own-adapter" not in got.message
    assert doctor.CHECKS["launch-adapter"][0] == "warn"


def test_doctor_is_quiet_about_an_own_adapter_that_names_the_agent(tmp_path):
    """REQ-073 AC4: an adapter that passes `--agent` is ok."""
    import doctor

    root = project_with(tmp_path, '#!/bin/sh\nclaude --agent "$AGK_AGENT" -p "$(cat)"\n')
    assert doctor.launch_adapter_result(root, cloud=False).status == "ok"
