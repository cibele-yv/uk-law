"""Check 3: every relation points to a unit we hold, or one marked external."""
from tools.validate.model import Doc, Problem

KEYS = ("amended_by", "cites", "interprets")


def check(docs: list[Doc], external: set[str]) -> list[Problem]:
    held = {d.front.get("id") for d in docs}
    problems = []
    for d in docs:
        where = d.path.as_posix()
        for key in KEYS:
            for target in (d.front.get("relations") or {}).get(key, []):
                if target not in held and target not in external:
                    problems.append(Problem("error", "relations", where, f"{key}: {target} is not fetched and not marked external"))
    return problems
