"""Parse one raw GOV.UK Content API snapshot into a Provision. No file writing here.

The page's HTML is turned into Markdown, keeping headings, lists, tables and
emphasis. Links become `relations.cites` when they point at a unit we hold
(a legislation provision or another GOV.UK page listed in an area file).
"""
import json
import re

from lxml import html

from tools.normalise.clml import Provision

# GOV.UK's Content API has no territorial extent field. Our scope is England
# and Wales; pages that differ elsewhere usually say so in the text.
EXTENT = ["E", "W"]
BLOCK = {"p", "div", "section", "blockquote", "address"}
SKIP = {"script", "style", "nav", "button", "svg", "img"}


def _clean(s: str) -> str:
    return re.sub(r"[ \t\r\n ]+", " ", s)


class _Md:
    """Small HTML -> Markdown renderer for GOV.UK 'govspeak' output."""

    def __init__(self) -> None:
        self.links: list[str] = []
        self.unhandled: set[str] = set()

    def inline(self, e) -> str:
        out = [_clean(e.text or "")]
        for c in e:
            tag = c.tag if isinstance(c.tag, str) else ""
            if tag in SKIP:
                pass
            elif tag == "a":
                if c.get("href"):
                    self.links.append(c.get("href"))
                out.append(self.inline(c))
            elif tag in ("strong", "b"):
                text = self.inline(c).strip()
                out.append(f"**{text}**" if text else "")
            elif tag in ("em", "i"):
                text = self.inline(c).strip()
                out.append(f"*{text}*" if text else "")
            elif tag == "br":
                out.append("\n")
            else:
                out.append(self.inline(c))
            out.append(_clean(c.tail or ""))
        return "".join(out)

    def blocks(self, e, depth: int = 0) -> list[str]:
        out: list[str] = []
        if e.text and e.text.strip():
            out.append(_clean(e.text).strip())
        for c in e:
            tag = c.tag if isinstance(c.tag, str) else ""
            if tag in SKIP or not tag:
                pass
            elif re.fullmatch(r"h[1-6]", tag):
                level = max(2, min(int(tag[1]) + 1, 6))  # page title is the only level-1 heading
                out.append("#" * level + " " + self.inline(c).strip())
            elif tag in ("ul", "ol"):
                out.append(self.list(c, tag == "ol", depth))
            elif tag == "table":
                out.append(self.table(c))
            elif tag in BLOCK:
                has_blocks = any(isinstance(x.tag, str) and (x.tag in BLOCK or x.tag in ("ul", "ol", "table") or re.fullmatch(r"h[1-6]", x.tag)) for x in c)
                if has_blocks:
                    out += self.blocks(c, depth)
                else:
                    text = self.inline(c).strip()
                    if text:
                        out.append(text)
            else:
                text = self.inline(c).strip()
                if text:
                    if tag not in ("span", "abbr", "a", "strong", "em", "b", "i", "code", "small"):
                        self.unhandled.add(tag)
                    out.append(text)
            if c.tail and c.tail.strip():
                out.append(_clean(c.tail).strip())
        return [b for b in out if b]

    def list(self, e, ordered: bool, depth: int) -> str:
        lines = []
        for i, li in enumerate((x for x in e if x.tag == "li"), 1):
            marker = f"{i}." if ordered else "-"
            nested = [x for x in li if x.tag in ("ul", "ol")]
            for n in nested:
                li.remove(n)
            lines.append("  " * depth + f"{marker} " + " ".join(self.blocks(li, depth + 1)).strip())
            for n in nested:
                lines.append(self.list(n, n.tag == "ol", depth + 1))
        return "\n".join(lines)

    def table(self, e) -> str:
        rows = [[self.inline(td).strip().replace("|", "\\|") for td in tr if td.tag in ("td", "th")] for tr in e.iter("tr")]
        rows = [r for r in rows if r]
        if not rows:
            return ""
        width = max(len(r) for r in rows)
        rows = [r + [""] * (width - len(r)) for r in rows]
        lines = ["| " + " | ".join(rows[0]) + " |", "|" + " --- |" * width]
        lines += ["| " + " | ".join(r) + " |" for r in rows[1:]]
        return "\n".join(lines)

    def render(self, fragment: str) -> str:
        if not fragment or not fragment.strip():
            return ""
        root = html.fragment_fromstring(fragment, create_parent="div")
        return "\n\n".join(self.blocks(root))


def link_target(href: str) -> str | None:
    """Unit ID a link points at, if it is legislation or a GOV.UK page."""
    m = re.search(r"legislation\.gov\.uk/(?:id/)?((?:ukpga|uksi|asp|anaw|nisi|ukla)/\d{4}/\d+(?:/[a-z]+/[0-9A-Za-z]+)?)", href)
    if m:
        return m.group(1)
    m = re.match(r"(?:https?://www\.gov\.uk)?/([a-z0-9][a-z0-9-]*)(?:[/#?]|$)", href)
    if m and not href.startswith("//"):
        return f"govuk/{m.group(1)}"
    return None


def parse(raw: bytes, uri: str, level: str = "guidance", known: set[str] | None = None) -> Provision:
    doc = json.loads(raw)
    details = doc.get("details", {})
    md = _Md()
    sections: list[str] = []
    if doc.get("description"):
        sections.append(_clean(doc["description"]).strip())
    if details.get("body"):
        sections.append(md.render(details["body"]))
    for part in details.get("parts", []):
        sections.append(f"## {part.get('title', '').strip()}\n\n{md.render(part.get('body', ''))}")
    text = "\n\n".join(s for s in sections if s).strip()

    cites = set()
    for href in md.links:
        target = link_target(href)
        if target and target != uri and (known is None or target in known):
            cites.add(target)

    review = []
    if md.unhandled:
        review.append(f"unhandled HTML elements: {', '.join(sorted(md.unhandled))}")
    version = (doc.get("updated_at") or "")[:10]
    return Provision(
        id=uri,
        title=doc.get("title") or uri,
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
        binding="guidance",
    )
