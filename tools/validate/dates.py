"""Check 4: version dates are ordered, chained and consistent with current.md."""
from collections import defaultdict

from tools.validate.model import Doc, Problem


def check(docs: list[Doc]) -> list[Problem]:
    problems = []
    versions: dict[str, list[Doc]] = defaultdict(list)
    current: dict[str, Doc] = {}
    for d in docs:
        uri = d.front.get("id")
        where = d.path.as_posix()
        if d.path.name == "current.md":
            current[uri] = d
        else:
            versions[uri].append(d)
        v = d.front.get("version") or {}
        if v.get("valid_to") and str(v.get("valid_from")) >= str(v["valid_to"]):
            problems.append(Problem("error", "dates", where, f"valid_from {v.get('valid_from')} is not before valid_to {v['valid_to']}"))
        if d.path.parent.name == "versions" and d.path.stem != str(v.get("valid_from")):
            problems.append(Problem("error", "dates", where, f"file name does not match valid_from {v.get('valid_from')}"))

    for uri, found in versions.items():
        found.sort(key=lambda d: str(d.front["version"]["valid_from"]))
        for older, newer in zip(found, found[1:]):
            if older.front["version"].get("valid_to") != newer.front["version"]["valid_from"]:
                problems.append(Problem("error", "dates", older.path.as_posix(), "valid_to does not meet the next version's valid_from (gap or overlap)"))
        newest = found[-1]
        if newest.front["version"].get("valid_to") is not None:
            problems.append(Problem("error", "dates", newest.path.as_posix(), "newest version must have valid_to: null"))
        cur = current.get(uri)
        if cur is None:
            problems.append(Problem("error", "dates", uri, "no current.md"))
        elif cur.front != newest.front or cur.body != newest.body:
            problems.append(Problem("error", "dates", cur.path.as_posix(), "current.md differs from the newest versions/ file"))
    return problems
