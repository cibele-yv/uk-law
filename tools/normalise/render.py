"""Render CLML elements to Markdown text. No metadata logic lives here.

The layout idea (numbered paragraphs indented by level, headings for parts)
follows i-dot-ai/lex's CLML text parser (MIT licence, Copyright (c) 2025
i.AI), rewritten on lxml with tables kept as tables.
"""
import re

from lxml import etree

NS = "{http://www.legislation.gov.uk/namespaces/legislation}"
XHTML = "{http://www.w3.org/1999/xhtml}"

# Elements that carry annotation markers or headings handled elsewhere, not body text.
SKIP = {"CommentaryRef", "FootnoteRef", "Commentaries", "Footnotes", "Pnumber", "Number", "Title", "TitleBlock", "Reference"}
# Elements we know how to render. Anything else is flagged for review.
KNOWN = {
    "Body", "Part", "Chapter", "Pblock", "PblockHeading", "P1group", "P1para", "P2para", "P3para", "P4para", "P5para",
    "Text", "P", "Para", "BlockText", "BlockAmendment", "Schedule", "Schedules", "ScheduleBody", "Tabular", "UnorderedList",
    "OrderedList", "ListItem", "Primary", "Secondary", "Legislation", "Division", "Form",
}
INLINE = {
    "Addition", "Substitution", "Repeal", "Emphasis", "Strong", "Citation", "CitationSubRef", "Acronym", "Abbreviation",
    "Underline", "SmallCaps", "Superior", "Inferior", "Span", "Character", "InlineAmendment", "Definition", "Term",
    "Expanded", "Uppercase", "Image", "Quote", "Heading",
}

OWN = -1  # marker: a paragraph's own text, levelled by the enclosing P-element
Item = tuple[int, str]  # (indent level, markdown line)


def local(e: etree._Element) -> str:
    return etree.QName(e).localname


def inline(e: etree._Element) -> str:
    """Flatten inline markup to text, dropping annotation markers."""
    parts: list[str] = []

    def walk(n: etree._Element) -> None:
        if n.text:
            parts.append(n.text)
        for c in n:
            if isinstance(c.tag, str) and local(c) not in ("CommentaryRef", "FootnoteRef"):
                walk(c)
            if c.tail:
                parts.append(c.tail)

    walk(e)
    text = re.sub(r"\s+", " ", "".join(parts)).strip()
    return text.replace("“ ", "“").replace(" ”", "”")


class Renderer:
    def __init__(self) -> None:
        self.flags: set[str] = set()

    def render(self, e: etree._Element) -> str:
        out: list[str] = []
        for level, line in self._items(e):
            level = max(level, 0)
            if level <= 2 and out:
                out.append("")  # blank line before top-level paragraphs
            out.append("  " * max(level - 2, 0) + line)
        return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()

    # -- internals ---------------------------------------------------------

    def _items(self, e: etree._Element) -> list[Item]:
        if not isinstance(e.tag, str):
            return []
        name = local(e)
        if name in SKIP:
            return []
        if re.fullmatch(r"P\d", name):
            return self._numbered(e, int(name[1:]))
        if e.tag == XHTML + "table":
            return [(0, self._table(e))]
        if name in ("Part", "Chapter", "Pblock", "Schedule"):
            return self._headed(e, name)
        if name == "P1group":  # a section heading; single-unit files carry it in the front matter instead
            title = e.find(NS + "Title")
            head = [(0, f"**{inline(title)}**")] if title is not None and inline(title) else []
            return head + self._children(e)
        if name in ("BlockText", "BlockAmendment"):
            return [(lvl, "> " + line) for lvl, line in self._children(e)]
        if name == "ListItem":
            kids = self._children(e)
            if kids:
                kids[0] = (kids[0][0], "- " + kids[0][1])
            return kids
        if name == "Text" or name in INLINE:
            t = inline(e)
            return [(OWN, t)] if t else []
        if name not in KNOWN:
            self.flags.add(f"unhandled element: {name}")
        kids = self._children(e)
        if not kids and not len(e):
            t = inline(e)
            return [(OWN, t)] if t else []
        return kids

    def _children(self, e: etree._Element) -> list[Item]:
        items: list[Item] = []
        for c in e:
            items.extend(self._items(c))
        return items

    def _numbered(self, e: etree._Element, level: int) -> list[Item]:
        num = e.find(NS + "Pnumber")
        label = inline(num) if num is not None else ""
        if level >= 2 and label:
            label = f"({label})"
        items = [(level if lvl == OWN else lvl, text) for lvl, text in self._children(e)]
        if items and label:
            first_lvl, first = items[0]
            items[0] = (first_lvl, f"{label} {first}")
        elif label:
            items.insert(0, (level, label))
        return items

    def _headed(self, e: etree._Element, name: str) -> list[Item]:
        items: list[Item] = []
        if name == "Schedule":
            self.flags.add("schedule")  # plan: a person reviews every schedule
        else:
            heading = " ".join(
                t for t in (inline(x) for x in e if isinstance(x.tag, str) and local(x) in ("Number", "Title")) if t
            )
            if heading:
                items.append((0, f"### {heading}"))
        items.extend(self._children(e))
        return items

    def _table(self, t: etree._Element) -> str:
        self.flags.add("table")
        rows: list[list[str]] = []
        has_header = False
        for tr in t.iter(XHTML + "tr"):
            cells: list[str] = []
            for cell in tr:
                if not isinstance(cell.tag, str):
                    continue
                text = inline(cell).replace("|", "\\|")
                span = int(cell.get("colspan", "1"))
                if span > 1 or cell.get("rowspan"):
                    self.flags.add("table with merged cells")
                cells.append(text)
                cells.extend([""] * (span - 1))
            rows.append(cells)
            if len(rows) == 1 and tr.find(XHTML + "th") is not None:
                has_header = True
        width = max((len(r) for r in rows), default=0)
        rows = [r + [""] * (width - len(r)) for r in rows]
        if not has_header:
            rows.insert(0, [""] * width)
        out = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * width]
        out += ["| " + " | ".join(r) + " |" for r in rows[1:]]
        return "\n" + "\n".join(out) + "\n"
