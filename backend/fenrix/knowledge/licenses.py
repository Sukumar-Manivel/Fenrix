"""License knowledge base and compatibility policy.

The policy answers one question deterministically: *given how an application is
used, can it legally depend on a library under license X?* No LLM is involved,
so every verdict is reproducible and explainable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Verdict = Literal["allow", "conditions", "block"]
UsageProfile = Literal["distributed", "saas", "internal"]

USAGE_PROFILES: dict[str, str] = {
    "distributed": "Shipped to clients (mobile app, SDK, on-prem software)",
    "saas": "Hosted service used by clients over the network",
    "internal": "Used only inside the company",
}


@dataclass(frozen=True)
class LicenseInfo:
    spdx: str
    name: str
    category: str
    obligations: tuple[str, ...] = field(default_factory=tuple)


USAGE_SHORT: dict[str, str] = {
    "distributed": "software shipped to clients",
    "saas": "a client-facing hosted service",
    "internal": "internal-only tools",
}

CATEGORY_LABELS = {
    "permissive": "Permissive",
    "public_domain": "Public domain",
    "weak_copyleft": "Weak copyleft",
    "strong_copyleft": "Strong copyleft",
    "network_copyleft": "Network copyleft",
    "source_available": "Source-available (not open source)",
    "commercial": "Commercial / proprietary",
    "non_standard": "Non-standard",
    "unknown": "Unknown",
}

_LICENSES: list[LicenseInfo] = [
    LicenseInfo("MIT", "MIT License", "permissive", ("Keep the copyright and license notice",)),
    LicenseInfo("Apache-2.0", "Apache License 2.0", "permissive",
                ("Keep the license and NOTICE file", "State significant changes you make")),
    LicenseInfo("BSD-2-Clause", "BSD 2-Clause", "permissive", ("Keep the copyright notice",)),
    LicenseInfo("BSD-3-Clause", "BSD 3-Clause", "permissive",
                ("Keep the copyright notice", "Do not use contributors' names for endorsement")),
    LicenseInfo("ISC", "ISC License", "permissive", ("Keep the copyright notice",)),
    LicenseInfo("PSF-2.0", "Python Software Foundation License", "permissive", ("Keep the license notice",)),
    LicenseInfo("HPND", "Historical Permission Notice and Disclaimer", "permissive", ("Keep the permission notice",)),
    LicenseInfo("OFL-1.1", "SIL Open Font License 1.1", "permissive",
                ("Keep the license with the font files", "Do not sell the fonts on their own")),
    LicenseInfo("0BSD", "Zero-Clause BSD", "public_domain"),
    LicenseInfo("Unlicense", "The Unlicense", "public_domain"),
    LicenseInfo("CC0-1.0", "Creative Commons Zero", "public_domain"),
    LicenseInfo("LGPL-2.1", "GNU Lesser GPL 2.1", "weak_copyleft",
                ("Link dynamically, never statically", "Publish changes you make to the library itself",
                 "Allow users to replace the library")),
    LicenseInfo("LGPL-3.0", "GNU Lesser GPL 3.0", "weak_copyleft",
                ("Link dynamically, never statically", "Publish changes you make to the library itself",
                 "Allow users to replace the library")),
    LicenseInfo("MPL-2.0", "Mozilla Public License 2.0", "weak_copyleft",
                ("Publish changes to MPL-licensed files", "Keep MPL files separate from proprietary code")),
    LicenseInfo("EPL-1.0", "Eclipse Public License 1.0", "weak_copyleft",
                ("Publish changes to EPL-licensed modules",)),
    LicenseInfo("EPL-2.0", "Eclipse Public License 2.0", "weak_copyleft",
                ("Publish changes to EPL-licensed modules",)),
    LicenseInfo("GPL-2.0", "GNU General Public License 2.0", "strong_copyleft",
                ("Any distributed program that links it must be released under the GPL",)),
    LicenseInfo("GPL-3.0", "GNU General Public License 3.0", "strong_copyleft",
                ("Any distributed program that links it must be released under the GPL",
                 "Grants patent rights to users")),
    LicenseInfo("AGPL-3.0", "GNU Affero GPL 3.0", "network_copyleft",
                ("Offering the software over a network counts as distribution",
                 "Full source of the whole service must be offered to its users")),
    LicenseInfo("SSPL-1.0", "Server Side Public License", "source_available",
                ("Offering it as a service requires releasing your entire service stack",)),
    LicenseInfo("BUSL-1.1", "Business Source License 1.1", "source_available",
                ("Production use limited by the vendor's Additional Use Grant",)),
    LicenseInfo("Elastic-2.0", "Elastic License 2.0", "source_available",
                ("Cannot be provided to third parties as a managed service",)),
    LicenseInfo("Commercial", "Commercial license", "commercial",
                ("A paid licence must be purchased and tracked by procurement",)),
    LicenseInfo("WTFPL", "Do What The F*ck You Want Public License", "non_standard",
                ("Not OSI-approved; many legal teams require review",)),
    LicenseInfo("UNKNOWN", "No license declared", "unknown",
                ("Without a license you have no legal right to use the code",)),
]

LICENSES: dict[str, LicenseInfo] = {lic.spdx.upper(): lic for lic in _LICENSES}

_ALIASES = {
    "APACHE 2.0": "Apache-2.0", "APACHE-2": "Apache-2.0", "APACHE LICENSE 2.0": "Apache-2.0", "APACHE2": "Apache-2.0",
    "BSD": "BSD-3-Clause", "NEW BSD": "BSD-3-Clause", "SIMPLIFIED BSD": "BSD-2-Clause",
    "GPL": "GPL-3.0", "GPLV2": "GPL-2.0", "GPLV3": "GPL-3.0", "GPL-2.0-ONLY": "GPL-2.0", "GPL-2.0-OR-LATER": "GPL-2.0",
    "GPL-3.0-ONLY": "GPL-3.0", "GPL-3.0-OR-LATER": "GPL-3.0", "AGPL": "AGPL-3.0", "AGPLV3": "AGPL-3.0",
    "AGPL-3.0-ONLY": "AGPL-3.0", "AGPL-3.0-OR-LATER": "AGPL-3.0", "LGPL": "LGPL-3.0", "LGPLV3": "LGPL-3.0",
    "LGPL-2.1-ONLY": "LGPL-2.1", "LGPL-2.1-OR-LATER": "LGPL-2.1", "LGPL-3.0-ONLY": "LGPL-3.0",
    "LGPL-3.0-OR-LATER": "LGPL-3.0", "MPL 2.0": "MPL-2.0", "SSPL": "SSPL-1.0", "BSL-1.1": "BUSL-1.1",
    "PROPRIETARY": "Commercial", "COMMERCIAL": "Commercial", "": "UNKNOWN", "NONE": "UNKNOWN",
    "NOASSERTION": "UNKNOWN", "SEE LICENSE IN LICENSE": "UNKNOWN",
}

# verdict per (category, usage profile)
POLICY: dict[str, dict[str, Verdict]] = {
    "permissive": {"distributed": "allow", "saas": "allow", "internal": "allow"},
    "public_domain": {"distributed": "allow", "saas": "allow", "internal": "allow"},
    "weak_copyleft": {"distributed": "conditions", "saas": "allow", "internal": "allow"},
    "strong_copyleft": {"distributed": "block", "saas": "conditions", "internal": "allow"},
    "network_copyleft": {"distributed": "block", "saas": "block", "internal": "conditions"},
    "source_available": {"distributed": "block", "saas": "block", "internal": "conditions"},
    "commercial": {"distributed": "conditions", "saas": "conditions", "internal": "conditions"},
    "non_standard": {"distributed": "conditions", "saas": "conditions", "internal": "conditions"},
    "unknown": {"distributed": "block", "saas": "block", "internal": "conditions"},
}

_REASONS: dict[tuple[str, str], str] = {
    ("weak_copyleft", "distributed"): "Allowed only if the library is dynamically linked and any changes to it are published.",
    ("strong_copyleft", "distributed"): "Shipping software that links a GPL library forces you to release your own source code under the GPL.",
    ("strong_copyleft", "saas"): "Acceptable while the service is only hosted, but it becomes a violation the day the code is shipped to a client.",
    ("strong_copyleft", "internal"): "Fine for internal use as long as the software is never given to anyone outside the company.",
    ("network_copyleft", "distributed"): "AGPL requires releasing the source of the entire application.",
    ("network_copyleft", "saas"): "AGPL treats network access as distribution: every client using the service could demand its full source code.",
    ("network_copyleft", "internal"): "Usable internally, but exposing it to clients later would trigger AGPL source release.",
    ("source_available", "distributed"): "Source-available licenses restrict commercial redistribution.",
    ("source_available", "saas"): "Source-available licenses restrict offering the software as part of a hosted service.",
    ("source_available", "internal"): "Internal use is usually permitted, but check the vendor's use grant.",
    ("commercial", "distributed"): "Requires a purchased commercial licence covering redistribution.",
    ("commercial", "saas"): "Requires a purchased commercial licence for production use.",
    ("commercial", "internal"): "Requires a purchased commercial licence, even for internal use.",
    ("non_standard", "distributed"): "Non-standard license text; legal review required before shipping.",
    ("non_standard", "saas"): "Non-standard license text; legal review required.",
    ("non_standard", "internal"): "Non-standard license text; legal review recommended.",
    ("unknown", "distributed"): "No license means no permission to use or ship the code.",
    ("unknown", "saas"): "No license means no permission to use the code in production.",
    ("unknown", "internal"): "No license declared; ask the author or legal before relying on it.",
}


def normalize(license_id: str | None) -> LicenseInfo:
    raw = (license_id or "").strip()
    key = raw.upper()
    if key in LICENSES:
        return LICENSES[key]
    if key in _ALIASES:
        return LICENSES[_ALIASES[key].upper()]
    # Expressions such as "(MIT OR Apache-2.0)" — choose the most permissive option.
    if " OR " in key:
        options = [normalize(part.strip(" ()")) for part in key.split(" OR ")]
        order = list(POLICY)
        return min(options, key=lambda lic: order.index(lic.category))
    for spdx, info in LICENSES.items():
        if spdx in key and spdx != "UNKNOWN":
            return info
    return LicenseInfo(raw or "UNKNOWN", raw or "No license declared", "unknown",
                       LICENSES["UNKNOWN"].obligations)


def evaluate(license_id: str | None, usage: str) -> dict:
    info = normalize(license_id)
    usage = usage if usage in USAGE_PROFILES else "saas"
    verdict = POLICY[info.category][usage]
    reason = _REASONS.get((info.category, usage)) or (
        f"{CATEGORY_LABELS[info.category]} license — compatible with this usage."
    )
    return {
        "license": info.spdx,
        "license_name": info.name,
        "category": info.category,
        "category_label": CATEGORY_LABELS[info.category],
        "usage": usage,
        "usage_label": USAGE_PROFILES[usage],
        "usage_short": USAGE_SHORT[usage],
        "verdict": verdict,
        "reason": reason,
        "obligations": list(info.obligations),
    }


def is_compatible(license_id: str | None, usage: str) -> bool:
    return evaluate(license_id, usage)["verdict"] == "allow"
