"""Kit-only tests of what a design command says when its headless browser fails (brief #1876).

A found browser that fails is refused with the call's own rule and text and one fixed clause that
names why: its sandbox cannot start, it runs as root, it timed out, it cannot be started, or
another error. The clause never holds the browser's text; with `AGK_DESIGN_BROWSER_LOG=1` the
last 20 lines of the browser's standard error go to standard error, `browser: ` before each and
the home folder written `~`. The kit keeps the browser's sandbox: no browser command carries
`--no-sandbox`. Fake browsers stand in for a real one; invented text only (example.com); no
network.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import KIT_ROOT, clean_env
from design_fixture import VERSION, frozen_version, png
from test_design_compare import imported, project
from test_design_write import FOLDER, existing_mockup

sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
import design  # noqa: E402
import design_compare  # noqa: E402
import design_render  # noqa: E402

AGK = KIT_ROOT / "scripts" / "agk"
GUIDE = 'see "Design screenshots and comparison" in docs/guides/reference.md'
SANDBOX = f"the browser could not start its sandbox ({GUIDE})"
ROOT = f"the browser does not start its sandbox as root ({GUIDE})"
OTHER = "the browser failed (its own message: AGK_DESIGN_BROWSER_LOG=1)"
TIMEOUT = "the browser did not finish within 120 seconds"
NOT_STARTED = "the browser could not be started"
HOME = str(Path.home())
MARKERS = ("example.com", "/home/invented-person", HOME + "/agk-invented")
TEXTS = {
    "No usable sandbox! See https://example.com/sandbox": SANDBOX,
    "FATAL: Failed to move to new namespace: example.com": SANDBOX,
    "The SUID sandbox helper binary was found, but is not configured: example.com": SANDBOX,
    "Running as root without --no-sandbox is not supported. See https://example.com/r": ROOT,
    "something else broke at https://example.com/x": OTHER,
}


def failing_browser(directory: Path, text: str, name: str = "chromium") -> Path:
    """A browser that writes TEXT, an invented path and noise to stderr, and exits 1, no file."""
    directory.mkdir(parents=True, exist_ok=True)
    script = directory / name
    lines = [f"noise line {n} at /home/invented-person/x" for n in range(30)]
    lines += [f"{HOME}/agk-invented/profile", text]
    body = "".join(f"echo '{line}' >&2\n" for line in lines)
    script.write_text("#!/bin/sh\n" + body + "exit 1\n", encoding="utf-8")
    script.chmod(0o755)
    return script


def noisy_browser(directory: Path, shot: Path) -> Path:
    """A browser that warns on stderr, logs its arguments, and still writes every screenshot."""
    directory.mkdir(parents=True, exist_ok=True)
    cp = __import__("shutil").which("cp")
    script = directory / "chromium"
    script.write_text(
        "#!/bin/sh\n"
        f'echo "$@" >> "{directory / "calls"}"\n'
        "echo 'WARNING: No usable sandbox at https://example.com/w' >&2\n"
        "case \"$*\" in *--dump-dom*) echo '<pre id=\"agk-reflow\">ok</pre>'; exit 0;; esac\n"
        'for a in "$@"; do case "$a" in --screenshot=*) '
        f'{cp} "{shot}" "${{a#--screenshot=}}";; esac; done\n',
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script


def run(script, *args, path, log=None):
    env = clean_env()
    env["PATH"] = path
    env.pop("AGK_DESIGN_BROWSER_LOG", None)
    if log is not None:
        env["AGK_DESIGN_BROWSER_LOG"] = log
    return subprocess.run(
        [sys.executable, str(AGK / script), *args],
        capture_output=True,
        text=True,
        env=env,
    )


def no_marker(text: str) -> bool:
    return not any(marker in text for marker in MARKERS)


def calls(tmp_path, text):
    """Each browser call of the kit with a failing browser: (rule and text, the call)."""
    browser = str(failing_browser(tmp_path / "bin", text))
    page = tmp_path / "page.html"
    page.write_text("<!doctype html><p>Example</p>\n", encoding="utf-8")
    target = tmp_path / "shot.png"
    return [
        (
            "rule 8: the headless browser did not make a screenshot",
            lambda: design_render.shoot(browser, page, 360, "light", target),
        ),
        (
            "rule 8: the headless browser did not measure a page",
            lambda: design_render.measure(browser, page, 360, "dark"),
        ),
        (
            "rule 11: the headless browser did not make a screenshot",
            lambda: design_compare.shoot_at(browser, page.as_uri(), (1440, 800), target),
        ),
        (
            "rule 11: the headless browser did not make a screenshot",
            lambda: design_compare.shoot_at(
                browser, "http://agk-files.example.com/home.html", (1440, 800), target, port=9
            ),
        ),
    ]


@pytest.mark.parametrize("text", list(TEXTS))
def test_ac6_each_browser_call_names_why_the_browser_failed(tmp_path, text):
    """REQ-044 AC6: brief #1876 answers 1 and 2 (the rule and text kept, one fixed clause)."""
    for want, call in calls(tmp_path, text):
        with pytest.raises(design.CheckError) as exc:
            call()
        assert str(exc.value) == f"{want}; {TEXTS[text]}"
        assert no_marker(str(exc.value))


