"""Tests of the one composition of domain packs (SPEC-0074 rules 3 and 4; REQ-081 AC2; brief #1936).

The packs of `[domain] packs` compose after `default`, the modules and the playbook, in their
order; a jurisdiction pack (`<domain>-<region>`) right after its domain; the project's own pack
last. A pack gate with an earlier id replaces it only when it is the same or stronger, and a
weakening is refused naming the pack's file and the key. Two constraints on one attribute are both
kept and one `warn domains:` line names both, never choosing. A project's pack is never in the
manifest, so the installer and an upgrade never write it. Fixtures in `tmp_path` only: invented
data (example.com), no network.
"""

from __future__ import annotations

import json
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import check_domains  # noqa: E402
import check_playbooks  # noqa: E402

HEAD = 'format = 1\ndomain = "{name}"\ntitle = "An invented pack"\nas_of = "2026-11-25"\n'
TERM = '\n[[terms]]\nterm = "{term}"\nmeaning = "An invented term"\nsynonyms = []\n'
REG = (
    '\n[[regulations]]\nid = "{id}"\ntitle = "An invented rule"\njurisdiction = "global"\n'
    'source = "https://example.com/{id}"\nas_of = "2026-11-25"\ncritical = true\n'
)
CONSTRAINT = (
    '\n[[constraints]]\nid = "{id}"\nattribute = "retention"\nscenario = "stimulus: an order is'
    ' closed; response: it is kept; measure: {years} years"\nhard = true\nbasis = "expected"\n'
)
GATE = (
    '\n[[gates]]\nid = "{id}"\nkind = "{kind}"\ntext = "An invented gate"\nowner_only = {owner}\n'
    'basis = "expected"\n{extra}'
)


def pack(name: str, *, term: str = "", body: str = "") -> str:
    return HEAD.format(name=name) + TERM.format(term=term or f"{name} term") + body


def project(tmp_path: Path, packs: dict[str, str], listed: list[str] | None) -> Path:
    """A stub project: the kit's playbooks, the given packs and an `agk.toml`."""
    shutil.copytree(KIT_ROOT / "config" / "playbooks", tmp_path / "config" / "playbooks")
    folder = tmp_path / "config" / "domains"
    folder.mkdir(parents=True)
    for name, text in packs.items():
        (folder / f"{name}.toml").write_text(text, encoding="utf-8")
    table = "" if listed is None else f"[domain]\npacks = {json.dumps(listed)}\n"
    (tmp_path / "agk.toml").write_text(table, encoding="utf-8")
    return tmp_path


def web(root: Path) -> Path:
    return root / "config" / "playbooks" / "web-app.toml"


def gate_ids(root: Path) -> list[str]:
    return [g["id"] for g in check_playbooks.composed(web(root), root)[0]]


def test_ac2_a_project_pack_composes_after_the_kits(tmp_path):
    """REQ-081 AC2: SPEC-0074 rules 3 and 4 (the project's own pack last)."""
    root = project(
        tmp_path,
        {
            "zz-own": pack(
                "zz-own",
                body=GATE.format(
                    id="zz-own-gate", kind="check", owner="false", extra='step = "lint"\n'
                ),
            ),
            "payments": (KIT_ROOT / "config/domains/payments.toml").read_text(encoding="utf-8"),
        },
        ["zz-own", "payments"],
    )
    assert check_domains.order(root, ["zz-own", "payments"]) == ["payments", "zz-own"]
    ids = gate_ids(root)
    assert ids.index("tests-first") < ids.index("card-data-scope") < ids.index("zz-own-gate")
    assert check_playbooks.composed(web(root), root)[2] == []


def test_ac2_a_pack_gate_restated_weaker_is_refused_naming_the_key(tmp_path):
    """REQ-081 AC2: SPEC-0074 rule 4 (`judgement` of a `check` is weaker)."""
    weak = REG.format(id="zz-law") + GATE.format(
        id="tests-first", kind="judgement", owner="false", extra='regulation = "zz-law"\n'
    )
    root = project(tmp_path, {"zz-shop": pack("zz-shop", body=weak)}, ["zz-shop"])
    gates, _, problems = check_playbooks.composed(web(root), root)
    assert problems == [
        "rule 21: config/domains/zz-shop.toml: a gate is restated weaker (key: kind)"
    ]
    assert next(g for g in gates if g["id"] == "tests-first")["kind"] == "check"


