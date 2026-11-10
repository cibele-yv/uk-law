"""Check 2: every data file traces to an unaltered raw file."""
import hashlib
import json

from tools.common.paths import RAW, raw_dir
from tools.validate.model import Doc, Problem


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check(docs: list[Doc]) -> list[Problem]:
    problems = []
    # raw files must still match the hash recorded when they were fetched
    for meta_path in sorted(RAW.rglob("*.meta.json")):
        xml = meta_path.with_name(meta_path.name.replace(".meta.json", ".xml"))
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if not xml.exists():
            problems.append(Problem("error", "hash", meta_path.as_posix(), "sidecar has no matching raw file"))
        elif _sha(xml.read_bytes()) != meta.get("sha256"):
            problems.append(Problem("error", "hash", xml.as_posix(), "raw file no longer matches its recorded SHA-256 (raw/ was edited)"))
    for xml in sorted(RAW.rglob("*.xml")):
        if not xml.with_name(xml.name.replace(".xml", ".meta.json")).exists():
            problems.append(Problem("error", "hash", xml.as_posix(), "raw file has no .meta.json sidecar"))
    # each data file must cite a raw file that exists for its unit
    for d in docs:
        uri = d.front.get("id", "")
        recorded = (d.front.get("source") or {}).get("sha256")
        known = {_sha(f.read_bytes()) for f in raw_dir(uri).glob("*.xml")}
        if recorded not in known:
            problems.append(Problem("error", "hash", d.path.as_posix(), f"source.sha256 {str(recorded)[:12]}... matches no raw file for {uri}"))
    return problems