@pytest.mark.parametrize("text", list(TEXTS))
def test_ac6_the_mockup_screenshots_name_why_the_browser_failed(tmp_path, text):
    """REQ-044 AC6: brief #1876 answer 2 (`screenshots --folder`, SPEC-0029 rule 6)."""
    existing_mockup(tmp_path)
    bin_dir = tmp_path.parent / (tmp_path.name + "-bin")
    failing_browser(bin_dir, text)
    proc = run(
        "design.py", "screenshots", "--folder", FOLDER, "--root", str(tmp_path), path=str(bin_dir)
    )
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert proc.stdout == (
        f"FAIL design: rule 6: the headless browser did not make a screenshot; {TEXTS[text]}\n"
    )
    assert proc.stderr == ""


def test_ac6_the_reflow_and_the_comparison_name_why_the_browser_failed(tmp_path):
    """REQ-044 AC6: brief #1876 answer 2 through `design.py screenshots --version` and
    `design_compare.py --version v<n>`."""
    text = "Running as root without --no-sandbox is not supported. See https://example.com/r"
    bin_dir = tmp_path.parent / (tmp_path.name + "-bin")
    failing_browser(bin_dir, text)
    path = f"{bin_dir}{os.pathsep}{os.path.dirname(sys.executable)}"
    frozen_version(tmp_path)
    proc = run("design.py", "screenshots", "--version", VERSION, "--root", str(tmp_path), path=path)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert proc.stdout == f"FAIL design: rule 8: the headless browser did not make a screenshot; {ROOT}\n"
    other = tmp_path.parent / (tmp_path.name + "-compare")
    other.mkdir()
    project(other, tolerance=0.3)
    proc = run(
        "design_compare.py", "--version", VERSION, "--screens", "home/default",
        "--root", str(other), path=path,
    )  # fmt: skip
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert proc.stdout == (
        f"FAIL design-compare: rule 8: the headless browser did not make a screenshot; {ROOT}\n"
    )
    third = tmp_path.parent / (tmp_path.name + "-imported")
    third.mkdir()
    imported(third)
    proc = run(
        "design_compare.py", "--version", "i1", "--screens", "home/default",
        "--root", str(third), path=str(bin_dir),
    )  # fmt: skip
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert proc.stdout == (
        f"FAIL design-compare: rule 11: the headless browser did not make a screenshot; {ROOT}\n"
    )


@pytest.mark.parametrize("value", [None, "", "0", "true"])
def test_ac6_the_browser_text_is_printed_only_with_the_log_setting_one(tmp_path, value):
    """REQ-044 AC6: brief #1876 answer 3 and Q-1833-2 (only the exact value 1 prints it)."""
    existing_mockup(tmp_path)
    bin_dir = tmp_path.parent / (tmp_path.name + "-bin")
    failing_browser(bin_dir, "No usable sandbox! See https://example.com/sandbox")
    args = ("screenshots", "--folder", FOLDER, "--root", str(tmp_path))
    proc = run("design.py", *args, path=str(bin_dir), log=value)
    assert proc.returncode == 1
    assert proc.stderr == "" and no_marker(proc.stdout)


