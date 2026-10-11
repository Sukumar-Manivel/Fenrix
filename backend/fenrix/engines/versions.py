"""Tolerant version comparison across npm, PyPI, Maven, Go and Debian styles."""
from __future__ import annotations

import re
from functools import lru_cache

_PRE = {"alpha": -4, "a": -4, "beta": -3, "b": -3, "milestone": -2, "m": -2, "rc": -1, "cr": -1, "snapshot": -5}


@lru_cache(maxsize=4096)
def key(version: str) -> tuple:
    """Turn a version string into a sortable tuple.

    "2.0-beta9" < "2.0" < "2.0.1" and "1.2.6" < "1.2.10". Leading "v" and
    build metadata are ignored.
    """
    v = (version or "0").strip().lower().lstrip("v").split("+")[0]
    parts: list[tuple[int, int]] = []
    for token in re.split(r"[.\-_]", v):
        if not token:
            continue
        m = re.fullmatch(r"(\d+)([a-z]+)?(\d+)?", token)
        if m:
            parts.append((0, int(m.group(1))))
            if m.group(2):
                parts.append((-1, _PRE.get(m.group(2), -1)))
                parts.append((0, int(m.group(3) or 0)))
            continue
        m = re.fullmatch(r"([a-z]+)(\d+)?", token)
        if m:
            parts.append((-1, _PRE.get(m.group(1), -1)))
            parts.append((0, int(m.group(2) or 0)))
    return tuple(parts)


def compare(a: str, b: str) -> int:
    ka, kb = list(key(a)), list(key(b))
    width = max(len(ka), len(kb))
    ka += [(0, 0)] * (width - len(ka))
    kb += [(0, 0)] * (width - len(kb))
    return (ka > kb) - (ka < kb)


def in_range(version: str, introduced: str | None, fixed: str | None) -> bool:
    if introduced and compare(version, introduced) < 0:
        return False
    if fixed and compare(version, fixed) >= 0:
        return False
    return True


def is_affected(version: str, ranges, explicit) -> bool:
    if explicit and version in explicit:
        return True
    return any(in_range(version, lo, hi) for lo, hi in ranges)