def test_ac2_a_stronger_pack_gate_replaces_the_held_one(tmp_path):
    """REQ-081 AC2: SPEC-0074 rule 4 (`judgement` to `check`, `owner_only` to true)."""
    strong = GATE.format(id="rollback", kind="check", owner="true", extra='step = "lint"\n')
    root = project(tmp_path, {"zz-shop": pack("zz-shop", body=strong)}, ["zz-shop"])
    gates, _, problems = check_playbooks.composed(web(root), root)
    held = next(g for g in gates if g["id"] == "rollback")
    assert problems == [] and held["kind"] == "check" and held["owner_only"] is True


def test_ac2_two_constraints_on_one_attribute_keep_both_and_name_both_packs(tmp_path):
    """REQ-081 AC2: SPEC-0074 rule 4 (the stricter holds until a person decides; Q-D74B-2)."""
    root = project(
        tmp_path,
        {
            "zz-shop": pack("zz-shop", body=CONSTRAINT.format(id="zz-keep", years=5)),
            "zz-bank": pack("zz-bank", body=CONSTRAINT.format(id="zz-hold", years=10)),
        },
        ["zz-shop", "zz-bank"],
    )
    kept = check_domains.items(root)["constraints"]
    assert [(c["id"], c["pack"]) for c in kept] == [("zz-keep", "zz-shop"), ("zz-hold", "zz-bank")]
    assert check_domains.warnings(root) == [
        "warn domains: attribute retention: zz-keep (zz-shop) and zz-hold (zz-bank) differ; "
        "the stricter holds until a person decides"
    ]


def test_ac2_a_jurisdiction_pack_composes_right_after_its_domain(tmp_path):
    """REQ-081 AC2: SPEC-0074 rule 4 (a jurisdiction layer, Q-S0074-9), even listed first."""
    packs = {n: pack(n) for n in ("zz-shop", "zz-shop-eu", "zz-shop-in", "zz-bank")}
    listed = ["zz-shop-in", "zz-bank", "zz-shop", "zz-shop-eu"]
    root = project(tmp_path, packs, listed)
    assert check_domains.order(root, listed) == ["zz-bank", "zz-shop", "zz-shop-in", "zz-shop-eu"]
    assert check_domains.warnings(root) == []


def test_ac2_a_jurisdiction_pack_without_its_domain_is_composed_and_warned(tmp_path):
    """REQ-081 AC2: SPEC-0074 rule 4 (the missing domain is named)."""
    root = project(tmp_path, {n: pack(n) for n in ("zz-shop", "zz-shop-eu")}, ["zz-shop-eu"])
    assert check_domains.order(root, ["zz-shop-eu"]) == ["zz-shop-eu"]
    assert check_domains.warnings(root) == [
        "warn domains: zz-shop-eu is a jurisdiction layer of zz-shop, which `[domain] packs` "
        "does not list"
    ]


def test_ac2_the_order_is_the_persons(tmp_path):
    """REQ-081 AC2: SPEC-0074 rule 4 (two orders of the same packs compose differently)."""
    packs = {
        n: pack(n, body=GATE.format(id="zz-gate", kind="check", owner=o, extra='step = "lint"\n'))
        for n, o in (("zz-shop", "false"), ("zz-bank", "true"))
    }
    first = project(tmp_path / "a", packs, ["zz-shop", "zz-bank"])
    second = project(tmp_path / "b", packs, ["zz-bank", "zz-shop"])
    held = [
        next(g for g in check_playbooks.composed(web(r), r)[0] if g["id"] == "zz-gate")
        for r in (first, second)
    ]
    assert held[0]["owner_only"] is True  # the later, stronger one replaced the first
    assert check_playbooks.composed(web(second), second)[2] == [
        "rule 21: config/domains/zz-shop.toml: a gate is restated weaker (key: owner_only)"
    ]


def test_ac2_a_pack_listed_twice_is_refused_naming_the_setting(tmp_path):
    """REQ-081 AC2: SPEC-0074 rule 4 (edge case: a pack listed twice)."""
    root = project(tmp_path, {"zz-shop": pack("zz-shop")}, ["zz-shop", "zz-shop"])
    problems = check_playbooks.composed(web(root), root)[2]
    assert problems == ["rule 4: agk.toml: the [domain] table is refused (setting: domain.packs)"]


