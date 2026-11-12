"""Measure retrieval: does the evidence for each test question contain its expected sources?

Usage: python -m tools.evaluate.run [--area road-traffic] [-k 8]

No legal judgment needed: the expected sources are listed in tests/<area>/questions.yaml.
Sources not in the index at all (not fetched yet) are reported separately, so a
missing fetch is not counted as a search failure.
"""
import argparse
import sys
from pathlib import Path

import yaml

from tools.retrieve.search import Index


def load_questions(area: str | None) -> list[tuple[str, dict]]:
    out = []
    for path in sorted(Path("tests").glob("*/questions.yaml")):
        if area and path.parent.name != area:
            continue
        out += [(path.parent.name, q) for q in yaml.safe_load(path.read_text(encoding="utf-8")) or []]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--area")
    ap.add_argument("-k", type=int, default=5, help="law search hits per question (plus 3 guidance pages), before following links")
    args = ap.parse_args()

    index = Index()
    found = expected_total = 0
    for area, q in load_questions(args.area):
        hits = index.evidence(q["question"], args.k)
        ranks = {h.id: i + 1 for i, h in enumerate(hits)}
        indexed = [s for s in q["expected_sources"] if index.get(s)]
        missing_data = [s for s in q["expected_sources"] if s not in indexed]
        got = [s for s in indexed if s in ranks]
        found += len(got)
        expected_total += len(indexed)
        mark = "PASS" if len(got) == len(indexed) and indexed else ("PART" if got else "MISS")
        print(f"{mark}  {q['id']}  {q['question']}")
        for s in indexed:
            where = f"#{ranks[s]} ({hits[ranks[s] - 1].via})" if s in ranks else "not found"
            print(f"        {s}: {where}")
        for s in missing_data:
            print(f"        {s}: NOT IN DATA (fetch it first)")
        print(f"        top hits: {', '.join(h.id for h in hits[:3])}")
    rate = found / expected_total if expected_total else 0.0
    print(f"\nRecall: {found}/{expected_total} expected sources found ({rate:.0%}), k={args.k}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
