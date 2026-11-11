"""MCP server: returns evidence from the knowledge base, never generated prose.

Usage: python -m tools.mcp.server            (stdio, for Claude Desktop / IDEs)

The calling application's LLM reads the evidence and writes the answer, so this
server costs nothing to run and every fact it returns is verbatim source text
with its URL, version date and hash. Build the index first:
python -m tools.index.build
"""
from functools import lru_cache

from mcp.server.mcpserver import MCPServer

from tools.retrieve.search import Index

INSTRUCTIONS = """\
UK law knowledge base (England and Wales unless stated). Every result is verbatim
text from an official source (legislation.gov.uk, OGL v3) with its URL and the date
the version took effect.

When answering a user's legal question:
1. Call get_evidence with the user's question (rephrase in legal terms and call
   search again if the first results look off-topic).
2. Answer ONLY from the returned text. Do not add law from memory.
3. Cite the url of every source you rely on, and quote the words you rely on.
4. State the "as at" date (valid_from) and say if unapplied_changes > 0: the text
   may not yet show recent amendments.
5. If no returned source answers the question, say so plainly; do not guess.
6. Say this is legal information, not legal advice, and suggest a solicitor or
   Citizens Advice for their specific situation.
"""

server = MCPServer(name="uk-law", instructions=INSTRUCTIONS)


@lru_cache(maxsize=1)
def _index() -> Index:
    return Index()


@server.tool()
def get_evidence(question: str, k: int = 5) -> dict:
    """Best sources for a plain-English legal question: the top k search hits plus
    the provisions they refer to (one step). Use this first."""
    hits = _index().evidence(question, k)
    return {"question": question, "count": len(hits), "sources": [h.to_dict() for h in hits]}


@server.tool()
def search(query: str, k: int = 8) -> dict:
    """Keyword + meaning search over all provisions. Returns the best excerpt of each."""
    hits = _index().search(query, k)
    return {"query": query, "count": len(hits), "sources": [h.to_dict() for h in hits]}


@server.tool()
def get_provision(id: str) -> dict:
    """Full current text and source details of one provision,
    e.g. 'ukpga/1988/53/section/54'."""
    doc = _index().get(id)
    if doc is None:
        return {"id": id, "found": False, "message": "not in the knowledge base"}
    doc.pop("path", None)
    return {"found": True, **doc}


@server.tool()
def get_related(id: str) -> dict:
    """Provisions this one refers to, and provisions that refer to it."""
    return {"id": id, "related": _index().related(id)}


if __name__ == "__main__":
    server.run()
