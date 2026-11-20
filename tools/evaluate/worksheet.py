"""Build a review worksheet so a person can verify the test questions against the source text.

Usage: python -m tools.evaluate.worksheet [--area road-traffic] [--ids rt-031,rt-032] [--out FILE]

For each question it shows the draft expected answer, the verbatim text of every expected
source (with its as-at date, extent and URL), what search actually returned, and a checklist.
It never edits questions.yaml: a person sets `verified: true` after ticking the checklist.
"""
import argparse
import re
import sys
from pathlib import Path

import yaml

from tools.evaluate.run import load_questions
from tools.retrieve.search import Index, nation_codes

MAX_LINES = 60


def split_front_matter(text: str) -> tuple[dict, str]:
    m = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    if not m:
        return {}, text
    try:
        meta = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return {}, text
    return (meta if isinstance(meta, dict) else {}), m.group(2).strip()


_ID_INDEX: dict[str, Path] | None = None


def find_current(unit_id: str) -> Path | None:
    """Path of the unit's current.md, found by the `id:` line in its front matter (scanned once)."""
    global _ID_INDEX
    if _ID_INDEX is None:
        _ID_INDEX = {}
        for p in Path("data").rglob("current.md"):
            m = re.search(r"^id: (.+)$", p.read_text(encoding="utf-8")[:600], re.M)
            if m:
                _ID_INDEX.setdefault(m.group(1).strip(), p)
    return _ID_INDEX.get(unit_id)


def render(q: dict, index: Index, k: int) -> str:
    nation = q.get("nation")
    sources = q.get("expected_sources") or []
    if isinstance(sources, str):
        sources = [sources]
    try:
        hits = index.evidence(q.get("question", ""), k, codes=nation_codes(nation))
    except ValueError as e:
        return f"## {q.get('id')}: {q.get('question')}\n\n**ERROR:** {e}\n\n---\n"
    ranks = {h.id: i + 1 for i, h in enumerate(hits)}
    out = [f"## {q.get('id')}: {q.get('question')}", ""]
    out += [f"- **Nation:** {nation or 'not given (England and Wales assumed)'}",
            f"- **Draft expected answer:** {q.get('expected_answer', 'MISSING')}",
            f"- **Currently marked verified:** {q.get('verified', False)}", ""]
    for sid in sources:
        path = find_current(sid)
        out.append(f"### Expected source `{sid}`")
        if not path:
            out += ["**NOT IN DATA.** Either the id is wrong or the unit was never fetched.", ""]
            continue
        meta, body = split_front_matter(path.read_text(encoding="utf-8"))
        v = meta.get("version") or {}
        out.append(f"{meta.get('title')} | level: {meta.get('level')} | extent: {','.join(meta.get('extent') or [])} "
                   f"({meta.get('extent_basis')}) | as at {v.get('valid_from')} | unapplied changes: {meta.get('unapplied_changes')}")
        if meta.get("extent_basis") == "assumed":
            out.append(f"Extent is ASSUMED, not stated: {meta.get('extent_evidence') or 'no evidence recorded'}")
        out.append(f"URL: {(meta.get('source') or {}).get('url')}")
        out.append(f"Search rank for this question (includes linked units, not only search hits): {('#%d' % ranks[sid]) if sid in ranks else 'NOT RETURNED'}")
        lines = body.splitlines()
        shown = "\n".join(lines[:MAX_LINES]) + (f"\n[... {len(lines) - MAX_LINES} more lines in {path.as_posix()}]" if len(lines) > MAX_LINES else "")
        out += ["", "````text", shown, "````", ""]
    all_extra = [h.id for h in hits if h.id not in sources]
    extra = all_extra[:6]
    more = f" (first 6 of {len(all_extra)}; run search for the rest)" if len(all_extra) > 6 else ""
    out += [f"**Also returned by search (not listed as expected){more}:** {', '.join(f'`{e}`' for e in extra) or 'none'}", "",
            "**Checklist** (a person ticks these, then sets `verified: true` in questions.yaml):",
            "- [ ] The quoted text above really supports every part of the expected answer (numbers, time limits, amounts)",
            "- [ ] No expected-answer detail comes from outside the quoted sources",
            "- [ ] The expected sources are the right ones: nothing essential is missing, nothing irrelevant is listed",
            "- [ ] Each source applies in the stated nation (extent) and is in force as at the date shown",
            "- [ ] The expected answer is not contradicted by any 'also returned' source",
            "- Verdict: `OK` / `FIX ANSWER` / `FIX SOURCES` / `UNSURE`. Notes:", "", "---", ""]
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--area", default="road-traffic")
    ap.add_argument("--ids", help="comma-separated question ids (default: all unverified)")
    ap.add_argument("--out", type=Path, help="default: docs/VERIFY-<area>.md")
    ap.add_argument("-k", type=int, default=6)
    args = ap.parse_args()

    args.out = args.out or Path(f"docs/VERIFY-{args.area}.md")
    if args.out.name == "questions.yaml":
        ap.error("--out must not be a questions.yaml file")
    wanted = set(args.ids.split(",")) if args.ids else None
    allq = [q for _, q in load_questions(args.area)]
    if not allq:
        ap.error(f"no questions found for area {args.area!r}")
    if wanted and (missing := wanted - {q.get("id") for q in allq}):
        ap.error(f"unknown question ids: {', '.join(sorted(missing))}")
    qs = [q for q in allq if (q.get("id") in wanted if wanted else q.get("verified") is not True)]
    index = Index()
    body = [f"# Verification worksheet: {args.area}", "",
            f"{len(qs)} questions. Generated by `python -m tools.evaluate.worksheet`; do not edit by hand.",
            "Text is verbatim from `data/`; long units are cut at "
            f"{MAX_LINES} lines (open the file named under the quote for the rest).", "", "---", ""]
    body += [render(q, index, args.k) for q in qs]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(body), encoding="utf-8")
    print(f"wrote {args.out} ({len(qs)} questions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
