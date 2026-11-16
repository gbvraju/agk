"""Docker as a choice of container engine beside Podman, with the same checks (brief #1379,
ADR-0579; REQ-050).

Answer 6: recorded doubles of `docker` and `podman` on the PATH stand in for the engines, so no
container engine runs in CI. `scripts/agk/wsl.py engine` reads the project's files and the
machine's engines and recommends one (answer 1); the group or rootless line (answer 2), the Docker
Desktop line that points to Docker's page and states no terms (answer 3), the never-two-engines
rule and the read-only volume list (answer 4) and the `podman-docker` line (answer 5) are its
output. `scripts/agk/wsl_setup.ps1` is read as text: the Docker steps check first, and nothing is
ever deleted or uninstalled. Invented names of example.com; no network, no model.
"""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import wsl  # noqa: E402

PS1 = SCRIPTS / "wsl_setup.ps1"
SKILL = ROOT / "skills" / "wsl" / "SKILL.md"

DOUBLE = r"""#!/usr/bin/env python3
import json, os, sys
name = os.path.basename(sys.argv[0])
args = sys.argv[1:]
with open(os.environ["FAKE_ENGINE_CALLS"], "a", encoding="utf-8") as f:
    f.write(json.dumps([name] + args) + "\n")
answers = json.loads(os.environ["FAKE_ENGINE_" + name.upper()])
if args[:1] == ["version"]:
    print(answers["version"])
    sys.exit(0)
if args[:2] == ["volume", "ls"]:
    print("\n".join(answers["volumes"]))
    sys.exit(0)
sys.exit(1)
"""


