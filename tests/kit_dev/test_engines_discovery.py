"""Kit-only tests of `engines.py questions --work-type <kind>` (SPEC-0048 rule 4; REQ-055 AC2;
brief #686).

Discovery asks the kit's ten common questions and the playbook's `[[discovery]]` questions, each
once: `questions --work-type <kind>` prints the ten, then the questions of
`config/playbooks/<kind>.toml`; with no flag the declared work type (`[delivery] work_type`) selects
the playbook; with neither the output is today's, byte for byte. An unknown kind, a missing
playbook, a playbook that fails the check, or a playbook id that repeats a common topic is
refused, naming the rule and the setting and never a value. `/agk:vision` reads the questions,
at most three per round. Fixtures in `tmp_path`, invented data, no network.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import tomllib

from conftest import KIT_ROOT, clean_env

SCRIPT = KIT_ROOT / "scripts" / "agk" / "engines.py"
PLAYBOOKS = KIT_ROOT / "config" / "playbooks"
TEN = (
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
)
FIVE = ("constraints", "success", "data-rules", "environments", "non-functional")
# The SHA-256 and length of `engines.py questions` on the default branch before this build.
TODAY_SHA = "33699814eaf2861eeb35806b25f31938212c1dfa07c8acd192377eb3e0162cbf"
TODAY_BYTES = 702


def engines(root, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "questions", *args, "--root", str(root)],
        capture_output=True,
        text=True,
        env=clean_env(),
    )


def project(tmp_path, *names, declared=None):
    folder = tmp_path / "config" / "playbooks"
    folder.mkdir(parents=True)
    for name in names:
        shutil.copyfile(PLAYBOOKS / f"{name}.toml", folder / f"{name}.toml")
    if declared:
        (tmp_path / "agk.toml").write_text(
            f'[delivery]\nwork_type = "{declared}"\n', encoding="utf-8"
        )
    return tmp_path


def ids(stdout):
    return [line.split("\t")[0] for line in stdout.splitlines()]


def playbook_ids(name):
    data = tomllib.loads((PLAYBOOKS / f"{name}.toml").read_text(encoding="utf-8"))
    return [entry["id"] for entry in data["discovery"]]


def test_ac2_without_a_declaration_the_output_is_today_byte_for_byte(tmp_path):
    """REQ-055 AC2: brief #686 answer 2 (no declaration, no flag: unchanged)."""
    proc = engines(project(tmp_path, "web-app"))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    raw = proc.stdout.encode("utf-8")
    assert len(raw) == TODAY_BYTES
    assert hashlib.sha256(raw).hexdigest() == TODAY_SHA


def test_ac2_with_a_work_type_the_ten_then_the_playbook_s_questions_once_each(tmp_path):
    """REQ-055 AC2: SPEC-0048 rule 4 (the ten common topics, then the playbook's, once each)."""
    proc = engines(project(tmp_path, "web-app"), "--work-type", "web-app")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    found = ids(proc.stdout)
    assert found == [*TEN, *playbook_ids("web-app")]
    assert found[len(TEN) : len(TEN) + len(FIVE)] == list(FIVE)
    assert len(found) == len(set(found))
    lines = proc.stdout.splitlines()
    assert all(len(line.split("\t")) == 2 and line.endswith("?") for line in lines)
    plain = engines(tmp_path).stdout
    assert proc.stdout.startswith(plain)


def test_ac2_the_declared_work_type_selects_the_playbook_without_the_flag(tmp_path):
    """REQ-055 AC2: SPEC-0048 rule 4 (the declaration of SPEC-0038 rule 5 selects the playbook)."""
    proc = engines(project(tmp_path, "rag-app", declared="rag-app"))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ids(proc.stdout) == [*TEN, *playbook_ids("rag-app")]


def test_ac2_the_flag_wins_over_the_declaration(tmp_path):
    """REQ-055 AC2: SPEC-0048 rule 5 (discovery's kind is proposed, the flag names it)."""
    root = project(tmp_path, "rag-app", "web-app", declared="rag-app")
    proc = engines(root, "--work-type", "web-app")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ids(proc.stdout) == [*TEN, *playbook_ids("web-app")]


def test_ac2_an_unknown_work_type_is_refused_naming_the_setting(tmp_path):
    """REQ-055 AC2: SPEC-0048 rules 4 and 15 (the refusal names the setting, never the value)."""
    proc = engines(project(tmp_path, "web-app"), "--work-type", "zz-unknown-kind")
    assert proc.returncode == 1
    assert "rule 4" in proc.stdout and "work-type" in proc.stdout
    assert "zz-unknown-kind" not in proc.stdout + proc.stderr


def test_ac2_a_missing_playbook_is_refused(tmp_path):
    """REQ-055 AC2: SPEC-0048 rule 4 (a kind with no shipped playbook has no questions to add)."""
    proc = engines(project(tmp_path, "web-app"), "--work-type", "mobile")
    assert proc.returncode == 1
    assert "rule 4" in proc.stdout and "config/playbooks/" in proc.stdout
    assert "mobile" not in proc.stdout + proc.stderr


def test_ac2_a_playbook_that_fails_the_check_is_refused(tmp_path):
    """REQ-055 AC2: SPEC-0048 rule 4 (questions only from a playbook that passes the check)."""
    root = project(tmp_path, "web-app")
    path = root / "config" / "playbooks" / "web-app.toml"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace('id = "success"', 'id = "zz-not-success"', 1), encoding="utf-8")
    proc = engines(root, "--work-type", "web-app")
    assert proc.returncode == 1
    assert "check_playbooks.py" in proc.stdout and "zz-not-success" not in proc.stdout


def test_ac2_a_playbook_id_that_repeats_a_common_topic_is_refused(tmp_path):
    """REQ-055 AC2: SPEC-0048 rule 4 (each question once: a common topic is never asked again)."""
    root = project(tmp_path, "web-app")
    path = root / "config" / "playbooks" / "web-app.toml"
    extra = '\n[[discovery]]\nid = "users"\ntext = "Zz who uses it again?"\n'
    path.write_text(path.read_text(encoding="utf-8") + extra, encoding="utf-8")
    proc = engines(root, "--work-type", "web-app")
    assert proc.returncode == 1
    assert "rule 4" in proc.stdout and "Zz who" not in proc.stdout


def test_ac2_a_declaration_with_a_problem_is_refused_without_the_flag(tmp_path):
    """REQ-055 AC2: SPEC-0038 rule 5 (a refused declaration is refused here as in `stack-write`)."""
    root = project(tmp_path, "web-app", declared="zz-unknown-kind")
    proc = engines(root)
    assert proc.returncode == 1
    assert "work_type" in proc.stdout and "zz-unknown-kind" not in proc.stdout


def test_ac2_the_vision_skill_reads_the_questions_three_per_round():
    """REQ-055 AC2: brief #686 answer 2 (`skills/vision/SKILL.md` reads them)."""
    text = (KIT_ROOT / "skills" / "vision" / "SKILL.md").read_text(encoding="utf-8")
    assert 'engines.py" questions --work-type' in text or "questions [--work-type" in text
    assert "at most three per round" in text
    for fixed in FIVE:
        assert f"`{fixed}`" in text
