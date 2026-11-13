"""Search the index: keyword + meaning (hybrid), then follow links one step.

No LLM and no topic rules. The same question over the same index always
returns the same results.
"""
import json
import re
import sqlite3
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from tools.index.build import INDEX
from tools.index.embed import embed_query

RRF_K = 60  # standard reciprocal-rank-fusion constant
CANDIDATES = 50  # chunks taken from each search before fusing


# Source types searched separately so one type never crowds out another:
LAW = frozenset({"act", "si"})              # legislation: decides the answer
GUIDELINES = frozenset({"guideline"})      # Sentencing Council: how courts sentence
CODE = frozenset({"code"})                  # Highway Code: long general rules, kept in its own pool
GUIDANCE = frozenset({"guidance"})          # plain-English GOV.UK pages: explain the answer


# Where a rule applies is recorded per unit as extent codes (E, W, S, NI). A person
# says where they are by nation; no nation means "England and Wales", the scope of
# this knowledge base, so a Wales-only rule still shows (its extent says W).
NATIONS = {
    "england": {"E"}, "wales": {"W"}, "scotland": {"S"},
    "northern ireland": {"NI"}, "england and wales": {"E", "W"},
}
ALIASES = {"ni": "northern ireland", "n ireland": "northern ireland", "uk": "england and wales"}
DEFAULT_NATIONS = {"E", "W"}


def nation_codes(nation: str | None) -> frozenset[str]:
    """Extent codes for a nation name (case-insensitive); None means England and Wales."""
    if nation is None or not nation.strip():
        return frozenset(DEFAULT_NATIONS)
    key = re.sub(r"\s+", " ", nation.strip().lower().replace("-", " "))
    key = ALIASES.get(key, key)
    if key not in NATIONS:
        raise ValueError(f"unknown nation {nation!r}: use one of {', '.join(sorted(NATIONS))}")
    return frozenset(NATIONS[key])


def web_url(source_url: str) -> str:
    """The page a person can open, from the URL we fetched (data API)."""
    return source_url.removesuffix("/data.xml").replace("www.gov.uk/api/content/", "www.gov.uk/")


