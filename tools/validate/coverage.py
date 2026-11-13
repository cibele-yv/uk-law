"""Check 5: every unit listed in an area file exists in data/, and nothing is unlisted."""
from tools.common.areas import load_units
from tools.common.paths import data_dir
from tools.normalise.extent import unused_entries
from tools.fetch.run import source_of
from tools.validate.model import Doc, Problem


def check(docs: list[Doc]) -> list[Problem]:
    problems = []
    held = {d.front.get("id"): d for d in docs}
    listed = {uri: areas for uri, areas in load_units().items() if source_of(uri)}
    for uri, areas in listed.items():
        current = data_dir(uri) / "current.md"
        if not current.exists():
            problems.append(Problem("error", "coverage", uri, f"listed in {', '.join(areas)} but {current.as_posix()} does not exist"))
        elif held.get(uri) and sorted(held[uri].front.get("areas", [])) != sorted(areas):
            problems.append(Problem("error", "coverage", current.as_posix(), f"areas {held[uri].front.get('areas')} do not match the area files {areas}"))
    for uri in held:
        if uri not in listed:
            problems.append(Problem("warning", "coverage", uri, "in data/ but not listed in any area file (stale?)"))
    for stale in unused_entries(set(listed)):
        problems.append(Problem("warning", "coverage", "curation/extent.yaml", f"entry {stale} matches no listed unit (renamed or removed?)"))
    return problems
