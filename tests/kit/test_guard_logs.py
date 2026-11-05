"""Tests of the redacting log reader, `agk logs` (SPEC-0042 rule 11).

The logs are generated in tmp_path from invented values only (example.io addresses that are not
example.com, the published Visa test number, documentation-free private addresses).
"""

from __future__ import annotations

import socket
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import time
from pathlib import Path

import guard_logs
import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "agk" / "guard_logs.py"
LIMIT_SECONDS = 30  # Q-S0042-9: a 10 MB log within 30 seconds on the CI runner


def run(args: list[str], cwd: Path, stdin: bytes | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), *args], cwd=cwd, input=stdin, capture_output=True
    )


LOG = (
    "2026-11-05T10:00:01Z INFO login user=ana@mail.example.io ip=10.1.2.3\n"
    "2026-11-05T10:00:02Z WARN retry user=raj@mail.example.io\n"
    "2026-11-05T10:00:03Z INFO login user=ana@mail.example.io card=4111111111111111\n"
    "2026-11-05T10:00:04Z INFO done\n"
)


def test_ac3_a_log_keeps_its_structure_and_one_value_keeps_one_label(tmp_path):
    """REQ-049 AC3: rule 11 (labels per kind, same value same label, structure kept)."""
    (tmp_path / "app.log").write_text(LOG, encoding="utf-8")
    proc = run(["app.log"], tmp_path)
    assert proc.returncode == 0
    out = proc.stdout.decode().splitlines()
    assert out[0] == "2026-11-05T10:00:01Z INFO login user=[EMAIL-1] ip=[IP-1]"
    assert out[1] == "2026-11-05T10:00:02Z WARN retry user=[EMAIL-2]"
    assert out[2] == "2026-11-05T10:00:03Z INFO login user=[EMAIL-1] card=[CARD-1]"
    assert out[3] == "2026-11-05T10:00:04Z INFO done"
    assert out[4] == "agk logs: EMAIL 3, IP 1, CARD 1"
    assert len(out) == 5
    assert "example.io" not in proc.stdout.decode()


def test_ac3_max_lines_prints_the_last_lines_and_numbers_labels_over_them(tmp_path):
    """REQ-049 AC3: rule 11 (--max-lines N prints the tail; labels over the lines printed)."""
    (tmp_path / "app.log").write_text(LOG, encoding="utf-8")
    out = run(["--max-lines", "3", "app.log"], tmp_path).stdout.decode().splitlines()
    assert out[0] == "2026-11-05T10:00:02Z WARN retry user=[EMAIL-1]"
    assert out[1] == "2026-11-05T10:00:03Z INFO login user=[EMAIL-2] card=[CARD-1]"
    assert out[-1] == "agk logs: EMAIL 2, CARD 1"
    assert len(out) == 4


def test_ac3_the_last_line_holds_counts_only_and_a_clean_log_says_no_findings(tmp_path):
    """REQ-049 AC3: rule 11 (the summary line)."""
    (tmp_path / "clean.log").write_text("a\nb\n", encoding="utf-8")
    out = run(["clean.log"], tmp_path).stdout.decode().splitlines()
    assert out == ["a", "b", "agk logs: no findings"]


def test_ac3_standard_input_is_read_with_a_dash(tmp_path):
    """REQ-049 AC3: rule 11 (`agk logs -`)."""
    proc = run(["-"], tmp_path, stdin=b"from 10.9.8.7\n")
    assert proc.stdout.decode().splitlines() == ["from [IP-1]", "agk logs: IP 1"]


def test_ac3_bytes_that_are_not_utf8_are_replaced_and_never_passed_raw(tmp_path):
    """REQ-049 AC3: rule 11 (non-UTF-8 bytes)."""
    (tmp_path / "bin.log").write_bytes(b"ok \xff\xfe end 10.1.2.3\n")
    proc = run(["bin.log"], tmp_path)
    assert proc.returncode == 0
    assert b"\xff" not in proc.stdout
    assert proc.stdout.decode().splitlines()[0] == "ok �� end [IP-1]"


