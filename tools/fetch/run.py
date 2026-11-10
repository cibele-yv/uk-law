"""Fetch every unit in the area files into raw/.

Usage: python -m tools.fetch.run [--area road-traffic]
"""
import argparse
import sys
from datetime import datetime, timezone

from tools.common.areas import load_units
from tools.common.storage import save_version, sha256
from tools.fetch import legislation


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--area", help="only this area (default: all areas)")
    args = parser.parse_args()

    units = load_units(only=args.area)
    todo = [u for u in units if legislation.handles(u)]
    skipped = [u for u in units if not legislation.handles(u)]
    failures = 0

    with legislation.LegislationClient() as client:
        for uri in todo:
            res = client.get(uri)
            if res.ok:
                meta = {"url": res.url, "retrieved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
                outcome = save_version(legislation.raw_dir(uri), res.version, res.content, legislation.canonical, meta)
                label = "SILENT EDIT (review)" if outcome == "silent-edit" else outcome
                print(f"{label:<12} {uri}  v{res.version}  {sha256(res.content)[:12]}  {res.title}")
            else:
                failures += 1
                print(f"{'FAILED':<17} {uri}  {res.error}")

    for uri in skipped:
        print(f"{'skipped':<17} {uri}  (no fetcher yet)")
    print(f"\n{len(todo) - failures}/{len(todo)} fetched")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