@dataclass
class Hit:
    id: str
    title: str
    score: float
    excerpt: str
    url: str
    retrieved_at: str
    sha256: str
    valid_from: str
    status: str
    unapplied_changes: int
    extent: list
    via: str = "search"  # "search", or "cited by <id>" when reached through a link
    review: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class Index:
    def __init__(self, path: Path = INDEX):
        if not path.exists():
            raise FileNotFoundError(f"{path} not found: run python -m tools.index.build")
        # Load the whole index into memory and release the file (it is a few MB), so the
        # index can be rebuilt while a server is running; the server keeps serving the
        # version it loaded until it is restarted.
        disk = sqlite3.connect(path)
        self.db = sqlite3.connect(":memory:", check_same_thread=False)
        disk.backup(self.db)
        disk.close()
        self.db.row_factory = sqlite3.Row
        rows = self.db.execute("SELECT rowid, doc_id, vector FROM chunks ORDER BY rowid").fetchall()
        self.chunk_ids = [r["rowid"] for r in rows]
        self.chunk_doc = {r["rowid"]: r["doc_id"] for r in rows}
        self.vectors = np.vstack([np.frombuffer(r["vector"], dtype=np.float32) for r in rows])
        self.level = {r[0]: r[1] for r in self.db.execute("SELECT id, level FROM docs")}
        self.extent = {r[0]: set(json.loads(r[1] or "[]")) for r in self.db.execute("SELECT id, extent FROM docs")}

    def applies(self, doc_id: str, codes: frozenset[str] | None) -> bool:
        """True if the unit applies in any of the given places (None: anywhere)."""
        return codes is None or bool(self.extent.get(doc_id, set()) & codes)

    # --- the two searches -------------------------------------------------
    def _keyword(self, question: str) -> list[int]:
        words = re.findall(r"[a-z0-9]+", question.lower())
        if not words:
            return []
        query = " OR ".join(f'"{w}"' for w in words)
        sql = "SELECT rowid FROM chunks_fts WHERE chunks_fts MATCH ? ORDER BY bm25(chunks_fts) LIMIT ?"
        return [r[0] for r in self.db.execute(sql, (query, CANDIDATES))]

    def _meaning(self, question: str) -> list[int]:
        sims = self.vectors @ embed_query(question)
        order = np.argsort(-sims, kind="stable")[:CANDIDATES]
        return [self.chunk_ids[i] for i in order]

    # --- public API -------------------------------------------------------
    def search(self, question: str, k: int = 8, levels: frozenset[str] | None = None,
               codes: frozenset[str] | None = None) -> list[Hit]:
        """Fuse both rankings (reciprocal rank fusion), best chunk per unit.

        `levels` keeps only units of those levels (see LAW, GUIDELINES, CODE, GUIDANCE);
        `codes` only units that apply in one of those places (see nation_codes). None keeps all.
        """
        scores: dict[int, float] = {}
        for ranking in (self._keyword(question), self._meaning(question)):
            for rank, rowid in enumerate(ranking):
                scores[rowid] = scores.get(rowid, 0.0) + 1.0 / (RRF_K + rank + 1)
        best: dict[str, tuple[float, int]] = {}
        for rowid, score in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0])):
            doc = self.chunk_doc[rowid]
            if levels is not None and self.level[doc] not in levels:
                continue
            if not self.applies(doc, codes):
                continue
            if doc not in best:
                best[doc] = (score, rowid)
        top = sorted(best.items(), key=lambda kv: (-kv[1][0], kv[0]))[:k]
        return [self._hit(doc, score, rowid) for doc, (score, rowid) in top]

    def get(self, doc_id: str) -> dict | None:
        row = self.db.execute("SELECT * FROM docs WHERE id = ?", (doc_id,)).fetchone()
        if not row:
            return None
        out = dict(row)
        for key in ("extent", "areas", "review"):
            out[key] = json.loads(out[key]) if out[key] else None
        return out

    def related(self, doc_id: str) -> list[str]:
        """Units this one cites, and units that cite it, that are in the index."""
        sql = """
          SELECT to_id FROM links WHERE from_id = ? AND to_id IN (SELECT id FROM docs)
          UNION SELECT from_id FROM links WHERE to_id = ?
        """
        return sorted(r[0] for r in self.db.execute(sql, (doc_id, doc_id)))

    def evidence(self, question: str, k: int = 6, k_guidance: int = 3, k_guidelines: int = 3, k_code: int = 2,
                 codes: frozenset[str] | None = None) -> list[Hit]:
        """Top k law units, k_guidelines Sentencing Council guidelines, k_code Highway Code
        sections and k_guidance GOV.UK pages, each type searched separately: the guidance
        matches lay wording best and the guidelines and Highway Code are long, so mixed
        together they would crowd out the statute. Then units linked to them (one step),
        without duplicates. `codes` limits everything to units that apply in those places."""
        hits = (
            self.search(question, k, LAW, codes)
            + self.search(question, k_guidelines, GUIDELINES, codes)
            + self.search(question, k_code, CODE, codes)
            + self.search(question, k_guidance, GUIDANCE, codes)
        )
        seen = {h.id for h in hits}
        for h in list(hits):
            for other in self.related(h.id):
                if other not in seen and self.applies(other, codes):
                    seen.add(other)
                    hits.append(self._hit(other, 0.0, None, via=f"linked from {h.id}"))
        return hits

    # --- helpers ----------------------------------------------------------
    def _hit(self, doc_id: str, score: float, rowid: int | None, via: str = "search") -> Hit:
        d = self.get(doc_id)
        if rowid is not None:
            excerpt = self.db.execute("SELECT text FROM chunks WHERE rowid = ?", (rowid,)).fetchone()[0]
        else:
            excerpt = f"{d['title']}\n\n{d['text']}"
        return Hit(
            id=doc_id, title=d["title"], score=round(score, 4), excerpt=excerpt[:1500],
            url=web_url(d["url"]), retrieved_at=d["retrieved_at"], sha256=d["sha256"], valid_from=d["valid_from"],
            status=d["status"], unapplied_changes=d["unapplied_changes"], extent=d["extent"],
            via=via, review=d["review"] or [],
        )
