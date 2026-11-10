"""Run every validation check over data/ and raw/.

Usage: python -m tools.validate.run

Exit code 1 if any error is found. Warnings and review flags are listed but do not fail.
"""
import sys
from pathlib import Path

import yaml

from tools.validate import coverage, dates, hashes, relations, schema
from tools.validate.model import Problem, load_docs


def external_ids(areas_dir: Path = Path("areas")) -> set[str]:
    """IDs deliberately not fetched, listed under `external:` in an area file."""
    found: set[str] = set()
    for path in areas_dir.glob("*.yaml"):
        found.update(yaml.safe_load(path.read_text(encoding="utf-8")).get("external", []) or [])
    return found


def main() -> int:
    docs, problems = load_docs()
    problems += schema.check(docs)
    problems += hashes.check(docs)
    problems += relations.check(docs, external_ids())
    problems += dates.check(docs)
    problems += coverage.check(docs)
    review = [
        Problem("warning", "review", d.path.as_posix(), "; ".join(d.front["review"]))
        for d in docs
        if d.front.get("review") and d.path.name == "current.md"
    ]

    errors = [p for p in problems if p.severity == "error"]
    warnings = [p for p in problems if p.severity == "warning"] + review
    for p in errors + warnings:
        print(f"{p.severity.upper():<8} [{p.check}] {p.where}: {p.message}")
    units = len([d for d in docs if d.path.name == "current.md"])
    print(f"\n{units} units, {len(docs)} files checked: {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
