"""Live intelligence: package registries (npm, PyPI) and OSV. Only used when
FENRIX_LIVE_FEEDS=true; every function returns None/[] on failure so the
offline knowledge base always remains the safety net."""
from __future__ import annotations

import logging

import httpx

from fenrix.config import get_settings

log = logging.getLogger("fenrix.feeds")
OSV_ECOSYSTEMS = {"npm": "npm", "pypi": "PyPI", "maven": "Maven", "go": "Go", "deb": "Debian"}


def _client() -> httpx.Client:
    return httpx.Client(timeout=get_settings().http_timeout_seconds, follow_redirects=True)


def registry_lookup(ecosystem: str, name: str) -> dict | None:
    if not get_settings().live_feeds:
        return None
    try:
        with _client() as c:
            if ecosystem == "npm":
                r = c.get(f"https://registry.npmjs.org/{name}")
                if r.status_code != 200:
                    return None
                d = r.json()
                latest = d.get("dist-tags", {}).get("latest", "")
                meta = d.get("versions", {}).get(latest, {})
                lic = meta.get("license") or d.get("license") or "UNKNOWN"
                if isinstance(lic, dict):
                    lic = lic.get("type", "UNKNOWN")
                return {"ecosystem": "npm", "name": name, "license": str(lic), "latest": latest,
                        "description": d.get("description", ""), "last_release": (d.get("time", {}).get(latest, "") or "")[:10],
                        "maintainers": len(d.get("maintainers", [])), "deprecated": meta.get("deprecated")}
            if ecosystem == "pypi":
                r = c.get(f"https://pypi.org/pypi/{name}/json")
                if r.status_code != 200:
                    return None
                info = r.json().get("info", {})
                latest = info.get("version", "")
                files = r.json().get("releases", {}).get(latest, [])
                lic = info.get("license_expression") or info.get("license") or ""
                if not lic or len(lic) > 60:
                    classifiers = [c.split("::")[-1].strip() for c in info.get("classifiers", []) if c.startswith("License ::")]
                    lic = classifiers[0] if classifiers else "UNKNOWN"
                return {"ecosystem": "pypi", "name": name, "license": lic, "latest": latest,
                        "description": info.get("summary", ""),
                        "last_release": (files[0].get("upload_time", "") if files else "")[:10],
                        "maintainers": 1, "deprecated": None}
    except Exception as exc:
        log.info("registry lookup failed for %s:%s — %s", ecosystem, name, exc)
    return None


def osv_query(ecosystem: str, name: str, version: str) -> list[dict]:
    if not get_settings().live_feeds or ecosystem not in OSV_ECOSYSTEMS:
        return []
    try:
        with _client() as c:
            r = c.post("https://api.osv.dev/v1/query", json={
                "version": version, "package": {"name": name, "ecosystem": OSV_ECOSYSTEMS[ecosystem]}})
            r.raise_for_status()
            out = []
            for v in r.json().get("vulns", [])[:20]:
                cve = next((a for a in v.get("aliases", []) if a.startswith("CVE-")), v.get("id"))
                out.append({"id": cve, "title": v.get("summary") or v.get("details", "")[:140],
                            "kind": "malicious" if v.get("id", "").startswith("MAL-") else "vulnerability",
                            "cvss": None, "source": "OSV (live)"})
            return out
    except Exception as exc:
        log.info("OSV query failed for %s:%s — %s", ecosystem, name, exc)
        return []
