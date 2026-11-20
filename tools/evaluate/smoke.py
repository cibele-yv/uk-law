"""End-to-end smoke test: ask each question in a fresh `claude -p` session that has only the
uk-law MCP server, then check the reply and the tool calls with fixed rules (no model judge).

Usage: python -m tools.evaluate.smoke [--only S1,S3] [--jobs 3] [--model sonnet] [--max-budget 1.0]

Needs the `claude` CLI logged in, and the index built (python -m tools.index.build).
Writes docs/SMOKE-TEST-results.md and raw transcripts to smoke-results/ (git-ignored).
Exit code 1 if any check fails.

Checks on every answer
  C1  a uk-law tool was called
  C2  the reply cites a URL that a tool returned
  C3  the reply gives an "as at" / in-force date
  C4  the reply says it is legal information, not advice, and points to a solicitor / advice service
  C5  every £ amount, number of points and number of days in the reply appears in the tool results
plus the per-question checks in tests/smoke/questions.yaml.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SYSTEM = "You are a helpful assistant. Use the tools you are given when they help."
URL = re.compile(r"https?://[^\s)\]>\"'`,]+")


def mcp_config() -> Path:
    cfg = {"mcpServers": {"uk-law": {"command": sys.executable, "args": ["-m", "tools.mcp.server"],
                                     "env": {"PYTHONPATH": str(ROOT)}}}}
    path = Path(tempfile.mkdtemp()) / "mcp.json"
    path.write_text(json.dumps(cfg), encoding="utf-8")
    return path


def ask(prompt: str, cfg: Path, model: str | None, budget: float, timeout: int) -> dict:
    cmd = [shutil.which("claude") or "claude", "-p", prompt, "--mcp-config", str(cfg), "--strict-mcp-config",
           "--tools", "", "--allowedTools", "mcp__uk-law", "--system-prompt", SYSTEM,
           "--output-format", "stream-json", "--verbose", "--no-session-persistence",
           "--max-budget-usd", str(budget)]
    if model:
        cmd += ["--model", model]
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE_CODE") and k != "CLAUDECODE"}
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", cwd=ROOT, env=env, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"error": f"timed out after {timeout}s"}
    events = []
    for line in p.stdout.splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            pass
    reply, tools_called, results = "", [], []
    for e in events:
        content = (e.get("message") or {}).get("content")
        if e.get("type") == "assistant" and isinstance(content, list):
            for b in content:
                if b.get("type") == "tool_use":
                    tools_called.append(b.get("name", ""))
        if e.get("type") == "user" and isinstance(content, list):
            for b in content:
                if b.get("type") == "tool_result":
                    c = b.get("content")
                    results.append(c if isinstance(c, str) else " ".join(x.get("text", "") for x in c or []))
        if e.get("type") == "result":
            reply = e.get("result") or ""
    if not events or not reply:
        return {"error": f"no reply (exit {p.returncode}): {(p.stderr or p.stdout)[:400]}", "events": len(events)}
    return {"reply": reply, "tools": tools_called, "results": "\n".join(results), "events": len(events)}


WORDS = {"seven": 7, "fourteen": 14, "twenty-one": 21, "twenty-eight": 28, "fifteen": 15, "six": 6, "twelve": 12,
         "three": 3, "four": 4, "five": 5, "ten": 10, "thirty": 30, "forty-two": 42, "fifty-six": 56, "sixty": 60,
         "ninety": 90, "seventy-two": 72}


def figures(text: str) -> set[str]:
    t = text.replace(",", "")
    for ch in ("–", "‐", "‑", "�"):  # dashes and a lost non-breaking hyphen
        t = t.replace(ch, "-")
    for w, n in WORDS.items():  # the Acts write "twenty-one days"; the reply may say "21 days"
        t = re.sub(rf"\b{w}\b(?=\s+(?:working\s+)?days?\b|\s+(?:penalty\s+)?points?\b)", str(n), t, flags=re.I)
    out = set(re.findall(r"£\s?\d+(?:\.\d+)?", t))
    # lookbehind and lookahead: "rule 29.4 points to ..." is not "4 points"
    out |= {m + " points" for m in re.findall(r"(?<![\d.])\b(\d+)\s+(?:penalty\s+)?points?\b(?!\s+to\b)", t, re.I)}
    out |= {m + " days" for m in re.findall(r"(?<![\d.])\b(\d+)\s+(?:working\s+)?days?\b", t, re.I)}
    return {re.sub(r"£\s", "£", f) for f in out}


def check(q: dict, r: dict) -> list[tuple[str, bool, str]]:
    if "error" in r:
        return [("RUN", False, r["error"])]
    reply, results = r["reply"], r["results"]
    flat = re.sub(r"\s+", " ", reply)
    out = []
    out.append(("C1 tool called", any("uk-law" in t or "uk_law" in t for t in r["tools"]), ", ".join(r["tools"]) or "no tool call"))
    cited = [u for u in URL.findall(reply) if u.rstrip(".").split("#")[0].replace("/data.xml", "") in results.replace("/data.xml", "")]
    out.append(("C2 cites a returned URL", bool(cited), f"{len(cited)} cited"))
    out.append(("C3 gives an as-at date", bool(re.search(r"as at|as of|in force (from|since|as)|valid from|version", reply, re.I)
                                              and re.search(r"\b(19|20)\d\d\b", reply)), ""))
    out.append(("C4 not advice + solicitor/advice", bool(re.search(r"not (legal )?advice|legal information", reply, re.I)
                                                        and re.search(r"solicitor|citizens advice|advice (service|centre)|lawyer", reply, re.I)), ""))
    known = figures(results)
    nums = set(re.findall(r"(?<![\d.])\d+(?![\d.])", results.replace(",", "")))

    def sourced(f: str) -> bool:  # amounts must match exactly; points and days may sit in a range ("3-6")
        return f in known or (not f.startswith("£") and f.split()[0] in nums)
    bad = sorted(f for f in figures(reply) if not sourced(f))
    out.append(("C5 figures come from sources", not bad, ("not in tool results: " + ", ".join(bad)) if bad else ""))
    if q.get("warning_first"):
        out.append(("warning first", bool(re.search(r"only partly|partly|only in part|in part|partial|limited coverage", flat[:600], re.I)), flat[:120]))
    for pat in q.get("all_of", []):
        out.append((f"must match /{pat}/", bool(re.search(pat, flat, re.I)), ""))
    if q.get("any_of"):
        out.append(("any of " + " | ".join(q["any_of"]), any(re.search(p, flat, re.I) for p in q["any_of"]), ""))
    for pat in q.get("none_of", []):
        m = re.search(pat, flat, re.I)
        out.append((f"must NOT match /{pat}/", not m, flat[max(0, m.start() - 60):m.end() + 60] if m else ""))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated ids, e.g. S1,S3")
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--model")
    ap.add_argument("--max-budget", type=float, default=1.0, help="USD per question")
    ap.add_argument("--timeout", type=int, default=300)
    args = ap.parse_args()

    if not (ROOT / "index" / "kb.sqlite").exists():
        print("index/kb.sqlite missing: run  python -m tools.index.build", file=sys.stderr)
        return 2
    qs = yaml.safe_load((ROOT / "tests/smoke/questions.yaml").read_text(encoding="utf-8"))
    if args.only:
        wanted = set(args.only.split(","))
        qs = [q for q in qs if q["id"] in wanted]
    cfg = mcp_config()
    out_dir = ROOT / "smoke-results"
    out_dir.mkdir(exist_ok=True)

    def run(q):
        r = ask(q["prompt"], cfg, args.model, args.max_budget, args.timeout)
        (out_dir / f"{q['id']}.json").write_text(json.dumps({"question": q, **r}, indent=2), encoding="utf-8")
        return q, r, check(q, r)

    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as ex:
        runs = list(ex.map(run, qs))

    lines = ["# Smoke test results", "", "Generated by `python -m tools.evaluate.smoke`. Fixed rules only, no model judge; "
             "raw transcripts are in `smoke-results/` (not committed).", ""]
    failed = 0
    for q, r, checks in runs:
        bad = [c for c in checks if not c[1]]
        failed += bool(bad)
        lines += [f"## {q['id']} {'PASS' if not bad else 'FAIL'}: {q['prompt']}", ""]
        if q.get("note"):
            lines += [f"_{q['note']}_", ""]
        for name, ok, detail in checks:
            lines.append(f"- {'PASS' if ok else '**FAIL**'} {name}" + (f": {detail}" if detail and not ok else ""))
        lines += ["", "<details><summary>Reply</summary>", "", (r.get("reply") or r.get("error", "")).strip(), "", "</details>", ""]
        print(f"{'PASS' if not bad else 'FAIL'}  {q['id']}  " + ("; ".join(f"{c[0]}" for c in bad) if bad else ""))
    lines.insert(3, f"**{len(runs) - failed}/{len(runs)} questions passed every check.**")
    Path(ROOT / "docs/SMOKE-TEST-results.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\n{len(runs) - failed}/{len(runs)} passed. Report: docs/SMOKE-TEST-results.md")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
