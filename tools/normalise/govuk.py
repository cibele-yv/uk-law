"""Parse one raw GOV.UK Content API snapshot into a Provision. No file writing here.

The page's HTML is turned into Markdown, keeping headings, lists, tables and
emphasis. Links become `relations.cites` when they point at a unit we hold
(a legislation provision or another GOV.UK page listed in an area file).
"""
import json

from tools.normalise.clml import Provision
from tools.normalise.htmlmd import Markdown, clean
from tools.normalise.linkmap import unit_for

# GOV.UK's Content API has no territorial extent field. Our scope is England
# and Wales; pages that differ elsewhere usually say so in the text.
EXTENT = ["E", "W"]


# The Highway Code is a code, not guidance: breaking it is not an offence in itself,
# but courts may rely on it to establish liability (Road Traffic Act 1988 s.38(7)).
HIGHWAY_CODE = "govuk/guidance/the-highway-code"


def kind(uri: str) -> tuple[str, str, str | None]:
    """(level, binding, title prefix) for a GOV.UK unit."""
    if uri.startswith(HIGHWAY_CODE):
        return "code", "evidential", "The Highway Code"
    return "guidance", "guidance", None


def parse(raw: bytes, uri: str, known: set[str] | None = None) -> Provision:
    doc = json.loads(raw)
    details = doc.get("details", {})
    md = Markdown()
    sections: list[str] = []
    if doc.get("description"):
        sections.append(clean(doc["description"]).strip())
    if details.get("body"):
        sections.append(md.render(details["body"]))
    for part in details.get("parts", []):
        sections.append(f"## {part.get('title', '').strip()}\n\n{md.render(part.get('body', ''))}")
    text = "\n\n".join(s for s in sections if s).strip()

    cites = {t for href in md.links if (t := unit_for(href, known)) and t != uri}
    level, binding, prefix = kind(uri)
    title = doc.get("title") or uri
    if prefix and not title.startswith(prefix):
        title = f"{prefix}: {title}"

    review = []
    if md.unhandled:
        review.append(f"unhandled HTML elements: {', '.join(sorted(md.unhandled))}")
    version = (doc.get("updated_at") or "")[:10]
    return Provision(
        id=uri,
        title=title,
        level=level,
        parent=None,
        extent=EXTENT,
        valid_from=version,
        status="in-force",
        unapplied_changes=0,
        cites=sorted(cites),
        snapshot=version,
        text=text,
        review=review,
        binding=binding,
    )