def test_ac6_with_the_log_setting_one_the_last_20_browser_lines_go_to_stderr(tmp_path):
    """REQ-044 AC6: brief #1876 answer 3 (the tail on standard error, `~` for the home folder,
    never on standard output)."""
    existing_mockup(tmp_path)
    bin_dir = tmp_path.parent / (tmp_path.name + "-bin")
    text = "No usable sandbox! See https://example.com/sandbox"
    failing_browser(bin_dir, text)
    args = ("screenshots", "--folder", FOLDER, "--root", str(tmp_path))
    proc = run("design.py", *args, path=str(bin_dir), log="1")
    assert proc.returncode == 1
    assert no_marker(proc.stdout)
    lines = proc.stderr.splitlines()
    assert len(lines) == 20 and all(line.startswith("browser: ") for line in lines)
    assert lines[-1] == f"browser: {text}"
    assert lines[-2] == "browser: ~/agk-invented/profile"
    assert HOME + "/" not in proc.stderr


def test_ac6_a_browser_that_passes_with_warnings_prints_none_of_them(tmp_path):
    """REQ-044 AC6: brief #1876 answer 3 (a passing call prints no browser text, even with 1)."""
    existing_mockup(tmp_path)
    bin_dir = tmp_path.parent / (tmp_path.name + "-bin")
    shot = png(tmp_path.parent / (tmp_path.name + "-s.png"), [[(255, 255, 255)]])
    noisy_browser(bin_dir, shot)
    args = ("screenshots", "--folder", FOLDER, "--root", str(tmp_path))
    proc = run("design.py", *args, path=str(bin_dir), log="1")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stderr == "" and no_marker(proc.stdout)


def test_ac6_without_a_browser_the_commands_read_not_run_never_a_cause(tmp_path):
    """REQ-044 AC6: SPEC-0037 rule 8 unchanged (no browser: `not run`, exit 0, no clause)."""
    empty = tmp_path.parent / (tmp_path.name + "-empty")
    empty.mkdir()
    frozen_version(tmp_path)
    proc = run("design.py", "screenshots", "--version", VERSION, "--root", str(tmp_path), path=str(empty))
    assert proc.returncode == 0
    assert proc.stdout == "design: no headless browser found; reflow not run\n"


