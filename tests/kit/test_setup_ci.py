"""/agk:setup build (f): in CI mode (`execution = "hosted"`) the command installs nothing and
checks the repository with GET calls only, naming each missing item by its setting (brief #1465,
SPEC-0065 rules 10 and 16, ADR-0623; REQ-072 AC6).

Saved GitHub answers behind a `gh` stub (a recorder of every call), a fake machine read and no
network, no model and no install. Invented names of example.com only.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))
_spec = importlib.util.spec_from_file_location("agk_setup_ci", SCRIPTS / "setup.py")
setup = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(setup)

REPO = "repos/example-org/example-project"
SECRET = re.compile(r"gh[pousr]_[A-Za-z0-9]{16,}|github_pat_|password\s*[=:]", re.IGNORECASE)
FAKE_VALUE = "ghp_" + "Example0123456789Example"  # token-shaped, served by the stub, never shown


def kit_workflows() -> list[str]:
    return list(setup.kit_workflows())


def answers(**over) -> dict:
    """A repository the kit has fully set up on GitHub: every check is met."""
    saved = {
        REPO: {"default_branch": "main"},
        f"{REPO}/actions/permissions": {"enabled": True},
        f"{REPO}/actions/workflows": {
            "workflows": [{"path": p, "state": "active"} for p in kit_workflows()]
        },
        f"{REPO}/rulesets": [{"name": "agk", "enforcement": "active"}],
        f"{REPO}/branches/main": {"name": "main", "protected": True},
        f"{REPO}/environments/merge/secrets": {
            "secrets": [{"name": "AGK_MERGE_TOKEN", "value": FAKE_VALUE}]
        },
    }
    saved.update(over)
    return {k: v for k, v in saved.items() if v is not None}


class Gh:
    """The `gh` stub: serves saved answers by path, records every call; any other call is 127."""

    def __init__(self, monkeypatch, saved):
        self.saved, self.calls = saved, []
        monkeypatch.setattr(setup, "capture", self.capture)
        monkeypatch.setattr(setup, "run_cmd", self.run_cmd)

    def capture(self, args, cwd=None):
        self.calls.append(list(args))
        if args[:4] == ["gh", "api", "-X", "GET"] and args[4] in self.saved:
            return json.dumps(self.saved[args[4]])
        return None

    def run_cmd(self, args, cwd):
        self.calls.append(list(args))
        return 127


def project(tmp_path: Path, text='execution = "hosted"\nreview_mode = "solo"\n') -> Path:
    (tmp_path / "agk.toml").write_text(text, encoding="utf-8")
    return tmp_path


def run(tmp_path, capsys, extra=(), text=None):
    root = project(tmp_path, *([text] if text else []))
    m = tmp_path.parent / "machine-ci.json"
    m.write_text(json.dumps({"os": "Linux", "remote": "example-org/example-project"}), "utf-8")
    code = setup.main(["ci", "--machine", str(m), "--root", str(root), *extra])
    return code, capsys.readouterr().out


def table(tmp_path, capsys, text=None):
    code, out = run(tmp_path, capsys, ["--json"], text)
    return code, json.loads(out)


def test_ac6_a_set_up_repository_passes_with_get_calls_only(tmp_path, capsys, monkeypatch):
    """REQ-072 AC6: rule 10: every check met, each row skipped, every call a `gh api -X GET`."""
    gh = Gh(monkeypatch, answers())
    code, out = table(tmp_path, capsys)
    assert code == 0 and out["pending"] == [] and out["missing"] == []
    assert [r["step"] for r in out["steps"]] == list(setup.CI_CHECKS)
    assert {r["result"] for r in out["steps"]} == {"skipped"}
    assert gh.calls and all(c[:4] == ["gh", "api", "-X", "GET"] for c in gh.calls)


def test_ac6_ci_mode_installs_nothing_and_writes_nothing(tmp_path, capsys, monkeypatch):
    """REQ-072 AC6: rule 16: no install call, no command run, no file written."""
    gh = Gh(monkeypatch, answers(**{f"{REPO}/actions/permissions": {"enabled": False}}))
    root = project(tmp_path)
    before = sorted(p.name for p in root.iterdir())
    run(tmp_path, capsys)
    assert not any(c[0] in ("winget", "apt", "apt-get", "dnf", "brew") for c in gh.calls)
    assert all(c[:4] == ["gh", "api", "-X", "GET"] for c in gh.calls)
    assert sorted(p.name for p in root.iterdir()) == before


@pytest.mark.parametrize(
    ("over", "step", "setting"),
    [
        ({"actions/permissions": {"enabled": False}}, "actions", "Actions permissions"),
        ({"actions/workflows": {"workflows": []}}, "workflows", "the kit's workflows"),
        ({"rulesets": [], "branches/main": {"name": "main", "protected": False}}, "rules",
         "kit/templates/ruleset.json"),
        ({"environments/merge/secrets": {"secrets": []}}, "secrets", "auto_merge"),
    ],
)  # fmt: skip
def test_ac6_each_missing_item_is_one_line_naming_its_setting(
    tmp_path, capsys, monkeypatch, over, step, setting
):
    """REQ-072 AC6: rule 10: one line per missing item for the owner, by its setting."""
    Gh(monkeypatch, answers(**{f"{REPO}/{k}": v for k, v in over.items()}))
    flow = 'execution = "hosted"\n[flow]\nauto_merge = true\n'
    code, out = table(tmp_path, capsys, flow)
    assert code == 1 and out["pending"] == [step]
    assert len(out["missing"]) == 1 and f"(setting: {setting})" in out["missing"][0]
    _, text = run(tmp_path, capsys, text=flow)
    assert sum(line.startswith("missing: ") for line in text.splitlines()) == 1


def test_ac6_a_missing_workflow_is_named_and_a_disabled_one_counts_as_missing(
    tmp_path, capsys, monkeypatch
):
    """REQ-072 AC6: rule 10: each absent or disabled kit workflow is named in the one line."""
    found = [{"path": p, "state": "active"} for p in kit_workflows()[1:]]
    found[0]["state"] = "disabled_manually"
    Gh(monkeypatch, answers(**{f"{REPO}/actions/workflows": {"workflows": found}}))
    _, out = table(tmp_path, capsys)
    line = out["missing"][0]
    assert Path(kit_workflows()[0]).name in line and Path(kit_workflows()[1]).name in line


def test_ac6_branch_rules_alone_satisfy_the_rules_check(tmp_path, capsys, monkeypatch):
    """REQ-072 AC6: rule 10: the ruleset or the branch rules: either one is enough."""
    Gh(monkeypatch, answers(**{f"{REPO}/rulesets": []}))
    _, out = table(tmp_path, capsys)
    assert out["missing"] == []


def test_ac6_the_merge_secret_is_checked_only_when_auto_merge_is_on(tmp_path, capsys, monkeypatch):
    """REQ-072 AC6: rule 10: the secrets the kit needs: none without `auto_merge = true`."""
    gh = Gh(monkeypatch, answers(**{f"{REPO}/environments/merge/secrets": {"secrets": []}}))
    _, out = table(tmp_path, capsys)
    assert out["missing"] == [] and not any("secrets" in c[4] for c in gh.calls)


def test_ac6_an_unreadable_answer_is_unknown_never_missing(tmp_path, capsys, monkeypatch):
    """REQ-072 AC6: a check GitHub does not answer for this sign-in is `waiting`, unknown."""
    Gh(monkeypatch, answers(**{f"{REPO}/actions/permissions": None}))
    code, out = table(tmp_path, capsys)
    row = next(r for r in out["steps"] if r["step"] == "actions")
    assert code == 1 and row["result"] == "waiting" and "unknown" in row["note"]
    assert out["missing"] == []


def test_ac6_only_ci_mode_runs_the_repository_checks(tmp_path, capsys, monkeypatch):
    """REQ-072 AC6: rule 16: local and personal mode are refused by the setting, nothing run."""
    gh = Gh(monkeypatch, answers())
    code, out = run(tmp_path, capsys, text='execution = "local"\n')
    assert code == 1 and "(setting: execution)" in out and gh.calls == []
    (tmp_path / "agk.toml").unlink()
    m = tmp_path.parent / "machine-ci.json"
    code = setup.main(["ci", "--machine", str(m), "--root", str(tmp_path)])
    assert code == 1 and "(setting: execution)" in capsys.readouterr().out and gh.calls == []


def test_ac6_no_remote_is_one_line_and_no_call(tmp_path, capsys, monkeypatch):
    """REQ-072 AC6: a folder without a GitHub remote stops with one line, no call made."""
    gh = Gh(monkeypatch, answers())
    root = project(tmp_path)
    m = tmp_path.parent / "machine-none.json"
    m.write_text(json.dumps({"os": "Linux", "remote": None}), encoding="utf-8")
    code = setup.main(["ci", "--machine", str(m), "--root", str(root)])
    out = capsys.readouterr().out
    assert code == 1 and len(out.strip().splitlines()) == 1 and gh.calls == []


def test_ac5_no_output_holds_a_token_or_a_secret_value(tmp_path, capsys, monkeypatch):
    """REQ-072 AC5, AC6: rule 10: secrets are named by their setting, never read or printed."""
    Gh(monkeypatch, answers())
    flow = 'execution = "hosted"\n[flow]\nauto_merge = true\n'
    outs = [run(tmp_path, capsys, extra, flow)[1] for extra in ([], ["--json"])]
    Gh(monkeypatch, answers(**{f"{REPO}/environments/merge/secrets": {"secrets": []}}))
    outs += [run(tmp_path, capsys, extra, flow)[1] for extra in ([], ["--json"])]
    assert not any(SECRET.search(o) or FAKE_VALUE in o or "AGK_MERGE_TOKEN" in o for o in outs)
