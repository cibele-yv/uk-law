"""Read practice-area files (areas/*.yaml)."""
from pathlib import Path

import yaml


def load_units(areas_dir: str | Path = "areas", only: str | None = None) -> dict[str, list[str]]:
    """Return {unit_id: [area, ...]} across all area files, or just one area.

    A unit listed in several areas appears once, tagged with all of them.
    """
    units: dict[str, list[str]] = {}
    for path in sorted(Path(areas_dir).glob("*.yaml")):
        area = yaml.safe_load(path.read_text(encoding="utf-8"))
        if only and area["area"] != only:
            continue
        for unit in area.get("units", []):
            tags = units.setdefault(unit["id"], [])
            if area["area"] not in tags:
                tags.append(area["area"])
    return units
