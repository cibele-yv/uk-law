"""Check 2: every data file traces to an unaltered raw file."""
import hashlib
import json

from tools.common.paths import RAW_ROOT, raw_dir
from tools.common.storage import META, is_raw, raw_files, sidecar
from tools.validate.model import Doc, Problem


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check(docs: list[Doc]) -> list[Problem]:
    problems = []
    raws = [p for p in sorted(RAW_ROOT.rglob("*")) if is_raw(p)]
    raw_by_sidecar = {sidecar(p): p for p in raws}
    # raw files must still match the hash recorded when they were fetched
    for meta_path in sorted(RAW_ROOT.rglob(f"*{META}")):
        raw = raw_by_sidecar.get(meta_path)
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if raw is None:
            problems.append(Problem("error", "hash", meta_path.as_posix(), "sidecar has no matching raw file"))
        elif _sha(raw.read_bytes()) != meta.get("sha256"):
            problems.append(Problem("error", "hash", raw.as_posix(), "raw file no longer matches its recorded SHA-256 (raw/ was edited)"))
    for raw in raws:
        if not sidecar(raw).exists():
            problems.append(Problem("error", "hash", raw.as_posix(), f"raw file has no {META} sidecar"))
    # each data file must cite a raw file that exists for its unit
    for d in docs:
        uri = d.front.get("id", "")
        recorded = (d.front.get("source") or {}).get("sha256")
        known = {_sha(f.read_bytes()) for f in raw_files(raw_dir(uri))}
        if recorded not in known:
            problems.append(Problem("error", "hash", d.path.as_posix(), f"source.sha256 {str(recorded)[:12]}... matches no raw file for {uri}"))
    return problems
