from types import SimpleNamespace

from fenrix.engines import parsers, triage, versions
from fenrix.engines.agent import check, scan_manifest
from fenrix.knowledge import licenses


def app(criticality=5, data_class="pci", exposure="internet"):
    return SimpleNamespace(criticality=criticality, data_class=data_class, exposure=exposure)


# ---------------------------------------------------------------- versions
def test_prerelease_sorts_before_release():
    assert versions.compare("2.0-beta9", "2.0") < 0
    assert versions.compare("1.2.6", "1.2.10") < 0
    assert versions.compare("1.0", "1.0.0") == 0


def test_log4shell_range():
    ranges = [("2.0-beta9", "2.15.0")]
    assert versions.is_affected("2.14.1", ranges, set())
    assert not versions.is_affected("2.17.1", ranges, set())
    assert not versions.is_affected("1.2.17", ranges, set())


# ---------------------------------------------------------------- licenses
def test_agpl_blocked_for_client_facing_service():
    assert licenses.evaluate("AGPL-3.0", "saas")["verdict"] == "block"


def test_gpl_fine_internally_but_not_when_shipped():
    assert licenses.evaluate("GPL-3.0", "internal")["verdict"] == "allow"
    assert licenses.evaluate("GPL-3.0", "distributed")["verdict"] == "block"


def test_dual_license_takes_most_permissive_option():
    assert licenses.normalize("(MIT OR GPL-3.0)").spdx == "MIT"


def test_missing_license_is_not_permission():
    assert licenses.evaluate(None, "saas")["verdict"] == "block"


# ---------------------------------------------------------------- triage
def test_payment_gateway_outranks_internal_tool():
    log4shell = triage.ThreatProfile("vulnerability", 10.0, 0.94, True)
    gateway, _ = triage.score_exposure(log4shell, app(), "reachable", True)
    todo, _ = triage.score_exposure(log4shell, app(1, "internal", "internal"), "unreachable", False)
    assert gateway == 100.0
    assert todo < 35
    assert triage.priority_for(gateway)[0] == "P1"
    assert triage.priority_for(todo)[0] == "P4"


def test_reachability_ignored_for_malicious_packages():
    backdoor = triage.ThreatProfile("malicious", 10.0, 0.0, False)
    a, _ = triage.score_exposure(backdoor, app(), "reachable", True)
    b, _ = triage.score_exposure(backdoor, app(), "unreachable", True)
    assert a == b


def test_factors_add_up_to_score():
    threat = triage.ThreatProfile("vulnerability", 7.5, 0.2, False)
    score, factors = triage.score_exposure(threat, app(3, "confidential", "partner"), "unknown", False)
    base = sum(f["points"] for f in factors if "points" in f)
    mult = 1.0
    for f in factors:
        mult *= f.get("multiplier", 1.0)
    assert abs(base * mult - score) < 0.11


def test_what_if_curve_is_cumulative():
    result = triage.what_if([90, 60, 30, 20])
    assert result["curve"][-1]["risk_removed_pct"] == 100.0
    assert result["highlights"][0] == {"fixed": 1, "risk_removed_pct": 45.0}


# ---------------------------------------------------------------- agent
def test_agent_blocks_agpl_pdf_library_and_suggests_pdfbox():
    r = check("itextpdf", "maven", usage="saas", use_llm=False)
    assert r["decision"] == "block"
    assert r["alternatives"][0]["name"] == "org.apache.pdfbox:pdfbox"
    assert r["remediation"]["type"] == "migrate"


def test_agent_blocks_known_malicious_release():
    r = check("ua-parser-js", "npm", "0.7.29", use_llm=False)
    assert r["decision"] == "block"
    assert "malicious" in r["headline"]


def test_agent_recommends_upgrade_for_fixable_vulnerability():
    r = check("log4j-core", "maven", "2.14.1", use_llm=False)
    assert r["decision"] == "block"
    assert r["remediation"]["type"] == "upgrade"
    assert "2.17.1" in r["remediation"]["after"]


def test_agent_says_honestly_when_no_library_fits():
    r = check("node-ipc", "npm", usage="internal", use_llm=False)
    assert r["no_fit"] is True
    assert r["remediation"]["type"] == "migrate"
    assert "node:net" in r["remediation"]["after"]


def test_agent_approves_safe_library():
    r = check("express", "npm", use_llm=False)
    assert r["decision"] == "approve"
    assert r["remediation"] is None


def test_unknown_package_needs_review():
    assert check("definitely-not-a-real-package", use_llm=False)["decision"] == "unknown"


# ---------------------------------------------------------------- parsers
def test_parse_package_json_and_scan():
    pkgs = parsers.parse("package.json", '{"dependencies": {"moment": "^2.29.4", "express": "4.21.2"}}')
    assert {p["name"] for p in pkgs} == {"moment", "express"}
    report = scan_manifest(pkgs, "saas")
    assert report["passed"] is True
    assert report["summary"]["conditions"] == 1


def test_parse_pom_resolves_properties():
    pom = """<project xmlns="http://maven.apache.org/POM/4.0.0"><properties><log4j.version>2.14.1</log4j.version></properties>
    <dependencies><dependency><groupId>org.apache.logging.log4j</groupId><artifactId>log4j-core</artifactId>
    <version>${log4j.version}</version></dependency></dependencies></project>"""
    [dep] = parsers.parse("pom.xml", pom)
    assert dep == {"ecosystem": "maven", "name": "org.apache.logging.log4j:log4j-core", "version": "2.14.1"}
    assert scan_manifest([dep])["passed"] is False


def test_parse_requirements():
    pkgs = parsers.parse("requirements.txt", "requests==2.25.1\n# comment\npyyaml>=6.0\nflask")
    assert [p["name"] for p in pkgs] == ["requests", "pyyaml", "flask"]
    assert pkgs[0]["version"] == "2.25.1"