@pytest.mark.parametrize("listed", [None, []])
def test_ac2_no_packs_give_todays_composition_for_every_shipped_playbook(
    tmp_path, monkeypatch, listed
):
    """REQ-081 AC2: SPEC-0074 rule 4 (`packs = []` or no table: exactly today's)."""
    root = project(tmp_path, {"zz-shop": pack("zz-shop")}, listed)
    now = {
        p.name: check_playbooks.composed(p, root)
        for p in sorted((root / "config/playbooks").glob("*.toml"))
    }
    monkeypatch.setattr(
        check_domains, "compose", lambda r, layers: ([(None, x) for x in layers], [])
    )
    before = {
        p.name: check_playbooks.composed(p, root)
        for p in sorted((root / "config/playbooks").glob("*.toml"))
    }
    assert now == before and len(now) == 11


def test_ac2_every_layer_passes_through_the_one_judgement(tmp_path, monkeypatch):
    """REQ-081 AC2: brief #1936 answer 9 (the composed list is the only input of `_weakened`)."""
    root = project(tmp_path, {}, None)
    seen: list[tuple] = []
    real = check_playbooks._weakened
    monkeypatch.setattr(
        check_playbooks, "_weakened", lambda n, h: seen.append((n, h)) or real(n, h)
    )
    planted = {"gates": [{"id": "tests-first", "kind": "judgement", "owner_only": False}]}
    monkeypatch.setattr(
        check_domains,
        "compose",
        lambda r, layers: ([(None, x) for x in layers] + [("config/domains/zz.toml", planted)], []),
    )
    problems = check_playbooks.composed(web(root), root)[2]
    assert problems == ["rule 21: config/domains/zz.toml: a gate is restated weaker (key: kind)"]
    assert any(new is planted["gates"][0] for new, _ in seen)


def test_ac2_items_are_kept_once_at_their_first_place(tmp_path):
    """REQ-081 AC2: SPEC-0074 rule 4 (each item once, at its first place)."""
    root = project(
        tmp_path,
        {"zz-shop": pack("zz-shop", term="basket"), "zz-bank": pack("zz-bank", term="basket")},
        ["zz-shop", "zz-bank"],
    )
    terms = check_domains.items(root)["terms"]
    assert [(t["term"], t["pack"]) for t in terms] == [("basket", "zz-shop")]


def test_ac2_the_shipped_packs_are_the_manifests():
    """REQ-081 AC2: SPEC-0074 rule 3 (`SHIPPED` is the manifest's `config/domains/` list)."""
    manifest = json.loads((KIT_ROOT / "kit/manifest.json").read_text(encoding="utf-8"))
    listed = {Path(p).stem for p in manifest["verbatim"] if p.startswith("config/domains/")}
    assert set(check_domains.SHIPPED) == listed


def test_ac2_install_and_upgrade_leave_a_project_pack_unchanged(tmp_path):
    """REQ-081 AC2: SPEC-0074 rule 3 (fix list on 0ed1a719 item 5: a real install and upgrade)."""
    target = tmp_path / "project"
    (target / "config" / "domains").mkdir(parents=True)
    (target / "README.md").write_text("An example project, example.com.\n", encoding="utf-8")
    own = target / "config" / "domains" / "zz-own.toml"
    text = pack("zz-own")
    own.write_text(text, encoding="utf-8")
    init = run([str(KIT_ROOT / "scripts/agk/init.py"), str(target), "--unreleased"], tmp_path)
    assert init.returncode == 0, init.stdout + init.stderr
    assert own.read_text(encoding="utf-8") == text
    for args in (["init", "-q"], ["add", "-A"]):
        subprocess.run(["git", *args], cwd=target, check=True, capture_output=True)  # nosec B603 B607 - fixed argument list, no shell
    done = run([str(KIT_ROOT / "scripts/agk/upgrade.py"), str(target)], tmp_path)
    assert done.returncode == 0, done.stdout + done.stderr
    assert own.read_text(encoding="utf-8") == text
    assert "zz-own" not in done.stdout


def run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, *args], cwd=cwd, capture_output=True, text=True, check=False
    )


def test_ac2_a_pack_gate_that_moves_a_check_to_another_step_is_refused(tmp_path):
    """REQ-081 AC2: SPEC-0048 rule 21 (fix list on 0ed1a719 item 1: a check keeps its step)."""
    moved = GATE.format(id="tests-first", kind="check", owner="false", extra='step = "lint"\n')
    root = project(tmp_path, {"zz-shop": pack("zz-shop", body=moved)}, ["zz-shop"])
    gates, _, problems = check_playbooks.composed(web(root), root)
    assert problems == [
        "rule 21: config/domains/zz-shop.toml: a gate is restated weaker (key: step)"
    ]
    assert next(g for g in gates if g["id"] == "tests-first")["step"] == "tests-floor"


