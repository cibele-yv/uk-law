"""Fetch every unit in the area files into raw/.

Usage: python -m tools.fetch.run [--area road-traffic] [--source govuk]
"""
import argparse
import sys
from datetime import datetime, timezone

from tools.common.areas import load_units
from tools.common.paths import raw_dir
from tools.common.storage import save_version, sha256
from tools.fetch import govuk, legislation

# One entry per source: (module, client class). A module provides
# handles(uri), canonical(bytes), EXT and SOURCE (publisher, format, licence).
SOURCES = [(legislation, legislation.LegislationClient), (govuk, govuk.GovukClient)]


def source_of(uri: str):
    return next((s for s in SOURCES if s[0].handles(uri)), None)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--area", help="only this area (default: all areas)")
    parser.add_argument("--source", help="only this source module, e.g. govuk or legislation")
    args = parser.parse_args()

    units = load_units(only=args.area)
    skipped = [u for u in units if source_of(u) is None]
    fetched = failures = 0

    for module, client_class in SOURCES:
        if args.source and module.__name__.rsplit(".", 1)[-1] != args.source:
            continue
        todo = [u for u in units if module.handles(u)]
        if not todo:
            continue
        with client_class() as client:
            for uri in todo:
                res = client.get(uri)
                if not res.ok:
                    failures += 1
                    print(f"{'FAILED':<17} {uri}  {res.error}")
                    continue
                meta = {
                    "url": res.url,
                    "retrieved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    **module.SOURCE,
                }
                outcome = save_version(raw_dir(uri), res.version, res.content, module.canonical, meta, module.EXT)
                label = "SILENT EDIT (review)" if outcome == "silent-edit" else outcome
                print(f"{label:<12} {uri}  v{res.version}  {sha256(res.content)[:12]}  {res.title}")
                fetched += 1

    for uri in skipped:
        print(f"{'skipped':<17} {uri}  (no fetcher yet)")
    print(f"\n{fetched}/{fetched + failures} fetched")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
