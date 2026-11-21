"""Tests of the shipped api-service playbook (brief #1602, ADR-0682; SPEC-0072 rules 1 and 2).

REQ-045 AC1 and REQ-079 AC1. `config/playbooks/api-service.toml` is a work type of the fixed list
(SPEC-0038 rule 1 as ADR-0682 widens it), composes with `default.toml`, holds the eight enterprise
gate ids and weakens no gate; its `[split]` is foundation, contract, back-end, join; every
`[testing] map` code falls in exactly one of its four layers. `front_door.py detect` proposes it
for an invented service tree and not for a web app. Invented data only (an "opening hours for
shops" service at example.com), fixtures in `tmp_path`, no network.
"""

from __future__ import annotations

import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = KIT_ROOT / "scripts" / "agk"
REL = "config/playbooks/api-service.toml"
PLAYBOOK = KIT_ROOT / REL
ENTERPRISE = {
    "sign-in-permissions",
    "secrets",
    "input-validation",
    "logging-tracing",
    "environment-settings",
    "migrations",
    "accessibility",
    "performance",
}
CHECKS = {"contract-tests", "secrets", "environment-settings"}
JUDGED = {"input-validation", "sign-in-permissions", "logging-tracing"}
GIT = ["git", "-c", "user.name=Ada", "-c", "user.email=ada@example.com"]
GIT += ["-c", "commit.gpgsign=false"]
SERVICE = {
    "pyproject.toml": '[project]\nname = "shop-hours"\ndependencies = ["fastapi>=0.1"]\n',
    "contracts/openapi.yaml": "openapi: 3.0.0\ninfo:\n  title: Opening hours for shops\n",
}
NODE_SERVICE = {"package.json": '{"dependencies": {"@nestjs/core": "1.0.0"}}\n'}
WEB_APP = {"package.json": '{"dependencies": {"react-dom": "1.0.0"}}\n'}

sys.path.insert(0, str(SCRIPTS))
import check_playbooks  # noqa: E402
import playbook_format  # noqa: E402


def data() -> dict:
    return tomllib.loads(PLAYBOOK.read_text(encoding="utf-8"))


def test_api_service_is_a_work_type_and_passes_the_check() -> None:
    """REQ-045 AC1: SPEC-0038 rules 1 to 4 as ADR-0682 widens rule 1."""
    assert playbook_format.WORK_TYPES[-1] == "api-service"
    assert len(playbook_format.WORK_TYPES) == len(set(playbook_format.WORK_TYPES)) == 10
    assert playbook_format.problems(PLAYBOOK, KIT_ROOT) == []
    assert data()["work_type"] == "api-service" == PLAYBOOK.stem
    assert [d["id"] for d in data()["discovery"]][:5] == list(playbook_format.DISCOVERY_IDS)


def test_it_composes_with_default_and_weakens_no_gate() -> None:
    """REQ-079 AC1: the eight enterprise ids, the brief's checks and judgements, none lowered."""
    gates, _, found = check_playbooks.composed(PLAYBOOK, KIT_ROOT)
    assert found == []
    by_id = {g["id"]: g for g in gates}
    assert ENTERPRISE <= set(by_id)
    # brief #1597 (ADR-0677): contract-tests is a check again
    restated = CHECKS - {"contract-tests"}
    assert {gid for gid in CHECKS if by_id[gid]["kind"] == "judgement"} == restated
    for gid in restated:
        assert "(ADR-0666)" in by_id[gid]["reason"] and "step" not in by_id[gid]
    assert by_id["contract-tests"]["kind"] == "check" and by_id["contract-tests"]["step"]
    for gid in JUDGED:
        assert by_id[gid]["kind"] == "judgement"
        assert len(by_id[gid]["reason"].strip()) >= playbook_format.REASON_MIN
    default = playbook_format.load(KIT_ROOT / "config/playbooks/default.toml")
    base = {g["id"]: g for g in default["gates"]}
    own = {g["id"]: g for g in data()["gates"]}
    for gid in set(own) & set(base):
        assert not (base[gid]["kind"] == "check" and own[gid]["kind"] == "judgement"), gid
        assert not (base[gid]["owner_only"] and not own[gid]["owner_only"]), gid


def test_the_split_and_every_map_code_falls_in_one_layer() -> None:
    """REQ-079 AC1: SPEC-0072 rule 2, the four layers and three `allow` entries of ADR-0682."""
    play = data()
    assert play["split"]["brief_order"] == ["foundation", "contract", "back-end", "join"]
    layers = play["architecture"]["layers"]
    assert [layer["name"] for layer in layers] == ["contracts", "api", "domain", "data"]
    allow = {(e["from"], e["to"]) for e in play["architecture"]["allow"]}
    assert allow == {("api", "contracts"), ("api", "domain"), ("domain", "data")}
    paths = [p for layer in layers for p in layer["paths"]]
    codes = [entry["code"] for entry in play["testing"]["map"]]
    assert sorted(codes) == sorted(paths) and len(codes) == len(layers)
    _, _, found = check_playbooks.standard(PLAYBOOK, KIT_ROOT)
    assert found == []


def detect(root: Path, files: dict[str, str]) -> list[str]:
    root.mkdir()
    subprocess.run([*GIT, "init", "-q"], cwd=root, check=True, capture_output=True)  # nosec B603 - fixed argument list
    for rel, body in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(body, encoding="utf-8")
    subprocess.run([*GIT, "add", "-A"], cwd=root, check=True, capture_output=True)  # nosec B603 - fixed argument list
    subprocess.run([*GIT, "commit", "-qm", "invented"], cwd=root, check=True, capture_output=True)  # nosec B603 - fixed argument list
    out = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", str(SCRIPTS / "front_door.py"), "detect", "--root", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert out.returncode == 0, out.stdout + out.stderr
    return out.stdout.splitlines()


def test_detect_proposes_api_service_for_a_service_tree(tmp_path: Path) -> None:
    """REQ-045 AC1: SPEC-0057 rule 5, the signals ADR-0682 lists."""
    assert 'work type: api-service (proposed) file "pyproject.toml" signal fastapi' in detect(
        tmp_path / "py", SERVICE
    )
    assert 'work type: api-service (proposed) file "package.json" signal nestjs' in detect(
        tmp_path / "node", NODE_SERVICE
    )


def test_detect_does_not_propose_it_for_a_web_app(tmp_path: Path) -> None:
    """REQ-045 AC1: a web app's tree stays a web app."""
    out = detect(tmp_path / "web", WEB_APP)
    assert not [line for line in out if "api-service" in line]
    assert 'work type: web-app (proposed) file "package.json" signal react-dom' in out
