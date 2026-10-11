def test_health_is_public(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_requires_login(client):
    assert client.get("/api/overview").status_code == 401


def test_wrong_password_rejected(client):
    r = client.post("/api/auth/login", json={"email": "analyst@fenrix.dev", "password": "nope"})
    assert r.status_code == 401


def test_overview(client, auth):
    data = client.get("/api/overview", headers=auth).json()
    assert data["kpis"]["applications"] == 50
    assert data["kpis"]["open_incidents"] >= 2
    assert len(data["trend"]) == 30
    assert data["kpis"]["license_blocks"] > 0


def test_applications_and_detail(client, auth):
    apps = client.get("/api/applications", headers=auth).json()
    assert len(apps) == 50
    detail = client.get("/api/applications/payment-gateway", headers=auth).json()
    assert detail["criticality"] == 5
    assert any(d["name"].endswith("log4j-core") and d["vulnerabilities"] for d in detail["dependencies"])


def test_library_detail(client, auth):
    data = client.get("/api/libraries/detail", params={"id": "maven:org.apache.logging.log4j:log4j-core"}, headers=auth).json()
    assert len(data["usages"]) >= 10
    assert data["advisories"][0]["id"] == "CVE-2021-44228"


def test_log4shell_demo_ranks_payment_apps_first(client, auth):
    inc_id = client.post("/api/demo/log4shell", headers=auth).json()["id"]
    inc = client.get(f"/api/incidents/{inc_id}", headers=auth).json()
    top = [i["app"]["id"] for i in inc["items"][:2]]
    assert set(top) == {"payment-gateway", "upi-switch"}
    assert inc["items"][-1]["priority"] in {"P3", "P4"}
    assert inc["safe_usages"], "patched apps should be listed as safe"

    item = inc["items"][0]
    r = client.patch(f"/api/incidents/{inc_id}/items/{item['id']}", json={"status": "fixed"}, headers=auth)
    assert r.status_code == 200
    after = client.get(f"/api/incidents/{inc_id}", headers=auth).json()
    assert after["fixed_items"] == 1

    csv_text = client.get(f"/api/incidents/{inc_id}/export.csv", headers=auth).text
    assert csv_text.splitlines()[0].startswith("rank,priority,score")


def test_agent_check_uses_application_context(client, auth):
    r = client.post("/api/agent/check", json={"name": "pymupdf", "ecosystem": "pypi", "app_id": "report-studio"}, headers=auth)
    body = r.json()
    assert body["decision"] == "block"
    assert body["context"]["usage"] == "saas"
    history = client.get("/api/agent/history", headers=auth).json()
    assert history[0]["query"] == "pymupdf"


def test_agent_scan_manifest(client, auth):
    r = client.post("/api/agent/scan", headers=auth, json={
        "filename": "requirements.txt", "content": "pymupdf==1.24.10\nrequests==2.32.3", "usage": "saas"})
    assert r.status_code == 200
    assert r.json()["passed"] is False


def test_custom_incident(client, auth):
    r = client.post("/api/incidents", headers=auth, json={"custom": {
        "component_id": "npm:lodash", "title": "Hypothetical lodash compromise", "kind": "malicious",
        "versions": ["4.17.15", "4.17.20"]}})
    assert r.status_code == 201
    inc = client.get(f"/api/incidents/{r.json()['id']}", headers=auth).json()
    assert inc["affected_apps"] > 0