class Engines:
    """Recorded doubles of `docker` and `podman`: each answers `version` and `volume ls` only."""

    def __init__(self, tmp: Path, **answers: dict) -> None:
        self.bin = tmp / "engine-bin"
        self.bin.mkdir()
        self.calls_path = tmp / "engine-calls.jsonl"
        self.answers = answers
        for name in answers:
            exe = self.bin / name
            exe.write_text(DOUBLE.replace("#!/usr/bin/env python3", f"#!{sys.executable}"), "utf-8")
            exe.chmod(exe.stat().st_mode | stat.S_IXUSR)

    def calls(self) -> list[list[str]]:
        if not self.calls_path.exists():
            return []
        return [json.loads(x) for x in self.calls_path.read_text("utf-8").splitlines()]

    def run(self, root: Path, *args: str) -> subprocess.CompletedProcess:
        env = {k: v for k, v in os.environ.items() if not k.startswith("FAKE_ENGINE_")}
        env.update(PATH=str(self.bin), FAKE_ENGINE_CALLS=str(self.calls_path))
        for name, answer in self.answers.items():
            env[f"FAKE_ENGINE_{name.upper()}"] = json.dumps(answer)
        return subprocess.run(  # nosec B603 - fixed argument list, no shell
            [sys.executable, str(SCRIPTS / "wsl.py"), "engine", *args, "--root", str(root)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            timeout=60,
        )


def project(tmp: Path, files: dict[str, str]) -> Path:
    root = tmp / "proj"
    root.mkdir()
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def state_file(tmp: Path, **engines) -> Path:
    data = {"distro": "Ubuntu-24.04", "engines": engines}
    path = tmp / "state.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def ps1_text() -> str:
    return PS1.read_text(encoding="utf-8")


# --- detection and recommendation (answer 1) -----------------------------------------------------


@pytest.mark.parametrize(
    ("files", "uses"),
    [
        ({"compose.yaml": "services: {}\n"}, {"docker"}),
        ({"Dockerfile": "FROM example\n"}, {"docker"}),
        ({"scripts/up.sh": "docker compose up -d\n"}, {"docker"}),
        ({"Containerfile": "FROM example\n"}, {"podman"}),
        ({"Makefile": "test:\n\tpodman run --rm example\n"}, {"podman"}),
        ({"README.md": "no engine here\n"}, set()),
        ({"scripts/agk/wsl.py": "docker run\n"}, set()),
    ],
)
def test_project_engines_are_read_from_its_files(tmp_path, files, uses):
    """REQ-050: brief #1379 answer 1: compose files, Dockerfile, Containerfile and scripts that
    call an engine decide; the kit's own scripts never do."""
    assert set(wsl.project_engines(project(tmp_path, files))) == uses


def test_recommendation_follows_the_project_then_the_machine():
    """REQ-050: brief #1379 answer 1: one engine with its reason; Podman when nothing decides."""
    assert wsl.recommend({"docker": ["compose.yaml"]}, set())[0] == "docker"
    assert "compose.yaml" in wsl.recommend({"docker": ["compose.yaml"]}, set())[1]
    assert wsl.recommend({"podman": ["Containerfile"]}, {"docker"})[0] == "podman"
    assert wsl.recommend({}, {"docker"})[0] == "docker"
    engine, reason = wsl.recommend({}, set())
    assert engine == "podman" and "default" in reason
    assert wsl.recommend({"docker": ["x"], "podman": ["y"]}, set())[0] == "podman"


def test_engine_recommends_docker_for_a_compose_project(tmp_path):
    """REQ-050: brief #1379 answer 1: the recommendation in one line, with the person's choice."""
    root = project(tmp_path, {"compose.yaml": "services: {}\n"})
    engines = Engines(tmp_path, docker={"version": "27.3.1", "volumes": []})
    done = engines.run(root)
    assert done.returncode == 0, done.stderr
    line = next(x for x in done.stdout.splitlines() if x.startswith("engine:"))
    assert line.startswith("engine: docker") and "compose.yaml" in line and "--choose" in line
    assert "docker 27.3.1" in done.stdout


def test_the_person_may_choose(tmp_path):
    """REQ-050: brief #1379 answer 1: `--choose` overrides the recommendation."""
    root = project(tmp_path, {"compose.yaml": "services: {}\n"})
    done = Engines(tmp_path).run(root, "--choose", "podman")
    assert done.returncode == 0, done.stderr
    assert "engine: podman (your choice)" in done.stdout
    (tmp_path / "x").mkdir()
    assert Engines(tmp_path / "x").run(root, "--choose", "lxc").returncode == 2


# --- the group or rootless choice (answer 2) -----------------------------------------------------


def test_docker_group_line_names_root_equivalent_access(tmp_path):
    """REQ-050: brief #1379 answer 2: the docker group grants root-equivalent access, said once."""
    root = project(tmp_path, {"Dockerfile": "FROM example\n"})
    done = Engines(tmp_path).run(root)
    assert re.search(r"(?m)^docker group: .*root-equivalent", done.stdout), done.stdout
    assert "--rootless" in done.stdout


def test_rootless_mode_when_the_person_chooses_it(tmp_path):
    """REQ-050: brief #1379 answer 2: rootless mode adds nobody to the docker group."""
    root = project(tmp_path, {"Dockerfile": "FROM example\n"})
    done = Engines(tmp_path).run(root, "--rootless")
    assert done.returncode == 0, done.stderr
    assert "docker group" not in done.stdout
    assert re.search(r"(?m)^rootless: ", done.stdout)


def test_the_setup_installs_docker_engine_from_dockers_repository():
    """REQ-050: brief #1379 answer 2: Docker's own apt repository with the Compose plugin, the
    group or rootless mode, and systemd starting the daemon; each step checks first."""
    text = ps1_text()
    assert "download.docker.com/linux/" in text
    for package in ("docker-ce", "docker-compose-plugin"):
        assert package in text
    assert re.search(r"usermod -aG docker", text)
    assert "dockerd-rootless-setuptool.sh install" in text
    assert re.search(r"systemctl enable --now docker", text)
    for step in ("docker", "docker_rootless", "engine_check"):
        assert re.search(rf"(?m)^step {step} has_{step} set_{step}", text), step
    assert re.search(r"ValidateSet\('podman', 'docker', 'docker-desktop'\)", text)


# --- Docker Desktop (answer 3) -------------------------------------------------------------------

TERMS = re.compile(r"(?i)(\$\s?\d|\d+\s*(employees|people|million)|revenue|free for|USD|EUR)")


def test_desktop_is_named_with_its_licence_line_and_no_terms(tmp_path):
    """REQ-050: brief #1379 answer 3: Docker Desktop found: its page is named, its terms never
    stated, and both ways are offered."""
    root = project(tmp_path, {"compose.yaml": "services: {}\n"})
    path = state_file(tmp_path, desktop=True, desktop_running=False, windows_docker="27.2.0")
    done = Engines(tmp_path).run(root, "--state", str(path))
    assert done.returncode == 0, done.stderr
    line = next(x for x in done.stdout.splitlines() if x.startswith("Docker Desktop:"))
    assert wsl.DOCKER_TERMS_PAGE in line and "may need" in line
    assert "docker-desktop" in line and "Ubuntu-24.04" in line
    assert not TERMS.search(done.stdout), done.stdout
    assert not TERMS.search(ps1_text())


def test_the_kit_never_installs_docker_desktop():
    """REQ-050: brief #1379 answer 3: Desktop is detected, never installed."""
    text = ps1_text()
    assert not re.search(r"(?i)winget\s+install|Docker%20Desktop%20Installer|choco\s+install", text)


# --- never two engines, never deleted (answer 4) -------------------------------------------------


def test_never_two_engines_on_one_port(tmp_path):
    """REQ-050: brief #1379 answer 3: with Desktop's engine running, Docker Engine inside WSL waits
    until it stops; the script stops the run there."""
    assert wsl.two_engines("docker", {"desktop_running": True})
    assert wsl.two_engines("docker", {"desktop_running": False}) is None
    assert wsl.two_engines("docker-desktop", {"desktop_running": True}) is None
    root = project(tmp_path, {"Dockerfile": "FROM example\n"})
    path = state_file(tmp_path, desktop=True, desktop_running=True)
    done = Engines(tmp_path).run(root, "--state", str(path))
    assert re.search(r"(?m)^ports: .*one engine", done.stdout), done.stdout
    text = ps1_text()
    assert re.search(r"Invoke-Step -Name 'one_engine'.*\{ Finish \}", text)


@pytest.mark.parametrize(
    "pattern",
    [
        r"machine\s+rm",
        r"volume\s+rm",
        r"volume\s+prune",
        r"system\s+prune",
        r"(?i)uninstall",
        r"apt-get\s+(remove|purge)",
        r"Remove-Item",
    ],
)
def test_nothing_is_deleted_or_uninstalled(pattern):
    """REQ-050: brief #1379 answer 4: the Windows engine is stopped, never uninstalled; volumes
    are listed, never removed."""
    assert not re.search(pattern, ps1_text()), pattern


def test_windows_engine_is_stopped_after_the_move_and_started_back():
    """REQ-050: brief #1379 answer 4: stopped with the watchdog pass, started again on back."""
    text = ps1_text()
    assert re.search(r"if \(\$InstallWatchdog\) \{[^}]*Invoke-Step -Name 'windows_engine'", text)
    assert "Invoke-Step -Name 'windows_engine_back'" in text
    assert "podman machine stop" in text and "podman machine start" in text


def test_volumes_are_listed_read_only_with_export_and_import(tmp_path):
    """REQ-050: brief #1379 answer 4: the doubles see `version` and `volume ls` only; the lines
    give the export and import commands and move nothing."""
    root = project(tmp_path, {"compose.yaml": "services: {}\n"})
    engines = Engines(
        tmp_path,
        docker={"version": "27.3.1", "volumes": ["pgdata", "cache"]},
        podman={"version": "5.2.0", "volumes": ["unused"]},
    )
    done = engines.run(root)
    assert done.returncode == 0, done.stderr
    assert "volumes: 2 of docker here (pgdata, cache); nothing is moved" in done.stdout
    assert "export pgdata:" in done.stdout and "import pgdata:" in done.stdout
    assert "unused" not in done.stdout
    calls = engines.calls()
    assert calls
    for call in calls:
        assert call[1:2] == ["version"] or call[1:3] == ["volume", "ls"], call


def test_versions_on_windows_and_in_wsl(tmp_path):
    """REQ-050: brief #1379 answer 4: the engine's version on Windows and in WSL, from the state."""
    root = project(tmp_path, {"Dockerfile": "FROM example\n"})
    path = state_file(tmp_path, windows_docker="27.2.0", wsl_version="27.3.1")
    done = Engines(tmp_path).run(root, "--state", str(path))
    line = next(x for x in done.stdout.splitlines() if x.startswith("versions:"))
    assert "Windows 27.2.0" in line and "WSL 27.3.1" in line


# --- compose and podman-docker (answer 5) --------------------------------------------------------


def test_podman_docker_is_named_when_scripts_call_docker(tmp_path):
    """REQ-050: brief #1379 answer 5: a project whose scripts call docker keeps working with
    Podman only with `podman-docker`, which the lines name."""
    root = project(tmp_path, {"scripts/up.sh": "docker compose up\n"})
    done = Engines(tmp_path).run(root, "--choose", "podman")
    assert re.search(r"(?m)^podman-docker: .*apt-get install podman-docker", done.stdout)
    (tmp_path / "y").mkdir()
    done = Engines(tmp_path / "y").run(root)
    assert "podman-docker" not in done.stdout


def test_the_check_runs_one_container_and_one_compose_service():
    """REQ-050: brief #1379 answer 5: the user step starts one container and one compose service
    with the chosen engine."""
    text = ps1_text()
    body = re.search(r"has_engine_check\(\) \{(.*?)\n\}", text, flags=re.S)
    assert body, "has_engine_check is defined"
    assert '"$e" run --rm' in body.group(1) and '"$e" compose -f' in body.group(1)


def test_the_state_carries_the_engine():
    """REQ-050: brief #1379 answers 1 and 4: the `-Json` table names the engine and its facts."""
    assert {"engine", "engines"} <= set(wsl.STATE_KEYS)
    for step in ("one_engine", "docker", "desktop_wsl", "docker_rootless", "engine_check"):
        assert step in wsl.STEP_IDS, step


def test_skill_runs_the_engine_lines_before_the_setup():
    """REQ-050: brief #1379 answer 1: the skill shows the engine lines and passes the choice."""
    text = SKILL.read_text("utf-8")
    assert '/scripts/agk/wsl.py" engine' in text
    assert "-Engine <engine>" in text and "-DockerRootless" in text
