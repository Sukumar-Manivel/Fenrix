"""Offline snapshot of real, well-known supply-chain advisories.

CVSS scores are NVD base scores. EPSS values are approximate snapshots — in live
mode Fenrix pulls current EPSS and CISA KEV data. Malicious-package events with
no CVE use Fenrix internal IDs (FNX-*) rather than invented CVE numbers.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Advisory:
    id: str
    component: str                      # catalog key, e.g. "maven:org.apache.logging.log4j:log4j-core"
    kind: str                           # vulnerability | malicious | sabotage
    title: str
    summary: str
    cvss: float
    epss: float
    kev: bool
    published: str
    affected: tuple[tuple[str | None, str | None], ...] = ()   # (introduced, fixed) half-open ranges
    versions: tuple[str, ...] = ()                            # explicitly affected versions
    fixed_version: str | None = None                          # recommended safe version
    aliases: tuple[str, ...] = field(default_factory=tuple)
    nickname: str | None = None


ADVISORIES: list[Advisory] = [
    Advisory("CVE-2021-44228", "maven:org.apache.logging.log4j:log4j-core", "vulnerability",
             "Log4Shell: remote code execution through JNDI lookups",
             "Attacker-controlled text that reaches a log message can make Log4j load and run code from a remote LDAP server.",
             10.0, 0.944, True, "2021-12-10", affected=(("2.0-beta9", "2.15.0"),), fixed_version="2.17.1",
             nickname="Log4Shell"),
    Advisory("CVE-2022-22965", "maven:org.springframework:spring-beans", "vulnerability",
             "Spring4Shell: remote code execution via data binding",
             "On JDK 9+ with WAR deployment, crafted request parameters can write a web shell through class-loader manipulation.",
             9.8, 0.943, True, "2022-03-31", affected=(("5.3.0", "5.3.18"), ("5.2.0", "5.2.20")), fixed_version="5.3.18",
             nickname="Spring4Shell"),
    Advisory("CVE-2022-42889", "maven:org.apache.commons:commons-text", "vulnerability",
             "Text4Shell: code execution through string interpolation",
             "Default interpolators in StringSubstitutor evaluate script, DNS and URL lookups on untrusted input.",
             9.8, 0.84, False, "2022-10-13", affected=(("1.5", "1.10.0"),), fixed_version="1.10.0", nickname="Text4Shell"),
    Advisory("CVE-2020-36518", "maven:com.fasterxml.jackson.core:jackson-databind", "vulnerability",
             "Denial of service through deeply nested JSON",
             "Deeply nested arrays exhaust the stack during deserialization.",
             7.5, 0.006, False, "2022-03-11", affected=((None, "2.12.6.1"), ("2.13.0", "2.13.2.1")), fixed_version="2.13.2.1"),
    Advisory("CVE-2022-1471", "maven:org.yaml:snakeyaml", "vulnerability",
             "Unsafe deserialization in SnakeYAML Constructor",
             "Loading untrusted YAML with the default Constructor can instantiate arbitrary Java types and run code.",
             9.8, 0.52, False, "2022-12-01", affected=((None, "2.0"),), fixed_version="2.2"),
    Advisory("CVE-2021-23337", "npm:lodash", "vulnerability",
             "Command injection in lodash template",
             "The template function lets attackers who control template options inject code.",
             7.2, 0.012, False, "2021-02-15", affected=((None, "4.17.21"),), fixed_version="4.17.21"),
    Advisory("CVE-2021-44906", "npm:minimist", "vulnerability",
             "Prototype pollution in minimist",
             "Crafted arguments can pollute Object.prototype, leading to logic bypass or code execution.",
             9.8, 0.009, False, "2022-03-17", affected=((None, "1.2.6"),), fixed_version="1.2.8"),
    Advisory("CVE-2023-45857", "npm:axios", "vulnerability",
             "Axios leaks the XSRF-TOKEN to third-party hosts",
             "The XSRF-TOKEN cookie is sent in a header on every request, including cross-origin requests.",
             6.5, 0.004, False, "2023-11-08", affected=(("0.8.1", "1.6.0"),), fixed_version="1.7.9"),
    Advisory("CVE-2020-14343", "pypi:pyyaml", "vulnerability",
             "Arbitrary code execution in PyYAML full_load",
             "full_load and FullLoader can still construct arbitrary Python objects from untrusted YAML.",
             9.8, 0.08, False, "2021-02-09", affected=((None, "5.4"),), fixed_version="6.0.2"),
    Advisory("CVE-2023-32681", "pypi:requests", "vulnerability",
             "Proxy-Authorization header leaked on redirect",
             "Requests forwards proxy credentials to destination servers when following HTTPS redirects.",
             6.1, 0.06, False, "2023-05-26", affected=(("2.3.0", "2.31.0"),), fixed_version="2.32.3"),
    Advisory("CVE-2023-50447", "pypi:pillow", "vulnerability",
             "Code execution through PIL.ImageMath.eval",
             "The environment argument of ImageMath.eval allows arbitrary code execution.",
             8.1, 0.01, False, "2024-01-19", affected=((None, "10.2.0"),), fixed_version="11.1.0"),
    Advisory("CVE-2023-43804", "pypi:urllib3", "vulnerability",
             "Cookie header leaked on cross-origin redirect",
             "urllib3 did not strip the Cookie header when following a redirect to a different origin.",
             8.1, 0.003, False, "2023-10-04", affected=((None, "1.26.17"), ("2.0.0", "2.0.6")), fixed_version="2.3.0"),
    Advisory("CVE-2024-3094", "deb:xz-utils", "malicious",
             "Backdoor in xz / liblzma",
             "A maintainer account inserted obfuscated code into release tarballs that hijacks OpenSSH authentication via systemd.",
             10.0, 0.86, False, "2024-03-29", versions=("5.6.0", "5.6.1"), fixed_version="5.6.4",
             nickname="xz backdoor"),
    Advisory("CVE-2022-23812", "npm:node-ipc", "sabotage",
             "node-ipc protestware overwrites files",
             "Code added by the maintainer overwrote files with a heart emoji on hosts with Russian or Belarusian IP addresses.",
             9.8, 0.02, False, "2022-03-16", versions=("10.1.1", "10.1.2"), fixed_version="9.2.2"),
    Advisory("GHSA-pjwm-rvh2-c87w", "npm:ua-parser-js", "malicious",
             "Hijacked ua-parser-js releases install malware",
             "A compromised npm account published versions that dropped a cryptominer and credential-stealing trojan.",
             9.8, 0.0, False, "2021-10-22", versions=("0.7.29", "0.8.0", "1.0.0"), fixed_version="1.0.39",
             nickname="ua-parser-js hijack"),
    Advisory("FNX-2018-0001", "npm:event-stream", "malicious",
             "event-stream pulls in malicious flatmap-stream",
             "A new maintainer added flatmap-stream, which stole wallet keys from the Copay bitcoin app.",
             9.8, 0.0, False, "2018-11-26", versions=("3.3.6",), fixed_version="4.0.1", nickname="event-stream"),
    Advisory("FNX-2022-0002", "npm:colors", "sabotage",
             "colors.js sabotaged by its maintainer",
             "Versions after 1.4.0 enter an infinite loop printing garbage text, causing denial of service.",
             7.5, 0.0, False, "2022-01-08", affected=(("1.4.1", None),), fixed_version="1.4.0"),
    Advisory("FNX-2022-0003", "pypi:ctx", "malicious",
             "Hijacked ctx package steals AWS credentials",
             "After the maintainer's expired domain was re-registered, new versions exfiltrated environment variables.",
             9.8, 0.0, False, "2022-05-24", versions=("0.1.2", "0.2.2", "0.2.6"), fixed_version=None),
]

BY_ID: dict[str, Advisory] = {a.id: a for a in ADVISORIES}


def for_component(component_key: str) -> list[Advisory]:
    return [a for a in ADVISORIES if a.component == component_key]
