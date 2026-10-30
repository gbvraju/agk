"""Kit-only tests of the plugin, the marketplace and the intake rules (SPEC-0005 rules 2-20)."""

from __future__ import annotations

import json
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import KIT_ROOT, clean_env, git, make_repo, manifest, run_init, set_handle, snapshot

PLUGIN = KIT_ROOT / ".claude-plugin"
SKILLS = KIT_ROOT / "skills"
COMMANDS = [
    "adopt",
    "architect",
    "brief",
    "confirm",
    "design",
    "doctor",
    "init",
    "issue",
    "launch",
    "review",
    "review-pass",
    "ruleset",
    "spec",
    "stack",
    "start",
    "uninstall",
    "upgrade",
    "vision",
]
USER_ONLY = [
    "adopt",
    "brief",
    "confirm",
    "design",
    "init",
    "issue",
    "launch",
    "review-pass",
    "ruleset",
    "spec",
    "stack",
    "start",
    "uninstall",
    "upgrade",
    "vision",
]
FORBIDDEN_VERBS = ["git push", "git commit", "gh pr", "gh issue close", "gh issue comment"]
SCRIPT_CALL = re.compile(r'^\s*python3 "\$\{CLAUDE_PLUGIN_ROOT\}/scripts/agk/(\w+)\.py"(.*)$', re.M)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def frontmatter(text: str) -> dict[str, str]:
    head = text.split("---\n", 2)[1]
    out = {}
    for line in head.splitlines():
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip()
    return out


def skill(name: str) -> str:
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


def calls(name: str) -> list[tuple[str, list[str]]]:
    """(script, arguments) of every script call a skill shows."""
    return [(m.group(1), shlex.split(m.group(2))) for m in SCRIPT_CALL.finditer(skill(name))]


def real(args: list[str]) -> list[str]:
    return [a for a in args if a != "--dry-run"]


def test_ac1_plugin_manifest_parses_and_carries_the_kit_version():
    """REQ-014 AC1: rules 6 and 13."""
    plugin = load(PLUGIN / "plugin.json")
    assert plugin["name"] == "agk"
    assert plugin["version"] == manifest()["kit_version"]
    assert plugin["description"]


def test_ac1_marketplace_parses_and_lists_the_one_plugin_at_the_root():
    """REQ-014 AC1: rules 12 and 13."""
    market = load(PLUGIN / "marketplace.json")
    assert market["name"] == "agk"
    assert market["owner"]["name"]
    assert [p["name"] for p in market["plugins"]] == ["agk"]
    entry = market["plugins"][0]
    assert entry["source"] == "."
    assert "version" not in entry  # the manifest version wins (rule 13)
    assert entry["name"] == load(PLUGIN / "plugin.json")["name"]


