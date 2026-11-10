"""Shared types and loading for the validators."""
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class Problem:
    severity: str  # "error" fails the build; "warning" is listed for a person
    check: str
    where: str
    message: str


@dataclass
class Doc:
    path: Path
    front: dict
    body: str


def load_docs(root: Path = Path("data")) -> tuple[list[Doc], list[Problem]]:
    """Load every Markdown file under root. Unreadable front matter is itself a problem."""
    docs: list[Doc] = []
    problems: list[Problem] = []
    for path in sorted(root.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        parts = text.split("---\n", 2)
        try:
            if len(parts) != 3 or parts[0].strip():
                raise ValueError("no YAML front matter block")
            front = yaml.safe_load(parts[1])
            if not isinstance(front, dict):
                raise ValueError("front matter is not a mapping")
        except (ValueError, yaml.YAMLError) as e:
            problems.append(Problem("error", "load", path.as_posix(), f"cannot read front matter: {e}"))
            continue
        docs.append(Doc(path, front, parts[2].strip()))
    return docs, problems
