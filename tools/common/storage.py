"""Save raw source bytes as dated versions, never overwriting anything.

Each raw file <version>[.rN].<ext> has a provenance sidecar <version>[.rN].meta.json.
"""
import hashlib
import json
from collections.abc import Callable
from pathlib import Path

META = ".meta.json"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _identity(b: bytes) -> bytes:
    return b


def is_raw(path: Path) -> bool:
    return path.is_file() and not path.name.endswith(META) and not path.name.startswith(".")


def raw_files(directory: Path) -> list[Path]:
    """Raw files in a unit's directory (sidecars excluded), oldest version first."""
    if not directory.exists():
        return []
    files = [p for p in directory.iterdir() if is_raw(p)]
    return sorted(files, key=lambda p: (p.name.split(".")[0], len(p.name), p.name))


def sidecar(raw_file: Path) -> Path:
    stem = raw_file.name[: -len(raw_file.suffix)] if raw_file.suffix else raw_file.name
    return raw_file.with_name(stem + META)


def save_version(
    directory: Path,
    version: str,
    data: bytes,
    canonical: Callable[[bytes], bytes] = _identity,
    meta: dict | None = None,
    ext: str = ".xml",
) -> str:
    """Save data as <directory>/<version><ext>; return the outcome.

    Outcomes:
      'saved'       first time this content is seen
      'unchanged'   same content as this version, or as the newest saved file
                    (a publisher re-stamping a date without changing the text)
      'silent-edit' same version, different content: the publisher edited
                    the text without a new version date. Saved alongside as
                    <version>.r2<ext> (r3, ...) and flagged for review.
    `canonical` maps bytes to a form that ignores meaningless differences
    (e.g. XML attribute order) when comparing; the bytes saved stay exact.
    """
    target = sha256(canonical(data))
    files = raw_files(directory)
    existing = [p for p in files if p.name.split(".")[0] == version]
    for path in existing + files[-1:]:
        if sha256(canonical(path.read_bytes())) == target:
            return "unchanged"
    directory.mkdir(parents=True, exist_ok=True)
    name = f"{version}{ext}" if not existing else f"{version}.r{len(existing) + 1}{ext}"
    path = directory / name
    path.write_bytes(data)
    if meta is not None:  # provenance: the raw bytes themselves have no fetch time
        record = {**meta, "sha256": sha256(data)}
        sidecar(path).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return "saved" if not existing else "silent-edit"


def latest_version(directory: Path) -> Path | None:
    """Newest raw file (highest date, then highest revision)."""
    files = raw_files(directory)
    return files[-1] if files else None
