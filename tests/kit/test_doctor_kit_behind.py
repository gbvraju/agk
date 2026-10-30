"""The doctor says when the installed kit is older than the newest kit release (brief #320 answer 1;
REQ-038, ADR-0181).

`kit-behind` (warn, after `kit-version`) reads the newest release of the kit's own repository (the
`repository` of the kit's `.claude-plugin/plugin.json`) with one GET and compares its tag with
`version` in `agk.toml`. It fails when the installed version is older and names both versions; it
is `ok` when they are equal or when the installed one is newer (a checkout between releases); a
release that cannot be read is `cannot-check` with a reason class, never `ok`. No network: the
release is a recorded file, or a stubbed `gh`.
"""

from __future__ import annotations

import json
import os

from test_doctor import IDS, checks_of, doctor, prepare, run_case, stub_gh


def with_release(tmp_path, release, installed: str = "9.9.9", *, kit: bool = True):
    """The `ok` case with the recorded release and the installed version replaced."""
    dirs = prepare("ok", tmp_path)
    file = dirs["api"] / "kit-release.json"
    if release is None:
        file.unlink()
    else:
        file.write_text(json.dumps(release), encoding="utf-8")
    toml = dirs["root"] / "agk.toml"
    toml.write_text(
        toml.read_text(encoding="utf-8").replace('version = "9.9.9"', f'version = "{installed}"'),
        encoding="utf-8",
    )
    args = ["--api-dir", str(dirs["api"]), "--json", str(dirs["root"])]
    if kit:
        args[:0] = ["--kit-root", str(dirs["kit"])]
    proc = doctor(*args)
    return checks_of(proc.stdout)["kit-behind"], proc


def test_the_check_is_a_warning_after_kit_version():
    assert IDS.index("kit-behind") == IDS.index("kit-version") + 1


def test_an_installed_kit_older_than_the_newest_release_is_named_with_both_versions(tmp_path):
    proc, log, _ = run_case("kit-behind", tmp_path, "--json")
    check = checks_of(proc.stdout)["kit-behind"]
    assert (check["status"], check["severity"]) == ("fail", "warn")
    assert "9.9.9" in check["message"] and "10.0.0" in check["message"]
    assert check["message"].index("9.9.9") < check["message"].index("10.0.0")
    assert "/agk:upgrade" in check["fix"]
    assert proc.returncode == 4 and not log.exists()


def test_the_versions_are_compared_as_numbers_not_as_text(tmp_path):
    check, _ = with_release(tmp_path / "a", {"tag_name": "v0.10.0"}, installed="0.9.0")
    assert check["status"] == "fail"
    check, _ = with_release(tmp_path / "b", {"tag_name": "v0.9.0"}, installed="0.10.0")
    assert check["status"] == "ok"


def test_an_installed_kit_equal_to_the_newest_release_is_ok(tmp_path):
    check, proc = with_release(tmp_path, {"tag_name": "v9.9.9"})
    assert check["status"] == "ok" and proc.returncode == 0, proc.stdout


def test_a_checkout_newer_than_the_newest_release_is_ok_and_says_so(tmp_path):
    """A pre-release checkout: the installed version is ahead of every published release."""
    check, _ = with_release(tmp_path, {"tag_name": "v9.9.8"})
    assert check["status"] == "ok"
    assert "newer than the newest release" in check["message"]


def test_a_tag_without_the_v_prefix_is_read_too(tmp_path):
    check, _ = with_release(tmp_path, {"tag_name": "10.0.0"})
    assert check["status"] == "fail"