@pytest.mark.skipif(shutil.which("claude") is None, reason="the claude CLI is not installed")
def test_ac1_claude_plugin_validate_passes():
    """REQ-014 AC1: rule 12 (runs only when the claude CLI is installed)."""
    proc = subprocess.run(
        ["claude", "plugin", "validate", "."],
        cwd=KIT_ROOT,
        capture_output=True,
        text=True,
        env=clean_env(),
        timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_ac2_one_skill_per_command_named_for_its_directory():
    """REQ-014 AC2: rules 6 and 8."""
    assert sorted(p.name for p in SKILLS.iterdir()) == COMMANDS
    for name in COMMANDS:
        head = frontmatter(skill(name))
        assert head["name"] == name
        assert head["description"]
        assert (SKILLS / name / "SKILL.md").is_file()


def test_ac2_each_skill_names_the_script_it_runs_and_the_script_exists():
    """REQ-014 AC2: rule 19 (the issue skill runs the user's own `gh`, no script)."""
    expected = {
        "init": {"init"},
        "adopt": {"adopt"},
        "doctor": {"doctor"},
        "upgrade": {"upgrade"},
        "uninstall": {"uninstall"},
        "spec": {"new_spec", "intake"},
        "brief": {"new_spec"},
        "review": {"review_context", "check_review_report"},
        "issue": set(),
        "ruleset": {"ruleset"},
        "architect": {"playbook"},
        "start": {"playbook"},
    }
    for name, scripts in expected.items():
        assert {script for script, _ in calls(name)} == scripts, name
        for script in scripts:
            assert (KIT_ROOT / "scripts" / "agk" / f"{script}.py").is_file(), script


def test_ac2_writing_skills_turn_off_model_invocation_and_readers_do_not():
    """REQ-014 AC2: rule 9 (`disable-model-invocation`, confirmed in the verify record)."""
    for name in COMMANDS:
        value = frontmatter(skill(name)).get("disable-model-invocation")
        assert (value == "true") == (name in USER_ONLY), name


def test_ac2_no_skill_runs_a_forbidden_verb_and_only_issue_creates_an_issue():
    """REQ-014 AC2: rule 10."""
    for name in COMMANDS:
        text = skill(name)
        for verb in FORBIDDEN_VERBS:
            assert verb not in text, (name, verb)
        assert ("gh issue create" in text) == (name == "issue"), name
        assert ("gh api --method POST|PUT|PATCH" in text) == (name == "ruleset"), name


def test_ac2_doctor_and_review_skills_write_nothing_and_run_no_gh_or_git():
    """REQ-014 AC2: SPEC-0006 rule 20 (no write verb beyond the script call)."""
    for name in ("doctor", "review"):
        text = skill(name)
        assert not re.search(r"\bgh\b|\bgit\b", text.replace("`gh`", "").replace("own `gh`", "")), (
            name
        )
    assert "--kit-root" in skill("doctor")
    assert 'doctor.py" --kit-root "${CLAUDE_PLUGIN_ROOT}"' in skill("doctor")


def test_ac2_no_skill_pre_approves_tools():
    """REQ-014 AC2: the plugin asks for no permission grant (Q-K3-73)."""
    for name in COMMANDS:
        assert "allowed-tools" not in frontmatter(skill(name)), name


def test_ac2_plugin_ships_no_hook_server_monitor_bin_or_agent():
    """REQ-014 AC2: rule 7."""
    for rel in ("hooks", "bin", "agents", "commands", "monitors", ".mcp.json", ".lsp.json"):
        assert not (KIT_ROOT / rel).exists(), rel
    plugin = load(PLUGIN / "plugin.json")
    for key in ("hooks", "mcpServers", "lspServers", "monitors", "agents", "commands", "bin"):
        assert key not in plugin, key
    assert sorted(p.name for p in PLUGIN.iterdir()) == ["marketplace.json", "plugin.json"]


def test_ac2_plugin_paths_are_protected_classes_and_not_installed():
    """REQ-014 AC2: rule 20."""
    entries = (KIT_ROOT / "config" / "protected-paths.txt").read_text(encoding="utf-8")
    assert ".claude-plugin/" in entries.split() and "skills/" in entries.split()
    reviewers = (KIT_ROOT / "config" / "reviewers.yaml").read_text(encoding="utf-8")
    assert reviewers.count(".claude-plugin/") == 2 and reviewers.count("skills/") == 2
    installed = set(manifest()["verbatim"]) | set(manifest()["templates"])
    assert not [p for p in installed if p.startswith((".claude-plugin/", "skills/"))]


def snapshot_hashes(root: Path) -> dict[str, str]:
    return {rel: digest for rel, (digest, _) in snapshot(root).items()}


def run_call(
    script: str, args: list[str], cwd: Path, root: Path = KIT_ROOT
) -> subprocess.CompletedProcess:
    if script in ("init", "adopt"):  # between releases is not a release (ADR-0160, ADR-0200)
        args = [*args, "--unreleased"]
    return subprocess.run(
        [sys.executable, str(root / "scripts" / "agk" / f"{script}.py"), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=clean_env(),
    )


def test_ac2_init_skill_call_writes_the_same_files_as_the_script(tmp_path):
    """REQ-014 AC2: rule 5 (the skill's call is the script's call)."""
    (script, args), *_ = calls("init")
    assert script == "init" and args == [".", "--dry-run"]
    by_script, by_skill = make_repo(tmp_path / "a" / "proj"), make_repo(tmp_path / "b" / "proj")
    assert run_init(by_script).returncode == 0
    assert run_call(script, real(args), by_skill).returncode == 0
    assert snapshot_hashes(by_script) == snapshot_hashes(by_skill)


def test_ac2_init_dry_run_in_the_skill_writes_nothing(tmp_path):
    """REQ-014 AC2: rule 8 (the first call of a writing skill is a dry run)."""
    repo = make_repo(tmp_path / "proj")
    before = snapshot_hashes(repo)
    assert run_call("init", calls("init")[0][1], repo).returncode == 0
    assert snapshot_hashes(repo) == before


def test_ac2_adopt_skill_call_writes_the_same_files_as_the_script(tmp_path):
    """REQ-014 AC2: rule 5."""
    (script, args), *_ = calls("adopt")
    assert script == "adopt" and args == [".", "--dry-run"]
    by_script, by_skill = make_repo(tmp_path / "a" / "proj"), make_repo(tmp_path / "b" / "proj")
    assert run_call("adopt", ["."], by_script).returncode == 0
    assert run_call(script, real(args), by_skill).returncode == 0
    assert snapshot_hashes(by_script) == snapshot_hashes(by_skill)


def test_ac2_upgrade_skill_call_is_a_no_op_on_a_current_install(tmp_path):
    """REQ-014 AC2: rule 5 and SPEC-0008 rule 17."""
    (script, args), *_ = calls("upgrade")
    assert script == "upgrade" and args == [".", "--dry-run"]
    repo = make_repo(tmp_path / "proj")
    assert run_init(repo).returncode == 0
    before = snapshot_hashes(repo)
    assert run_call(script, args, repo).returncode == 0
    assert run_call(script, real(args), repo).returncode == 0
    assert snapshot_hashes(repo) == before


def templates_in(root: Path) -> Path:
    for rel in (
        "docs/specs/TEMPLATE.md",
        "docs/adr/TEMPLATE.md",
        "docs/briefs/TEMPLATE.md",
        "docs/requirements.md",
    ):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(KIT_ROOT / rel, root / rel)
    return root


def test_ac2_spec_and_brief_skill_calls_run_new_spec_on_the_repository(tmp_path):
    """REQ-014 AC2: rule 5 (the skills' calls are accepted by the script)."""
    root = templates_in(tmp_path / "proj")
    for name, kind, path in (
        ("spec", "spec", "docs/specs/0001-t.md"),
        ("brief", "brief", "docs/briefs/t.md"),
    ):
        script, args = calls(name)[0]
        assert script == "new_spec" and args[0] == kind
        shown = [{"TITLE": "T", "REQ-nnn": "REQ-001"}.get(a, a) for a in args]
        proc = run_call(script, shown, root)
        assert proc.returncode == 0, proc.stdout
        assert (root / path).is_file()


def test_ac2_review_skill_runs_the_review_scripts_in_order():
    """REQ-014 AC2: SPEC-0005 rule 8."""
    assert [s for s, _ in calls("review")] == ["review_context", "check_review_report"]
    assert "reviewer" in skill("review") and "never an approval" in skill("review")


def test_ac3_no_law_file_depends_on_the_plugin():
    """REQ-014 AC3: rule 2 (the checks, hooks, workflows and scripts name no plugin variable)."""
    for rel in manifest()["verbatim"]:
        if rel.startswith("tests/kit/"):
            continue
        text = (KIT_ROOT / rel).read_text(encoding="utf-8")
        assert "CLAUDE_PLUGIN" not in text, rel
        if rel.startswith((".github/", ".claude/")) or rel in ("Makefile", "agk.mk"):
            assert "/agk:" not in text, rel


def test_ac3_an_install_has_no_plugin_file_and_governance_runs_without_it(tmp_path):
    """REQ-014 AC3: rule 2."""
    repo = make_repo(tmp_path / "proj")
    assert run_init(repo).returncode == 0
    assert not (repo / ".claude-plugin").exists() and not (repo / "skills").exists()
    set_handle(repo)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "install")
    proc = subprocess.run(
        ["make", "governance"], cwd=repo, capture_output=True, text=True, env=clean_env()
    )
    assert proc.returncode == 0, proc.stdout[-800:] + proc.stderr[-400:]


def test_ac4_no_script_or_workflow_reads_an_intake_issue():
    """REQ-014 AC4: rule 17 (d): the only issue reads are the kit's own report issues, by label."""
    files = [
        *(KIT_ROOT / "scripts" / "agk").glob("*.py"),
        *(KIT_ROOT / ".github" / "workflows").glob("*.yml"),
    ]
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert "gh issue view" not in text, path.name
        for line in text.splitlines():
            if "gh issue list" in line:
                assert "--label agk-" in line, path.name


def test_ac4_issue_templates_are_installed_and_say_the_issue_decides_nothing(tmp_path):
    """REQ-014 AC4: rule 17."""
    repo = make_repo(tmp_path / "proj")
    assert run_init(repo).returncode == 0
    for kind in ("proposal", "question", "report"):
        text = (repo / ".github" / "ISSUE_TEMPLATE" / f"{kind}.md").read_text(encoding="utf-8")
        assert text.startswith("---\n") and "intake only" in text
        assert frontmatter(text)["name"]


def test_ac4_pull_request_template_has_an_optional_issue_line_that_no_check_requires(tmp_path):
    """REQ-014 AC4: rule 17 (c)."""
    template = (KIT_ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md").read_text(encoding="utf-8")
    assert re.search(r"(?m)^Issue: #nnn \(optional", template)
    body = tmp_path / "body.md"
    for extra in ("", "Issue: #12\n"):
        body.write_text(
            f"Advances: REQ-001\n{extra}Build-state row: 2026-10-16 | x | REQ-001\n"
            "Summary: A change.\n",
            encoding="utf-8",
        )
        proc = run_call("check_pr_body", [str(body)], KIT_ROOT)
        assert proc.returncode == 0, proc.stdout


def settings_entries(output: str) -> dict:
    lines = [
        ln.strip()
        for ln in output.splitlines()
        if ln.strip().startswith(('"extraKnownMarketplaces"', '"enabledPlugins"'))
    ]
    return json.loads("{" + ",".join(lines) + "}")


def test_ac2_init_and_adopt_print_the_two_settings_entries_and_write_none(tmp_path):
    """REQ-014 AC2: rule 14 (print only)."""
    version = manifest()["kit_version"]
    for tool in ("init", "adopt"):
        repo = make_repo(tmp_path / tool / "proj")
        proc = run_call(tool, ["."], repo)
        assert proc.returncode == 0, proc.stdout
        entries = settings_entries(proc.stdout)
        assert entries["enabledPlugins"] == {"agk@agk": True}
        source = entries["extraKnownMarketplaces"]["agk"]["source"]
        assert source["source"] == "github" and source["ref"] == f"v{version}"
        assert "(verify)" in proc.stdout  # the `ref` form is not confirmed (Q-K3-72)
        settings = (repo / ".claude" / "settings.json").read_text(encoding="utf-8")
        assert "extraKnownMarketplaces" not in settings and "enabledPlugins" not in settings


def test_ac2_readme_states_the_install_and_the_four_trust_caveats():
    """REQ-014 AC2: rules 12 and 15."""
    readme = (KIT_ROOT / "docs" / "guides" / "reference.md").read_text(encoding="utf-8")
    section = readme.split("## Plugin", 1)[1].split("\n## ", 1)[0]
    assert "claude plugin marketplace add gbvraju/agk" in section
    assert "claude plugin install agk@agk" in section
    for phrase in (
        "workspace trust",
        "own machine",
        "cloud session",
        "user's privileges",
        "extraKnownMarketplaces",
        "protected",
    ):
        assert phrase in section, phrase


def test_ac2_ruleset_skill_shows_the_plan_asks_and_never_tightens_on_its_own():
    """REQ-020 AC1: SPEC-0013 rules 19 and 20 (the skill text)."""
    text = skill("ruleset")
    assert [s for s, _ in calls("ruleset")] == ["ruleset"]
    assert calls("ruleset")[0][1][0] == "plan"
    assert "Ask the person" in text and "Never pass `--tighten` on your own" in text
    assert "add-only" in text and "none is stored or asked for" in text
    assert "--payload-dir" in text
