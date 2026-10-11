"""Read dependency lists from the files developers actually have."""
from __future__ import annotations

import json
import re

from defusedxml import ElementTree

SUPPORTED = ["package.json", "package-lock.json", "requirements.txt", "pyproject.toml", "pom.xml", "go.mod",
             "CycloneDX JSON", "SPDX JSON"]


def _clean_npm_version(spec: str) -> str | None:
    m = re.search(r"\d+(\.\d+){0,3}([-.][0-9A-Za-z.]+)?", spec or "")
    return m.group(0) if m else None


def parse(filename: str, text: str) -> list[dict]:
    name = filename.lower().rsplit("/", 1)[-1]
    if name.endswith(".json"):
        data = json.loads(text)
        if data.get("bomFormat") == "CycloneDX":
            return _cyclonedx(data)
        if "spdxVersion" in data:
            return _spdx(data)
        if "lockfileVersion" in data:
            return _package_lock(data)
        if "dependencies" in data or "devDependencies" in data:
            return _package_json(data)
        raise ValueError("JSON file is not a package.json, package-lock.json, CycloneDX or SPDX document")
    if name.endswith("pom.xml") or name.endswith(".xml"):
        return _pom(text)
    if name.endswith("go.mod"):
        return _go_mod(text)
    if name.endswith(".toml"):
        return _pyproject(text)
    if name.endswith(".txt") or "requirements" in name:
        return _requirements(text)
    raise ValueError(f"Unsupported file '{filename}'. Supported: {', '.join(SUPPORTED)}")


def _package_json(data: dict) -> list[dict]:
    out = []
    for section, dev in (("dependencies", False), ("devDependencies", True)):
        for pkg, spec in (data.get(section) or {}).items():
            out.append({"ecosystem": "npm", "name": pkg, "version": _clean_npm_version(str(spec)), "dev": dev})
    return out


def _package_lock(data: dict) -> list[dict]:
    out = []
    for location, meta in (data.get("packages") or {}).items():
        if not location:
            continue
        pkg = location.split("node_modules/")[-1]
        out.append({"ecosystem": "npm", "name": pkg, "version": meta.get("version"),
                    "license": meta.get("license") if isinstance(meta.get("license"), str) else None,
                    "direct": location.count("node_modules/") == 1})
    return out


def _requirements(text: str) -> list[dict]:
    out = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith(("-", "git+", "http")):
            continue
        m = re.match(r"([A-Za-z0-9_.\-]+)(\[[^\]]*\])?\s*(==|>=|~=|<=|>|<)?\s*([0-9][^\s;,]*)?", line)
        if m:
            out.append({"ecosystem": "pypi", "name": m.group(1).lower(), "version": m.group(4)})
    return out


def _pyproject(text: str) -> list[dict]:
    import tomllib

    data = tomllib.loads(text)
    deps = data.get("project", {}).get("dependencies", [])
    if not deps:
        deps = [f"{k}=={v}" if isinstance(v, str) else k
                for k, v in data.get("tool", {}).get("poetry", {}).get("dependencies", {}).items() if k != "python"]
    return _requirements("\n".join(deps))


def _pom(text: str) -> list[dict]:
    root = ElementTree.fromstring(text)
    ns = root.tag.split("}")[0] + "}" if root.tag.startswith("{") else ""
    props = {}
    p = root.find(f"{ns}properties")
    if p is not None:
        props = {child.tag.replace(ns, ""): (child.text or "").strip() for child in p}
    out = []
    for dep in root.iter(f"{ns}dependency"):
        group = (dep.findtext(f"{ns}groupId") or "").strip()
        artifact = (dep.findtext(f"{ns}artifactId") or "").strip()
        version = (dep.findtext(f"{ns}version") or "").strip()
        m = re.fullmatch(r"\$\{(.+)\}", version)
        if m:
            version = props.get(m.group(1), "")
        if group and artifact:
            out.append({"ecosystem": "maven", "name": f"{group}:{artifact}", "version": version or None})
    return out


def _go_mod(text: str) -> list[dict]:
    out = []
    for line in text.splitlines():
        line = line.split("//", 1)[0].strip()
        if line.startswith("require "):
            line = line[len("require "):].strip()
        parts = line.split()
        if len(parts) >= 2 and parts[1].startswith("v") and "." in parts[0]:
            out.append({"ecosystem": "go", "name": parts[0], "version": parts[1].lstrip("v")})
    return out


def _cyclonedx(data: dict) -> list[dict]:
    out = []
    for c in data.get("components", []):
        purl = c.get("purl", "")
        eco = purl[4:].split("/", 1)[0] if purl.startswith("pkg:") else None
        eco = {"pypi": "pypi", "npm": "npm", "maven": "maven", "golang": "go", "deb": "deb"}.get(eco or "", eco)
        name = f"{c['group']}:{c['name']}" if eco == "maven" and c.get("group") else c.get("name")
        lic = None
        for entry in c.get("licenses", []):
            lic = (entry.get("license") or {}).get("id") or (entry.get("license") or {}).get("name") or entry.get("expression")
            if lic:
                break
        out.append({"ecosystem": eco, "name": name, "version": c.get("version"), "license": lic})
    return out


def _spdx(data: dict) -> list[dict]:
    out = []
    for p in data.get("packages", []):
        eco = None
        for ref in p.get("externalRefs", []):
            loc = ref.get("referenceLocator", "")
            if loc.startswith("pkg:"):
                eco = {"golang": "go"}.get(loc[4:].split("/", 1)[0], loc[4:].split("/", 1)[0])
        lic = p.get("licenseConcluded")
        out.append({"ecosystem": eco, "name": p.get("name"), "version": p.get("versionInfo"),
                    "license": None if lic in (None, "NOASSERTION") else lic})
    return out
