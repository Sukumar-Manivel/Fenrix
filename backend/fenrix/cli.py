"""Fenrix command line.

    fenrix check moment --ecosystem npm --usage saas
    fenrix scan package.json --usage distributed     # exits 1 if anything is blocked (CI gate)
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from fenrix.engines import agent, parsers

_TTY = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
_C = {"approve": "32", "conditions": "33", "block": "31", "unknown": "35", "dim": "2", "bold": "1"}
ICON = {"pass": "✓", "warn": "!", "fail": "✗", "info": "·"}
STEP_COLOR = {"pass": "32", "warn": "33", "fail": "31", "info": "2"}


def c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _TTY else text


def cmd_check(args: argparse.Namespace) -> int:
    r = agent.check(args.name, args.ecosystem, args.version, args.usage, args.license, use_llm=not args.no_llm)
    if args.json:
        print(json.dumps(r, indent=2, default=str))
        return 0 if r["decision"] != "block" else 1
    print()
    print(c(f"  {r['decision_label'].upper()}", _C[r["decision"]] + ";1"), " ", r["headline"])
    print()
    for step in r["steps"]:
        print(f"  {c(ICON[step['status']], STEP_COLOR[step['status']])} {c(step['title'], '1')}: {step['detail']}")
    if r["alternatives"]:
        print(c("\n  Alternatives", "1"))
        for a in r["alternatives"][:3]:
            print(f"    {a['name']:<36} {a['license']:<22} fit {a['fit_score']}/100")
    fix = r["remediation"]
    if fix:
        print(c(f"\n  Fix: {fix['title']}", "1"), c(f"({fix['generated_by']})", _C["dim"]))
        if fix.get("after"):
            for line in fix["after"].splitlines():
                print(c("    │ ", _C["dim"]) + line)
        for s in fix.get("steps", []):
            print(f"    → {s}")
    print()
    return 1 if r["decision"] == "block" else 0


def cmd_scan(args: argparse.Namespace) -> int:
    with open(args.file, encoding="utf-8") as fh:
        packages = parsers.parse(args.file, fh.read())
    report = agent.scan_manifest([p for p in packages if p.get("name")], args.usage)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(c(f"\n  Fenrix scan of {args.file} ({len(report['results'])} packages, usage: {args.usage})\n", "1"))
        order = {"block": 0, "unknown": 1, "conditions": 2, "approve": 3}
        for r in sorted(report["results"], key=lambda r: order[r["decision"]]):
            if r["decision"] == "approve" and not args.verbose:
                continue
            label = c(f"{r['decision'].upper():<10}", _C[r["decision"]])
            print(f"  {label} {r['name']}@{r['version'] or 'latest'} — {r['headline']}")
            if r["fix"]:
                print(c(f"             fix: {r['fix']}", _C["dim"]))
        s = report["summary"]
        print(f"\n  {s['block']} blocked · {s['conditions']} with conditions · {s['unknown']} need review · {s['approve']} approved\n")
    fail_on = {"block": {"block"}, "conditions": {"block", "conditions"}, "never": set()}[args.fail_on]
    return 1 if any(r["decision"] in fail_on for r in report["results"]) else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="fenrix", description="Check open-source libraries before they reach production.")
    sub = p.add_subparsers(dest="command", required=True)

    chk = sub.add_parser("check", help="Ask the Fenrix agent about one library")
    chk.add_argument("name")
    chk.add_argument("--ecosystem", choices=["npm", "pypi", "maven", "go", "deb"])
    chk.add_argument("--version")
    chk.add_argument("--usage", choices=["distributed", "saas", "internal"], default="saas")
    chk.add_argument("--license", help="Declared license, for packages Fenrix does not know")
    chk.add_argument("--no-llm", action="store_true", help="Never call the local LLM")
    chk.add_argument("--json", action="store_true")
    chk.set_defaults(func=cmd_check)

    scn = sub.add_parser("scan", help="Check every dependency in a manifest or SBOM")
    scn.add_argument("file", help=", ".join(parsers.SUPPORTED))
    scn.add_argument("--usage", choices=["distributed", "saas", "internal"], default="saas")
    scn.add_argument("--fail-on", choices=["block", "conditions", "never"], default="block")
    scn.add_argument("--verbose", action="store_true", help="Also list approved packages")
    scn.add_argument("--json", action="store_true")
    scn.set_defaults(func=cmd_scan)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
