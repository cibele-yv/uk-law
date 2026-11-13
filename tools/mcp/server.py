"""MCP server: returns evidence from the knowledge base, never generated prose.

Usage: python -m tools.mcp.server            (stdio, for Claude Desktop / IDEs)

The calling application's LLM reads the evidence and writes the answer, so this
server costs nothing to run and every fact it returns is verbatim source text
with its URL, version date and hash. Build the index first:
python -m tools.index.build
"""
from functools import lru_cache

from mcp.server.mcpserver import MCPServer

from tools.retrieve.search import Index, nation_codes

INSTRUCTIONS = """\
UK law knowledge base (England and Wales unless stated). Every result is verbatim
text from an official source with its URL and the date the version took effect:
legislation (binding law, legislation.gov.uk), Sentencing Council guidelines (courts
must follow them unless unjust), the Highway Code (level "code": not an offence to
break in itself, but courts may rely on it) or GOV.UK guidance (plain-English
explanation, not law). All under the Open Government Licence v3.

When answering a user's legal question:
1. Call get_evidence with the user's question (rephrase in legal terms and call
   search again if the first results look off-topic).
2. Answer ONLY from the returned text. Do not add law from memory. Where guidance
   and legislation differ, the legislation wins; say so.
3. Cite the url of every source you rely on, and quote the words you rely on.
4. State the "as at" date (valid_from) and say if unapplied_changes > 0: the text
   may not yet show recent amendments.
5. If no returned source answers the question, say so plainly; do not guess.
   Where a person lives matters: England, Wales, Scotland and Northern Ireland differ.
   Pass `nation` when you know it; if you do not and it could change the answer, ask,
   or state that you are assuming England and Wales. Never apply England and Wales
   rules to Scotland or Northern Ireland. A source whose extent_basis is "assumed" does
   not say where it applies (its extent_evidence is empty): say that, do not present
   its territory as certain.
6. Say this is legal information, not legal advice, and suggest a solicitor or
   Citizens Advice for their specific situation.
"""

server = MCPServer(name="uk-law", instructions=INSTRUCTIONS)


def _note(nation: str | None, hits: list) -> str:
    """A caution for the calling model about where the sources apply."""
    count = len(hits)
    assumed = [h.id for h in hits if h.extent_basis == "assumed"]
    caution = (
        f" Territory is only ASSUMED (England and Wales) for {len(assumed)} of these sources "
        "(extent_basis \"assumed\"): they do not state where they apply, so say so rather than treat them as certain."
        if assumed else ""
    )
    if nation is None or not nation.strip():
        return ("No nation was given, so England and Wales are assumed. Some rules differ in Wales "
                "(see each source's extent). If the person's location could change the answer, ask "
                "which nation they are in." + caution)
    if nation_codes(nation) & {"S", "NI"}:
        return ("This knowledge base is built for England and Wales. Scotland and Northern Ireland have "
                "separate courts and rules and are only partly covered: say so, and do not apply "
                "England and Wales rules to them." + caution)
    return ("" if count else "Nothing found for this nation: say so.") + caution


@lru_cache(maxsize=1)
def _index() -> Index:
    return Index()


@server.tool()
def get_evidence(question: str, nation: str | None = None, k: int = 6, k_guidance: int = 3,
                 k_guidelines: int = 3, k_code: int = 2) -> dict:
    """Best sources for a plain-English legal question: the top k law provisions
    (Acts, SIs, Criminal Procedure Rules), the top k_guidelines Sentencing Council guidelines,
    the top k_code Highway Code sections and the top k_guidance GOV.UK guidance pages, plus what they
    refer to (one step). Use this first. Law decides the answer; guidelines and the
    Highway Code show how courts apply it; guidance explains it.

    `nation` (England, Wales, Scotland or Northern Ireland) keeps only sources that apply
    there; leave it out if unknown (England and Wales are then assumed)."""
    try:
        codes = nation_codes(nation)
    except ValueError as e:
        return {"error": str(e)}
    hits = _index().evidence(question, k, k_guidance, k_guidelines, k_code, codes)
    return {
        "question": question,
        "nation": nation or "not given: England and Wales assumed",
        "count": len(hits),
        "note": _note(nation, hits),
        "sources": [h.to_dict() for h in hits],
    }


@server.tool()
def search(query: str, nation: str | None = None, k: int = 8) -> dict:
    """Keyword + meaning search over all provisions that apply in `nation` (default England
    and Wales). Returns the best excerpt of each."""
    try:
        codes = nation_codes(nation)
    except ValueError as e:
        return {"error": str(e)}
    hits = _index().search(query, k, codes=codes)
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
