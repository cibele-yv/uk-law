"""Check 1: every file's front matter matches schema/provision.schema.json."""
import json
from datetime import date, datetime
from pathlib import Path

import jsonschema

from tools.validate.model import Doc, Problem


def check(docs: list[Doc]) -> list[Problem]:
    schema = json.loads(Path("schema/provision.schema.json").read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    problems = []
    for d in docs:
        where = d.path.as_posix()
        for err in validator.iter_errors(d.front):
            loc = ".".join(str(p) for p in err.absolute_path) or "(root)"
            problems.append(Problem("error", "schema", where, f"{loc}: {err.message}"))
        # jsonschema does not enforce "format" keywords without optional packages, so check dates here
        version = d.front.get("version") or {}
        for key in ("valid_from", "valid_to"):
            if version.get(key) is not None:
                try:
                    date.fromisoformat(str(version[key]))
                except ValueError:
                    problems.append(Problem("error", "schema", where, f"version.{key} is not a date: {version[key]!r}"))
        retrieved = (d.front.get("source") or {}).get("retrieved_at")
        if retrieved:
            try:
                datetime.fromisoformat(str(retrieved).replace("Z", "+00:00"))
            except ValueError:
                problems.append(Problem("error", "schema", where, f"source.retrieved_at is not a date-time: {retrieved!r}"))
    return problems
