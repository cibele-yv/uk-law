"""Build the search index from data/ into one SQLite file.

Usage: python -m tools.index.build

The index is a derived artefact: data/ stays the source of truth, and the index
is rebuilt from scratch every time (index/ is gitignored).

Tables:
  docs        one row per unit (current version): id, title, source fields, text
  chunks      search-sized pieces of each unit, with an embedding vector
  chunks_fts  SQLite full-text index over chunks (keyword search)
  links       from_id -> to_id: 'cites' from front matter relations.cites (other
              legislation), 'refers_to' from plain-text references in the same Act
"""
import json
import sqlite3
import sys
from pathlib import Path

from tools.index.chunk import chunks
from tools.index.embed import MODEL, embed_documents
from tools.index.links import same_act_refs
from tools.validate.model import load_docs

REPO = Path(__file__).resolve().parents[2]
INDEX = REPO / "index" / "kb.sqlite"  # absolute: the MCP server may start in any folder

SCHEMA = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE docs (
  id TEXT PRIMARY KEY, title TEXT, level TEXT, extent TEXT, extent_basis TEXT, extent_evidence TEXT, areas TEXT,
  valid_from TEXT, status TEXT, unapplied_changes INTEGER, review TEXT,
  url TEXT, retrieved_at TEXT, sha256 TEXT, licence TEXT, path TEXT, text TEXT
);
CREATE TABLE chunks (rowid INTEGER PRIMARY KEY, doc_id TEXT, n INTEGER, text TEXT, vector BLOB);
CREATE VIRTUAL TABLE chunks_fts USING fts5(text, content='chunks', content_rowid='rowid', tokenize='porter');
CREATE TABLE links (from_id TEXT, to_id TEXT, kind TEXT);
"""


def build(path: Path = INDEX) -> tuple[int, int, int]:
    docs, problems = load_docs(REPO / "data")
    if problems:
        raise SystemExit(f"cannot build index: {len(problems)} unreadable files (run the validator)")
    current = [d for d in docs if d.path.name == "current.md"]
    known = {d.front["id"] for d in current}

    path.parent.mkdir(exist_ok=True)
    path.unlink(missing_ok=True)
    db = sqlite3.connect(path)
    db.executescript(SCHEMA)
    db.execute("INSERT INTO meta VALUES ('model', ?)", (MODEL,))

    rows: list[tuple[str, int, str]] = []
    for d in current:
        f, v, s = d.front, d.front.get("version", {}), d.front.get("source", {})
        db.execute(
            "INSERT INTO docs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                f["id"], f.get("title"), f.get("level"), json.dumps(f.get("extent")), f.get("extent_basis"), f.get("extent_evidence"),
                json.dumps(f.get("areas")),
                v.get("valid_from"), v.get("status"), f.get("unapplied_changes", 0), json.dumps(f.get("review", [])),
                s.get("url"), s.get("retrieved_at"), s.get("sha256"), s.get("licence"), d.path.as_posix(), d.body,
            ),
        )
        for target in (f.get("relations") or {}).get("cites") or []:
            db.execute("INSERT INTO links VALUES (?,?,'cites')", (f["id"], target))
        for target in sorted(same_act_refs(f["id"], d.body, known)):
            db.execute("INSERT INTO links VALUES (?,?,'refers_to')", (f["id"], target))
        for n, text in enumerate(chunks(f.get("title") or f["id"], d.body)):
            rows.append((f["id"], n, text))

    vectors = embed_documents([text for _, _, text in rows])
    for (doc_id, n, text), vec in zip(rows, vectors):
        db.execute("INSERT INTO chunks (doc_id, n, text, vector) VALUES (?,?,?,?)", (doc_id, n, text, vec.tobytes()))
    db.execute("INSERT INTO chunks_fts (rowid, text) SELECT rowid, text FROM chunks")
    links = db.execute("SELECT COUNT(*) FROM links").fetchone()[0]
    db.commit()
    db.close()
    return len(current), len(rows), links


def main() -> int:
    units, n_chunks, links = build()
    print(f"{INDEX}: {units} units, {n_chunks} chunks, {links} links")
    return 0


if __name__ == "__main__":
    sys.exit(main())