def test_ac2_a_jurisdiction_without_its_domain_stays_where_it_is_listed(tmp_path):
    """REQ-081 AC2: brief #1936 answer 7 (fix list on 0ed1a719 item 2)."""
    shipped = {
        n: (KIT_ROOT / f"config/domains/{n}.toml").read_text(encoding="utf-8")
        for n in check_domains.SHIPPED
    }
    root = project(tmp_path, {**shipped, "payments-eu": pack("payments-eu")}, None)
    assert check_domains.order(root, ["payments-eu", "field-service"]) == [
        "payments-eu",
        "field-service",
    ]


def test_ac2_a_shipped_pack_is_never_another_packs_layer(tmp_path):
    """REQ-081 AC2: SPEC-0074 rule 4 (fix list on 0ed1a719 item 4)."""
    packs = {n: pack(n) for n in ("aa", "field")}
    packs["field-service"] = (KIT_ROOT / "config/domains/field-service.toml").read_text(
        encoding="utf-8"
    )
    root = project(tmp_path, packs, None)
    listed = ["field-service", "aa", "field"]
    assert check_domains.order(root, listed) == ["field-service", "aa", "field"]


ZZ_GATE = GATE.format(id="zz-gate", kind="check", owner="false", extra='step = "lint"\n')


def test_ac2_with_no_work_type_default_alone_then_the_packs(tmp_path):
    """REQ-081 AC2: brief #1936 answer 6 (`[delivery] work_type` absent: `default`, then packs)."""
    root = project(tmp_path, {"zz-shop": pack("zz-shop", body=ZZ_GATE)}, ["zz-shop"])
    base = root / "config" / "playbooks" / "default.toml"
    ids = [g["id"] for g in check_playbooks.composed(base, root)[0]]
    assert ids[-1] == "zz-gate" and "tests-first" in ids
    assert check_playbooks.composed(base, root)[2] == []


def test_ac2_a_derived_work_type_then_the_packs(tmp_path):
    """REQ-081 AC2: brief #1936 answer 6 (a derived work type: its playbook, then the packs)."""
    root = project(tmp_path, {"zz-shop": pack("zz-shop", body=ZZ_GATE)}, ["zz-shop"])
    (root / "docs" / "research").mkdir(parents=True)
    (root / "docs" / "research" / "zz-kiosk.md").write_text("# An invented record\n", "utf-8")
    derived = root / "config" / "playbooks" / "zz-kiosk.toml"
    own = GATE.format(id="zz-kiosk-gate", kind="judgement", owner="true", extra="")
    derived.write_text('format = 1\nwork_type = "zz-kiosk"\n' + own, encoding="utf-8")
    assert check_domains.playbook_format.is_derived("zz-kiosk", root)
    ids = [g["id"] for g in check_playbooks.composed(derived, root)[0]]
    assert ids.index("tests-first") < ids.index("zz-kiosk-gate") < ids.index("zz-gate")


def test_ac2_in_the_plugin_layout_the_projects_pack_is_read_first(tmp_path, monkeypatch):
    """REQ-081 AC2: brief #1936 answer 6 (`[kit] layout = "plugin"`: the project's pack by name,
    else the plugin's)."""
    root = project(tmp_path, {"zz-own": pack("zz-own", body=ZZ_GATE)}, None)
    shutil.rmtree(root / "config" / "playbooks")
    (root / "agk.toml").write_text(
        '[kit]\nlayout = "plugin"\n\n[domain]\npacks = ["zz-own", "payments"]\n', "utf-8"
    )
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(KIT_ROOT))
    assert check_domains.pack_path(root, "payments") == KIT_ROOT / "config/domains/payments.toml"
    plugin_web = KIT_ROOT / "config" / "playbooks" / "web-app.toml"
    ids = [g["id"] for g in check_playbooks.composed(plugin_web, root)[0]]
    assert ids.index("tests-first") < ids.index("card-data-scope") < ids.index("zz-gate")
    (root / "config/domains/payments.toml").write_text(pack("payments", body=ZZ_GATE), "utf-8")
    assert check_domains.pack_path(root, "payments") == root / "config/domains/payments.toml"
