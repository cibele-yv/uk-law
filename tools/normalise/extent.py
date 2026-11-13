"""Where a non-legislation unit applies (England, Wales, Scotland, Northern Ireland).

Only what a source states is recorded (see curation/extent.yaml). Otherwise the unit
is assumed to apply in England and Wales, the scope of this knowledge base, and is
marked `assumed` so that answers can say the source does not state its territory.
"""
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

OVERRIDES = Path(__file__).resolve().parents[2] / "curation" / "extent.yaml"
DEFAULT = ["E", "W"]
CODES = {"E", "W", "S", "NI"}
OTHER_NATIONS = {"Scotland": "Scotland", "Northern Ireland": "Northern Ireland"}


@dataclass
class Extent:
    extent: list[str]
    basis: str  # "stated" or "assumed"
    evidence: str | None = None
    review: list[str] = field(default_factory=list)


@lru_cache(maxsize=1)
def _entries() -> tuple[dict[str, dict], list[dict]]:
    entries = yaml.safe_load(OVERRIDES.read_text(encoding="utf-8")) or []
    for e in entries:
        bad = set(e["extent"]) - CODES
        if bad or not e.get("evidence") or not (("id" in e) != ("prefix" in e)):
            raise ValueError(f"curation/extent.yaml: invalid entry {e}")
    return {e["id"]: e for e in entries if "id" in e}, [e for e in entries if "prefix" in e]


def entry_for(uri: str) -> dict | None:
    """The curated entry for a unit: an exact `id`, else the longest matching `prefix`."""
    by_id, prefixes = _entries()
    if uri in by_id:
        return by_id[uri]
    matching = [e for e in prefixes if uri.startswith(e["prefix"])]
    return max(matching, key=lambda e: len(e["prefix"]), default=None)


def unused_entries(units: set[str]) -> list[str]:
    """Curated entries that match none of the given unit IDs (stale after a rename)."""
    by_id, prefixes = _entries()
    stale = [i for i in by_id if i not in units]
    stale += [e["prefix"] for e in prefixes if not any(u.startswith(e["prefix"]) for u in units)]
    return stale


def resolve(uri: str, text: str) -> Extent:
    entry = entry_for(uri)
    if entry:
        return Extent(list(entry["extent"]), "stated", entry["evidence"])
    review = []
    mentioned = [n for n in OTHER_NATIONS if re.search(rf"\b{n}\b", text)]
    if mentioned:
        review.append(
            f"territory not stated; assumed England and Wales, but the text mentions {' and '.join(mentioned)}: "
            "check whether it covers them (add an entry to curation/extent.yaml with the quoted sentence)"
        )
    return Extent(list(DEFAULT), "assumed", None, review)
