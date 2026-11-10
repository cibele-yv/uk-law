"""Rebuild data/ from raw/ for every unit in the area files.

Usage: python -m tools.normalise.run [--area road-traffic]
"""
import argparse
import sys

from tools.common.areas import load_units
from tools.fetch import legislation
from tools.normalise import clml, write

LEVELS = {"ukpga": "act", "asp": "act", "anaw": "act", "ukla": "act", "uksi": "si", "nisi": "si"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--area")
    args = parser.parse_args()

    failed = 0
    for uri, areas in load_units(only=args.area).items():
        if not legislation.handles(uri):
            continue
        raw_files = sorted(legislation.raw_dir(uri).glob("*.xml"))
        if not raw_files:
            print(f"{'MISSING':<8} {uri}  no raw file; run the fetcher")
            failed += 1
            continue
        level = LEVELS[uri.split("/")[0]]
        try:
            versions = [(clml.parse(f.read_bytes(), uri, level), write.source_of(f)) for f in raw_files]
            review = write.write_unit(uri, versions, areas)
        except Exception as e:  # a wrong parse is worse than a missing one
            print(f"{'FAILED':<8} {uri}  {type(e).__name__}: {e}")
            failed += 1
            continue
        print(f"{'REVIEW' if review else 'ok':<8} {uri}" + (f"  [{'; '.join(review)}]" if review else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
