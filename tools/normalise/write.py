"""Turn parsed provisions into data/ files: front matter + verbatim text, versioned."""
import json
from pathlib import Path

import yaml

from tools.common.paths import data_dir
from tools.normalise.clml import Provision


def front_matter(p: Provision, valid_to: str | None, areas: list[str], source: dict) -> dict:
    fm = {
        "id": p.id,
        "title": p.title,
        "level": p.level,
        "binding": "binding",
        "parent": p.parent,
        "made_under": None,
        "extent": p.extent,
        "areas": areas,
        "version": {"valid_from": p.valid_from, "valid_to": valid_to, "status": p.status},
        "unapplied_changes": p.unapplied_changes,
        "relations": {"cites": p.cites},
        "source": {
            "url": source["url"],
            "publisher": "legislation.gov.uk",
            "format": "CLML XML",
            "retrieved_at": source["retrieved_at"],
            "sha256": source["sha256"],
            "licence": "OGL-3.0",
        },
    }
    if p.review:
        fm["review"] = p.review
    return fm


def render_file(fm: dict, text: str) -> str:
    head = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True, width=10_000).rstrip()
    return f"---\n{head}\n---\n\n{text}\n"


def source_of(raw_file: Path) -> dict:
    meta = json.loads(raw_file.with_suffix(".meta.json").read_text(encoding="utf-8"))
    return {"url": meta["url"], "retrieved_at": meta["retrieved_at"], "sha256": meta["sha256"]}


def write_unit(uri: str, versions: list[tuple[Provision, dict]], areas: list[str]) -> list[str]:
    """Write versions/<valid_from>.md for each distinct valid_from and current.md for the newest.

    `versions` pairs each snapshot's Provision with its source record, oldest
    snapshot first. Returns review reasons for the newest version.
    """
    by_start: dict[str, tuple[Provision, dict]] = {}
    notes: list[str] = []
    for prov, src in versions:
        earlier = by_start.get(prov.valid_from)
        if earlier and earlier[0].text != prov.text:
            notes.append(f"text changed within version {prov.valid_from} (snapshots {earlier[0].snapshot} -> {prov.snapshot})")
        by_start[prov.valid_from] = (prov, src)  # later snapshot wins

    starts = sorted(by_start)
    out = data_dir(uri)
    (out / "versions").mkdir(parents=True, exist_ok=True)
    for i, start in enumerate(starts):
        prov, src = by_start[start]
        valid_to = starts[i + 1] if i + 1 < len(starts) else None
        if valid_to is None:
            prov.review = prov.review + notes
        content = render_file(front_matter(prov, valid_to, areas, src), prov.text)
        (out / "versions" / f"{start}.md").write_text(content, encoding="utf-8", newline="\n")
        if valid_to is None:
            (out / "current.md").write_text(content, encoding="utf-8", newline="\n")
    return by_start[starts[-1]][0].review
