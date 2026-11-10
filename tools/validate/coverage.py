"""Check 5: every unit listed in an area file exists in data/, and nothing is unlisted."""
from tools.common.areas import load_units
from tools.common.paths import data_dir
from tools.fetch import legislation
from tools.validate.model import Doc, Problem


def check(docs: list[Doc]) -> list[Problem]:
    problems = []
    held = {d.front.get("id"): d for d in docs}
    listed = {uri: areas for uri, areas in load_units().items() if legislation.handles(uri)}
    for uri, areas in listed.items():
        current = data_dir(uri) / "current.md"
        if not current.exists():
            problems.append(Problem("error", "coverage", uri, f"listed in {', '.join(areas)} but {current.as_posix()} does not exist"))
        elif held.get(uri) and sorted(held[uri].front.get("areas", [])) != sorted(areas):
            problems.append(Problem("error", "coverage", current.as_posix(), f"areas {held[uri].front.get('areas')} do not match the area files {areas}"))
    for uri in held:
        if uri not in listed:
            problems.append(Problem("warning", "coverage", uri, "in data/ but not listed in any area file (stale?)"))
    return problems
