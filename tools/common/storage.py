"""Save raw source bytes as dated versions, never overwriting anything."""
import hashlib
import json
from collections.abc import Callable
from pathlib import Path


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _identity(b: bytes) -> bytes:
    return b


def save_version(
    directory: Path,
    version: str,
    data: bytes,
    canonical: Callable[[bytes], bytes] = _identity,
    meta: dict | None = None,
) -> str:
    """Save data as <directory>/<version>.<ext-less name>; return the outcome.

    Outcomes:
      'saved'       first time this version is seen
      'unchanged'   same version, same content: nothing written
      'silent-edit' same version, different content: the publisher edited
                    the text without a new version date. Saved alongside as
                    <version>.r2.xml (r3, ...) and flagged for review.
    `canonical` maps bytes to a form that ignores meaningless differences
    (e.g. XML attribute order) when comparing; the bytes saved stay exact.
    """
    target = canonical(data)
    existing = sorted(directory.glob(f"{version}.xml")) + sorted(directory.glob(f"{version}.r*.xml"))
    for path in existing:
        if sha256(canonical(path.read_bytes())) == sha256(target):
            return "unchanged"
    directory.mkdir(parents=True, exist_ok=True)
    name = f"{version}.xml" if not existing else f"{version}.r{len(existing) + 1}.xml"
    (directory / name).write_bytes(data)
    if meta is not None:  # provenance sidecar: the XML itself has no fetch time
        record = {**meta, "sha256": sha256(data)}
        sidecar = directory / name.replace(".xml", ".meta.json")
        sidecar.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return "saved" if not existing else "silent-edit"


def latest_version(directory: Path) -> Path | None:
    """Newest version file (highest date, then highest revision)."""
    files = sorted(directory.glob("*.xml"), key=lambda p: (p.name.split(".")[0], len(p.name)))
    return files[-1] if files else None