def test_ac3_a_custom_pattern_of_the_guard_table_adds_a_custom_kind(tmp_path):
    """REQ-049 AC3: rule 11 with a [guard] patterns entry (rule 1)."""
    (tmp_path / "agk.toml").write_text(
        "[guard]\npatterns = [{ name = 'employee', regex = 'EMP-\\d{5}' }]\n", encoding="utf-8"
    )
    (tmp_path / "app.log").write_text("by EMP-00417\n", encoding="utf-8")
    out = run(["app.log"], tmp_path).stdout.decode().splitlines()
    assert out == ["by [CUSTOM-employee-1]", "agk logs: CUSTOM-employee 1"]


def test_ac1_a_refused_guard_table_exits_2_naming_the_setting_and_prints_no_log(tmp_path):
    """REQ-049 AC1: rule 1 (a refused table: exit 2, the setting named, no value)."""
    (tmp_path / "agk.toml").write_text("[guard]\nenabled = false\n", encoding="utf-8")
    (tmp_path / "app.log").write_text("user ana@mail.example.io\n", encoding="utf-8")
    proc = run(["app.log"], tmp_path)
    assert proc.returncode == 2
    assert "(setting: [guard] enabled)" in proc.stdout.decode()
    assert "example.io" not in proc.stdout.decode()


@pytest.mark.parametrize("args", [[], ["a.log", "b.log"], ["--max-lines", "0", "a.log"]])
def test_ac3_bad_usage_exits_2_naming_the_option(tmp_path, args):
    """REQ-049 AC3: rule 11 (usage)."""
    proc = run(args, tmp_path)
    assert proc.returncode == 2
    assert "usage" in proc.stdout.decode() or "--max-lines" in proc.stdout.decode()


def test_ac3_a_file_it_cannot_read_exits_2_naming_the_option_not_the_path(tmp_path):
    """REQ-049 AC3: rule 11 (an unreadable file)."""
    proc = run(["secret-name-missing.log"], tmp_path)
    assert proc.returncode == 2
    assert "secret-name-missing" not in proc.stdout.decode()
    assert "(option: FILE)" in proc.stdout.decode()


def test_ac3_no_socket_is_opened_and_no_file_is_written(tmp_path, monkeypatch, capsys):
    """REQ-049 AC3: rule 11 (opens no socket, writes no file)."""
    (tmp_path / "app.log").write_text(LOG, encoding="utf-8")

    def refuse(*_a, **_k):
        raise AssertionError("a socket was opened")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.chdir(tmp_path)
    before = sorted(p.name for p in tmp_path.iterdir())
    assert guard_logs.main(["app.log"]) == 0
    assert sorted(p.name for p in tmp_path.iterdir()) == before
    assert "[EMAIL-1]" in capsys.readouterr().out


def test_ac3_a_10_mb_generated_log_is_redacted_within_the_limit(tmp_path):
    """REQ-049 AC3: rule 11 and Q-S0042-9 (speed)."""
    lines = []
    i = 0
    size = 0
    while size < 10 * 1024 * 1024:
        line = (
            f"2026-11-05T10:{i % 60:02d}:00Z INFO req={i} user=u{i % 97}@mail.example.io "
            f"ip=10.0.{i % 250}.{i % 200} path=/api/v1/items/{i} status=200 took={i % 900}ms\n"
        )
        lines.append(line)
        size += len(line)
        i += 1
    (tmp_path / "big.log").write_text("".join(lines), encoding="utf-8")
    start = time.monotonic()
    proc = run(["--max-lines", str(len(lines)), "big.log"], tmp_path)
    elapsed = time.monotonic() - start
    assert proc.returncode == 0
    assert elapsed < LIMIT_SECONDS, f"{elapsed:.1f}s"
    assert b"example.io" not in proc.stdout
