"""Curated library catalog used by the Fenrix agent when it runs offline.

Every library and alternative here is a real, published package. Versions and
release dates are an offline snapshot; with FENRIX_LIVE_FEEDS=true the agent
refreshes license, version and release data from the package registries.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Library:
    ecosystem: str          # npm | pypi | maven | go | deb
    name: str
    license: str
    purpose: str            # functional category used to find alternatives
    description: str
    latest: str
    last_release: str       # ISO date of the latest release in the snapshot
    maintainers: int = 3
    popularity: str = "high"    # high | medium | low
    deprecated: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)
    # Earlier licenses, newest first: ((first_version_with_current_license, previous_license), ...)
    license_before: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    @property
    def key(self) -> str:
        return f"{self.ecosystem}:{self.name}"


_L = Library
LIBRARIES: list[Library] = [
    # ---------------- npm ----------------
    _L("npm", "moment", "MIT", "date-time", "Parse, validate and format dates", "2.30.1", "2023-12-27", 4,
       deprecated="In maintenance mode since 2020; the authors recommend modern alternatives."),
    _L("npm", "dayjs", "MIT", "date-time", "2KB immutable date library with a Moment-compatible API", "1.11.13", "2024-08-20", 2),
    _L("npm", "date-fns", "MIT", "date-time", "Modular, tree-shakeable date utility functions", "4.1.0", "2024-09-17", 4),
    _L("npm", "luxon", "MIT", "date-time", "Immutable dates with first-class time-zone support", "3.5.0", "2024-08-03", 3),
    _L("npm", "request", "Apache-2.0", "http-client", "Simplified HTTP client", "2.88.2", "2020-02-11", 2,
       deprecated="Deprecated by its maintainers in February 2020; no security fixes."),
    _L("npm", "axios", "MIT", "http-client", "Promise-based HTTP client for the browser and Node.js", "1.7.9", "2024-12-04", 5),
    _L("npm", "undici", "MIT", "http-client", "HTTP/1.1 client written for Node.js (powers native fetch)", "7.2.0", "2024-12-19", 6),
    _L("npm", "node-fetch", "MIT", "http-client", "The Fetch API for Node.js", "3.3.2", "2023-07-25", 4),
    _L("npm", "lodash", "MIT", "utility", "Utility functions for arrays, objects and strings", "4.17.21", "2021-02-20", 3),
    _L("npm", "left-pad", "WTFPL", "string-padding", "Pad a string on the left", "1.3.0", "2018-04-09", 1,
       deprecated="Deprecated; use the native String.prototype.padStart().",
       notes=("Its 2016 unpublishing broke thousands of builds — a classic single-maintainer risk.",)),
    _L("npm", "ua-parser-js", "AGPL-3.0", "user-agent", "Detect browser, engine, OS and device from a user-agent string",
       "2.0.0", "2024-11-18", 1, license_before=(("2.0.0", "MIT"),),
       notes=("Version 2.0 changed the license from MIT to AGPL-3.0; 1.x remains MIT.",
              "Versions 0.7.29, 0.8.0 and 1.0.0 were hijacked in October 2021 to install a cryptominer and password stealer.")),
    _L("npm", "bowser", "MIT", "user-agent", "Small browser and platform detector", "2.11.0", "2020-08-13", 1, popularity="high"),
    _L("npm", "detect-browser", "MIT", "user-agent", "Detect the browser from the user-agent string", "5.3.0", "2022-01-21", 1, popularity="medium"),
    _L("npm", "highcharts", "Commercial", "charts", "Interactive charting library (free only for non-commercial use)",
       "12.1.2", "2024-12-20", 10, notes=("Commercial use requires a paid Highsoft licence.",)),
    _L("npm", "chart.js", "MIT", "charts", "Simple HTML5 canvas charts", "4.4.7", "2024-12-01", 6),
    _L("npm", "echarts", "Apache-2.0", "charts", "Apache ECharts — powerful interactive charts", "5.6.0", "2024-12-28", 8),
    _L("npm", "event-stream", "MIT", "streams", "Construct pipes of streams of events", "4.0.1", "2018-09-14", 1,
       notes=("Version 3.3.6 pulled in the malicious flatmap-stream package that targeted Copay bitcoin wallets (2018).",)),
    _L("npm", "through2", "MIT", "streams", "Tiny wrapper around Node.js Transform streams", "4.0.2", "2020-06-10", 2),
    _L("npm", "minimist", "MIT", "cli-args", "Parse command-line arguments", "1.2.8", "2023-02-09", 2),
    _L("npm", "yargs", "MIT", "cli-args", "Build interactive command-line tools", "17.7.2", "2023-04-27", 4),
    _L("npm", "commander", "MIT", "cli-args", "Complete solution for Node.js command-line programs", "13.0.0", "2024-12-31", 3),
    _L("npm", "colors", "MIT", "terminal-colors", "Colors in the Node.js console", "1.4.0", "2019-09-21", 1,
       notes=("The maintainer published sabotaged versions (1.4.1+) that printed garbage in an infinite loop (January 2022).",)),
    _L("npm", "chalk", "MIT", "terminal-colors", "Terminal string styling", "5.4.1", "2024-12-21", 2),
    _L("npm", "picocolors", "ISC", "terminal-colors", "The tiniest and fastest terminal colouring library", "1.1.1", "2024-10-16", 1),
    _L("npm", "faker", "MIT", "fake-data", "Generate fake data", "6.6.6", "2022-01-04", 1,
       deprecated="The maintainer wiped the code in version 6.6.6 (January 2022).",
       notes=("The community fork @faker-js/faker is the maintained successor.",)),
    _L("npm", "@faker-js/faker", "MIT", "fake-data", "Generate massive amounts of fake contextual data", "9.3.0", "2024-12-04", 6),
    _L("npm", "node-ipc", "MIT", "ipc", "Inter-process communication for Node.js", "12.0.0", "2023-04-04", 1,
       notes=("Versions 10.1.1–10.1.2 contained protestware that overwrote files on machines in specific countries (CVE-2022-23812).",)),
    _L("npm", "express", "MIT", "web-framework", "Fast, minimalist web framework for Node.js", "5.1.0", "2025-03-31", 6),
    _L("npm", "react", "MIT", "ui", "Library for building user interfaces", "19.0.0", "2024-12-05", 10),
    _L("npm", "react-dom", "MIT", "ui", "React renderer for the browser DOM", "19.0.0", "2024-12-05", 10),
    _L("npm", "next", "MIT", "web-framework", "The React framework by Vercel", "15.5.27", "2026-06-01", 12),
    _L("npm", "lucide-react", "ISC", "icons", "Open-source icon set for React", "0.468.0", "2024-12-04", 4),
    _L("npm", "typescript", "Apache-2.0", "language", "Typed superset of JavaScript", "5.7.2", "2024-11-22", 8),
    _L("npm", "@types/node", "MIT", "types", "Type definitions for Node.js (DefinitelyTyped)", "22.10.2", "2024-12-12", 10),
    _L("npm", "@types/react", "MIT", "types", "Type definitions for React (DefinitelyTyped)", "19.0.2", "2024-12-18", 10),
    _L("npm", "@types/react-dom", "MIT", "types", "Type definitions for React DOM (DefinitelyTyped)", "19.0.2", "2024-12-18", 10),
    _L("npm", "@fontsource-variable/archivo", "OFL-1.1", "fonts", "Self-hosted Archivo variable font", "5.3.0", "2025-01-01", 3),
    _L("npm", "@fontsource-variable/jetbrains-mono", "OFL-1.1", "fonts", "Self-hosted JetBrains Mono variable font", "5.3.0", "2025-01-01", 3),
    _L("npm", "jsonwebtoken", "MIT", "auth", "JSON Web Token implementation for Node.js", "9.0.2", "2023-08-30", 3),

    # ---------------- PyPI ----------------
    _L("pypi", "requests", "Apache-2.0", "http-client", "HTTP for Humans", "2.32.3", "2024-05-29", 4),
    _L("pypi", "httpx", "BSD-3-Clause", "http-client", "Next-generation HTTP client with sync and async APIs", "0.28.1", "2024-12-06", 3),
    _L("pypi", "urllib3", "MIT", "http-client", "HTTP library with thread-safe connection pooling", "2.3.0", "2024-12-22", 4),
    _L("pypi", "pyyaml", "MIT", "yaml", "YAML parser and emitter for Python", "6.0.2", "2024-08-06", 3),
    _L("pypi", "ruamel.yaml", "MIT", "yaml", "YAML 1.2 loader/dumper that preserves comments", "0.18.6", "2024-02-07", 1),
    _L("pypi", "pillow", "HPND", "imaging", "Python Imaging Library (fork)", "11.1.0", "2025-01-02", 5),
    _L("pypi", "mysqlclient", "GPL-2.0", "mysql-driver", "MySQL database connector (C extension)", "2.2.7", "2025-01-10", 1),
    _L("pypi", "pymysql", "MIT", "mysql-driver", "Pure-Python MySQL client", "1.1.1", "2024-05-21", 2),
    _L("pypi", "pyqt5", "GPL-3.0", "desktop-gui", "Python bindings for Qt 5 (GPL or paid commercial licence)", "5.15.11", "2024-07-19", 1,
       notes=("Riverbank sells a commercial licence; without it PyQt5 is GPL-3.0.",)),
    _L("pypi", "pyside6", "LGPL-3.0", "desktop-gui", "Official Qt for Python bindings", "6.8.1", "2024-12-04", 8),
    _L("pypi", "pymupdf", "AGPL-3.0", "pdf", "High-performance PDF rendering and extraction",
       "1.25.1", "2024-12-12", 3, notes=("Artifex sells a commercial licence; otherwise AGPL-3.0.",)),
    _L("pypi", "pypdf", "BSD-3-Clause", "pdf", "Pure-Python PDF library: split, merge, extract text", "5.1.0", "2024-10-27", 3),
    _L("pypi", "pdfplumber", "MIT", "pdf", "Extract text and tables from PDFs", "0.11.5", "2025-01-01", 2),
    _L("pypi", "ctx", "UNKNOWN", "utility", "Dictionary helper", "0.2.6", "2022-05-21", 1,
       notes=("Hijacked in May 2022: new versions stole AWS credentials from environment variables.",)),
    _L("pypi", "django", "BSD-3-Clause", "web-framework", "High-level Python web framework", "5.1.4", "2024-12-04", 12),
    _L("pypi", "flask", "BSD-3-Clause", "web-framework", "Lightweight WSGI web framework", "3.1.0", "2024-11-13", 6),
    _L("pypi", "pandas", "BSD-3-Clause", "data", "Data analysis and manipulation", "2.2.3", "2024-09-20", 15),
    _L("pypi", "numpy", "BSD-3-Clause", "data", "Fundamental package for array computing", "2.2.1", "2024-12-21", 15),

    # ---------------- Maven ----------------
    _L("maven", "org.apache.logging.log4j:log4j-core", "Apache-2.0", "logging", "Apache Log4j 2 implementation",
       "2.24.3", "2024-12-13", 8, notes=("Log4Shell (CVE-2021-44228) affected 2.0-beta9 through 2.14.1.",)),
    _L("maven", "ch.qos.logback:logback-classic", "EPL-1.0 OR LGPL-2.1", "logging", "Logback logging implementation for SLF4J", "1.5.16", "2024-12-23", 2),
    _L("maven", "org.springframework:spring-beans", "Apache-2.0", "framework", "Spring Framework beans and dependency injection", "6.2.1", "2024-12-12", 10),
    _L("maven", "org.springframework.boot:spring-boot-starter-web", "Apache-2.0", "framework", "Spring Boot web starter", "3.4.1", "2024-12-19", 10),
    _L("maven", "com.fasterxml.jackson.core:jackson-databind", "Apache-2.0", "json", "General data-binding for Jackson", "2.18.2", "2024-11-28", 3),
    _L("maven", "com.google.code.gson:gson", "Apache-2.0", "json", "Google's Java JSON library", "2.11.0", "2024-05-19", 4),
    _L("maven", "org.apache.commons:commons-text", "Apache-2.0", "text", "Apache Commons Text string algorithms", "1.13.0", "2024-12-07", 6),
    _L("maven", "org.yaml:snakeyaml", "Apache-2.0", "yaml", "YAML 1.1 parser and emitter for Java", "2.3", "2024-08-30", 2),
    _L("maven", "com.itextpdf:itextpdf", "AGPL-3.0", "pdf", "iText 5 PDF library (AGPL or paid commercial licence)", "5.5.13.4", "2024-07-24", 4,
       notes=("End-of-life; iText Group sells commercial licences.",)),
    _L("maven", "org.apache.pdfbox:pdfbox", "Apache-2.0", "pdf", "Apache PDFBox — create and manipulate PDF documents", "3.0.4", "2025-01-14", 6),
    _L("maven", "com.github.librepdf:openpdf", "LGPL-2.1 OR MPL-2.0", "pdf", "Open-source fork of iText 4 under LGPL/MPL", "2.0.3", "2024-08-12", 3),
    _L("maven", "mysql:mysql-connector-java", "GPL-2.0", "mysql-driver", "MySQL JDBC driver (GPL-2.0 with Universal FOSS Exception)", "8.0.33", "2023-04-18", 3,
       deprecated="Relocated to com.mysql:mysql-connector-j."),
    _L("maven", "org.mariadb.jdbc:mariadb-java-client", "LGPL-2.1", "mysql-driver", "MariaDB/MySQL JDBC driver", "3.5.1", "2024-11-25", 3),
    _L("maven", "org.postgresql:postgresql", "BSD-2-Clause", "postgres-driver", "PostgreSQL JDBC driver", "42.7.4", "2024-08-22", 6),

    # ---------------- Go / OS packages ----------------
    _L("go", "github.com/gin-gonic/gin", "MIT", "web-framework", "HTTP web framework for Go", "1.10.0", "2024-05-07", 6),
    _L("go", "golang.org/x/crypto", "BSD-3-Clause", "crypto", "Supplementary Go cryptography libraries", "0.31.0", "2024-12-11", 10),
    _L("go", "github.com/golang-jwt/jwt/v5", "MIT", "auth", "JSON Web Tokens for Go", "5.2.1", "2024-04-02", 3),
    _L("go", "github.com/hashicorp/terraform", "BUSL-1.1", "infrastructure", "Infrastructure as code",
       "1.10.3", "2024-12-18", 20, license_before=(("1.6.0", "MPL-2.0"),), notes=("Changed from MPL-2.0 to BUSL-1.1 in version 1.6 (August 2023).",)),
    _L("go", "github.com/opentofu/opentofu", "MPL-2.0", "infrastructure", "Open-source Terraform fork under the Linux Foundation", "1.9.0", "2025-01-09", 15),
    _L("deb", "xz-utils", "0BSD", "compression", "XZ-format compression utilities and liblzma", "5.6.4", "2025-01-23", 2,
       notes=("Versions 5.6.0 and 5.6.1 shipped a backdoor targeting OpenSSH (CVE-2024-3094).",)),
]

CATALOG: dict[str, Library] = {lib.key: lib for lib in LIBRARIES}
_BY_NAME: dict[str, list[Library]] = {}
for _lib in LIBRARIES:
    _BY_NAME.setdefault(_lib.name.lower(), []).append(_lib)
    if ":" in _lib.name:  # maven: allow lookup by artifactId alone
        _BY_NAME.setdefault(_lib.name.split(":")[-1].lower(), []).append(_lib)

PURPOSE_LABELS = {
    "date-time": "Date & time", "http-client": "HTTP client", "utility": "Utilities", "string-padding": "String padding",
    "user-agent": "User-agent parsing", "charts": "Charts", "streams": "Streams", "cli-args": "CLI arguments",
    "terminal-colors": "Terminal colours", "fake-data": "Fake data", "ipc": "Inter-process communication",
    "web-framework": "Web framework", "ui": "UI", "auth": "Authentication", "yaml": "YAML", "imaging": "Imaging",
    "mysql-driver": "MySQL driver", "desktop-gui": "Desktop GUI", "pdf": "PDF", "data": "Data", "logging": "Logging",
    "framework": "Framework", "json": "JSON", "text": "Text", "postgres-driver": "PostgreSQL driver",
    "infrastructure": "Infrastructure", "compression": "Compression", "crypto": "Cryptography",
    "icons": "Icons", "language": "Language tooling", "types": "Type definitions", "fonts": "Fonts",
}


def find(name: str, ecosystem: str | None = None) -> Library | None:
    name = name.strip()
    if ":" in name and name.split(":", 1)[0] in {"npm", "pypi", "maven", "go", "deb"}:
        ecosystem, name = name.split(":", 1)
    if ecosystem and f"{ecosystem}:{name}" in CATALOG:
        return CATALOG[f"{ecosystem}:{name}"]
    matches = _BY_NAME.get(name.lower(), [])
    if ecosystem:
        matches = [m for m in matches if m.ecosystem == ecosystem]
    return matches[0] if matches else None


def license_at(key: str, version: str | None, default: str = "UNKNOWN") -> str:
    """License that applied to a specific version (projects sometimes relicense)."""
    from fenrix.engines.versions import compare

    lib = CATALOG.get(key)
    if lib is None:
        return default
    if version:
        for since, previous in lib.license_before:
            if compare(version, since) < 0:
                return previous
    return lib.license


def same_purpose(lib: Library) -> list[Library]:
    return [o for o in LIBRARIES if o.purpose == lib.purpose and o.ecosystem == lib.ecosystem and o.key != lib.key]


def search(query: str, limit: int = 8) -> list[Library]:
    q = query.lower().strip()
    if not q:
        return []
    scored = []
    for lib in LIBRARIES:
        name = lib.name.lower()
        if name == q or name.endswith(":" + q):
            score = 0
        elif name.startswith(q) or (":" in name and name.split(":")[-1].startswith(q)):
            score = 1
        elif q in name:
            score = 2
        elif q in lib.description.lower() or q in PURPOSE_LABELS.get(lib.purpose, "").lower():
            score = 3
        else:
            continue
        scored.append((score, lib.name, lib))
    return [lib for _, _, lib in sorted(scored)[:limit]]