def test_a_release_that_cannot_be_read_is_cannot_check_never_ok(tmp_path):
    check, proc = with_release(tmp_path / "a", None)
    assert (check["status"], check["reason"]) == ("cannot-check", "bad-response")
    assert proc.returncode == 4
    check, _ = with_release(tmp_path / "b", {"tag_name": "latest"})
    assert (check["status"], check["reason"]) == ("cannot-check", "bad-response")
    check, _ = with_release(tmp_path / "c", {"name": "no tag"})
    assert (check["status"], check["reason"]) == ("cannot-check", "bad-response")
    check, _ = with_release(tmp_path / "d", {"message": "Not Found", "status": "404"})
    assert (check["status"], check["reason"]) == ("cannot-check", "no-release")
    check, _ = with_release(tmp_path / "e", {"message": "rate limit", "status": "403"})
    assert (check["status"], check["reason"]) == ("cannot-check", "release-unreadable")


def test_an_unreadable_installed_version_is_cannot_check(tmp_path):
    check, _ = with_release(tmp_path, {"tag_name": "v9.9.9"}, installed="nine")
    assert (check["status"], check["reason"]) == ("cannot-check", "bad-response")


def test_without_the_kit_root_the_kit_repository_is_unknown(tmp_path):
    check, _ = with_release(tmp_path, {"tag_name": "v9.9.9"}, kit=False)
    assert (check["status"], check["reason"]) == ("cannot-check", "no-kit-root")


def test_a_kit_whose_repository_is_not_on_github_is_not_github(tmp_path):
    dirs = prepare("ok", tmp_path)
    plugin = dirs["kit"] / ".claude-plugin" / "plugin.json"
    plugin.write_text(json.dumps({"repository": "https://example.invalid/kit"}), encoding="utf-8")
    proc = doctor("--api-dir", str(dirs["api"]), "--kit-root", str(dirs["kit"]), "--json",
                  str(dirs["root"]))  # fmt: skip
    check = checks_of(proc.stdout)["kit-behind"]
    assert (check["status"], check["reason"]) == ("cannot-check", "not-github")
    plugin.unlink()
    proc = doctor("--api-dir", str(dirs["api"]), "--kit-root", str(dirs["kit"]), "--json",
                  str(dirs["root"]))  # fmt: skip
    check = checks_of(proc.stdout)["kit-behind"]
    assert (check["status"], check["reason"]) == ("cannot-check", "bad-response")


def test_live_mode_reads_the_kit_release_with_one_get(tmp_path):
    dirs = prepare("ok", tmp_path)
    stub = tmp_path / "bin"
    release = dirs["api"] / "kit-release.json"
    log = stub_gh(stub, f'case "$*" in *releases/latest) /bin/cat \'{release}\';; *) exit 1;; esac')
    proc = doctor(
        "--repo", "example-owner/example-repo", "--kit-root", str(dirs["kit"]), "--json",
        str(dirs["root"]), path=f"{stub}{os.pathsep}{os.environ['PATH']}",
    )  # fmt: skip
    assert checks_of(proc.stdout)["kit-behind"]["status"] == "ok"
    calls = log.read_text(encoding="utf-8").splitlines()
    kit_calls = [c for c in calls if "example-kit" in c]
    assert kit_calls == ["api --method GET repos/example-owner/example-kit/releases/latest"]


def test_live_mode_offline_is_cannot_check(tmp_path):
    dirs = prepare("ok", tmp_path)
    stub = tmp_path / "bin"
    stub_gh(stub, 'echo "dial tcp: lookup api.github.com: no such host" >&2; exit 1')
    proc = doctor(
        "--repo", "example-owner/example-repo", "--kit-root", str(dirs["kit"]), "--json",
        str(dirs["root"]), path=f"{stub}{os.pathsep}{os.environ['PATH']}",
    )  # fmt: skip
    check = checks_of(proc.stdout)["kit-behind"]
    assert (check["status"], check["reason"]) == ("cannot-check", "offline")


def test_the_text_report_prints_a_hint_for_each_new_reason():
    from doctor import HINTS

    assert "no-release" in HINTS and "release-unreadable" in HINTS
    assert "kit" in HINTS["no-release"] and "kit" in HINTS["release-unreadable"]
