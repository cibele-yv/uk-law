"""Rebuild data/ from raw/ for every unit in the area files.

Usage: python -m tools.normalise.run [--area road-traffic]
"""
import argparse
import sys
from collections.abc import Callable

from tools.common.areas import load_units
from tools.common.paths import raw_dir
from tools.common.storage import raw_files
from tools.fetch import govuk, legislation
from tools.normalise import clml, write
from tools.normalise import govuk as govuk_parser
from tools.normalise.clml import Provision

LEVELS = {"ukpga": "act", "asp": "act", "anaw": "act", "ukla": "act", "uksi": "si", "nisi": "si"}


def parser_for(uri: str, known: set[str]) -> Callable[[bytes], Provision] | None:
    """The parse function for a unit's source, or None if no source handles it."""
    if legislation.handles(uri):
        return lambda raw: clml.parse(raw, uri, LEVELS[uri.split("/")[0]])
    if govuk.handles(uri):
        return lambda raw: govuk_parser.parse(raw, uri, known=known)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--area")
    args = parser.parse_args()

    known = set(load_units())  # links are kept only to units we hold
    failed = 0
    for uri, areas in load_units(only=args.area).items():
        parse = parser_for(uri, known)
        if parse is None:
            continue
        files = raw_files(raw_dir(uri))
        if not files:
            print(f"{'MISSING':<8} {uri}  no raw file; run the fetcher")
            failed += 1
            continue
        try:
            versions = [(parse(f.read_bytes()), write.source_of(f)) for f in files]
            review = write.write_unit(uri, versions, areas)
        except Exception as e:  # a wrong parse is worse than a missing one
            print(f"{'FAILED':<8} {uri}  {type(e).__name__}: {e}")
            failed += 1
            continue
        print(f"{'REVIEW' if review else 'ok':<8} {uri}" + (f"  [{'; '.join(review)}]" if review else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