def raising(monkeypatch, browser: str, error: BaseException):
    real = subprocess.run

    def fake(command, *args, **kwargs):
        if command and command[0] == browser:
            raise error
        return real(command, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", fake)


@pytest.mark.parametrize(
    ("error", "clause"),
    [
        (subprocess.TimeoutExpired(["chromium"], 120), TIMEOUT),
        (PermissionError(13, "invented"), NOT_STARTED),
        (FileNotFoundError(2, "invented"), NOT_STARTED),
    ],
)
def test_ac6_a_timeout_or_a_browser_that_cannot_start_is_a_refusal_not_a_traceback(
    tmp_path, monkeypatch, capsys, error, clause
):
    """REQ-044 AC6: brief #1876 answers 1 and 2 (`TimeoutExpired` and `OSError`, exit 1, through
    `design.main` and `design_compare.main`)."""
    browser = str(tmp_path / "bin" / "chromium")
    monkeypatch.setattr(design, "find_browser", lambda: browser)
    raising(monkeypatch, browser, error)
    existing_mockup(tmp_path)
    assert design.main(["screenshots", "--folder", FOLDER, "--root", str(tmp_path)]) == 1
    out = capsys.readouterr()
    assert out.out == f"FAIL design: rule 6: the headless browser did not make a screenshot; {clause}\n"
    assert out.err == ""
    other = tmp_path / "compare"
    other.mkdir()
    project(other, tolerance=0.3)
    args = ["--version", VERSION, "--screens", "home/default", "--root", str(other)]
    assert design_compare.main(args) == 1
    out = capsys.readouterr()
    assert out.out == (
        f"FAIL design-compare: rule 8: the headless browser did not make a screenshot; {clause}\n"
    )


@pytest.mark.parametrize("tolerance", [0, 0.01, 1])
def test_ac6_a_browser_refusal_is_exit_1_whatever_the_tolerance(tmp_path, tolerance):
    """REQ-044 AC6: brief #1876 answer 8 (`pixel_tolerance` 0, 0.01 and 1)."""
    bin_dir = tmp_path.parent / (tmp_path.name + "-bin")
    failing_browser(bin_dir, "FATAL: Failed to move to new namespace: example.com")
    path = f"{bin_dir}{os.pathsep}{os.path.dirname(sys.executable)}"
    project(tmp_path, tolerance=tolerance)
    args = ("--version", VERSION, "--screens", "home/default", "--root", str(tmp_path))
    proc = run("design_compare.py", *args, path=path)
    assert proc.returncode == 1
    assert proc.stdout.endswith(f"; {SANDBOX}\n")


@pytest.mark.parametrize("case", ["bad tolerance", "render fails"])
def test_ac6_settings_refusals_come_before_any_browser_call(tmp_path, case):
    """REQ-044 AC6: brief #1876 answer 8 (a bad `pixel_tolerance` and a failing `[design] render`
    are refused as today, with no browser clause)."""
    bin_dir = tmp_path.parent / (tmp_path.name + "-bin")
    failing_browser(bin_dir, "No usable sandbox! See https://example.com/sandbox")
    path = f"{bin_dir}{os.pathsep}{os.path.dirname(sys.executable)}"
    project(tmp_path, tolerance="2" if case == "bad tolerance" else 0.3)
    if case == "render fails":
        (tmp_path / "render.py").write_text("raise SystemExit(3)\n", encoding="utf-8")
    args = ("--version", VERSION, "--screens", "home/default", "--root", str(tmp_path))
    proc = run("design_compare.py", *args, path=path)
    assert proc.returncode == 1
    assert proc.stdout.startswith("FAIL design-compare: ") and "browser" not in proc.stdout


def test_ac6_no_browser_command_of_the_kit_turns_the_sandbox_off(tmp_path):
    """REQ-044 AC6: brief #1876 answer 4 (the kit keeps the browser's sandbox)."""
    assert "--no-sandbox" not in design.OFFLINE
    assert "--no-sandbox" not in design_render.proxied(9)
    shot = png(tmp_path / "s.png", [[(255, 255, 255)]])
    browser = noisy_browser(tmp_path / "bin", shot)
    page = tmp_path / "page.html"
    page.write_text("<!doctype html><p>Example</p>\n", encoding="utf-8")
    design_render.shoot(str(browser), page, 360, "light", tmp_path / "a.png")
    assert design_render.measure(str(browser), page, 360, "dark") is False
    design_compare.shoot_at(str(browser), page.as_uri(), (1440, 800), tmp_path / "b.png")
    design_compare.shoot_at(str(browser), page.as_uri(), (1440, 800), tmp_path / "c.png", port=9)
    existing_mockup(tmp_path / "mock")
    env_path = os.environ["PATH"]
    try:
        os.environ["PATH"] = str(browser.parent)
        assert design.cmd_screenshots(tmp_path / "mock", {"folder": FOLDER}) == 0
    finally:
        os.environ["PATH"] = env_path
    logged = (tmp_path / "bin" / "calls").read_text(encoding="utf-8").splitlines()
    assert len(logged) == 8 and all("--headless" in c for c in logged)
    assert not any("--no-sandbox" in c for c in logged)
    for name in ("design.py", "design_render.py", "design_compare.py"):
        assert '"--no-sandbox"' not in (AGK / name).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "error", [subprocess.TimeoutExpired(["pdftoppm"], 120), FileNotFoundError(2, "invented")]
)
def test_ac6_the_pdf_renderer_still_reads_none_when_it_cannot_run(tmp_path, monkeypatch, error):
    """REQ-044 AC6: brief #1876 answer 1 (`pdf_page` keeps `design_render._run`, unchanged)."""
    renderer = str(tmp_path / "pdftoppm")
    raising(monkeypatch, renderer, error)
    pdf = tmp_path / "brief.pdf"
    pdf.write_bytes(b"%PDF-1.4\n% invented\n")
    assert design_compare.pdf_page(renderer, pdf, 1, tmp_path / "page.png") is None
