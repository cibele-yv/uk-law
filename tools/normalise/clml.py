"""Parse one raw CLML XML snapshot into a Provision. No file writing here.

Extent mapping follows i-dot-ai/lex (MIT licence, Copyright (c) 2025 i.AI).
"""
import re
from dataclasses import dataclass, field

from lxml import etree

from tools.normalise.render import NS, Renderer, inline

DCT = "{http://purl.org/dc/terms/}"
DC = "{http://purl.org/dc/elements/1.1/}"
UKM = "{http://www.legislation.gov.uk/namespaces/metadata}"
EXTENT = {"E": "E", "W": "W", "S": "S", "N.I.": "NI", "N.I": "NI", "NI": "NI"}
UNIT_KINDS = {"section", "regulation", "article", "rule", "schedule", "paragraph"}


@dataclass
class Provision:
    id: str
    title: str
    level: str
    parent: str | None
    extent: list[str]
    valid_from: str
    status: str
    unapplied_changes: int
    cites: list[str]
    snapshot: str  # dct:valid of the raw file this came from
    text: str
    review: list[str] = field(default_factory=list)


def _nearest(e: etree._Element, attr: str) -> str | None:
    """Value of attr on the element or its closest ancestor that has it."""
    node = e
    while node is not None:
        if node.get(attr):
            return node.get(attr)
        node = node.getparent()
    return None


def _extent(raw: str | None) -> list[str]:
    if not raw:
        return []
    out = [EXTENT.get(tok) for tok in raw.split("+")]
    return [x for x in dict.fromkeys(out) if x]


def _element_id(uri: str) -> str | None:
    """XML id of the unit: section/172 -> 'section-172'; a lone unnumbered schedule -> 'schedule'."""
    parts = uri.split("/")
    if len(parts) >= 5 and parts[-2] in UNIT_KINDS:
        return f"{parts[-2]}-{parts[-1]}"
    if len(parts) == 4 and parts[-1] in UNIT_KINDS:
        return parts[-1]
    return None


def _is_unit(uri: str) -> bool:
    return _element_id(uri) is not None


def _target(root: etree._Element, uri: str) -> etree._Element | None:
    if not _is_unit(uri):
        return root  # whole instrument
    wanted = _element_id(uri)
    for e in root.iter():
        if isinstance(e.tag, str) and e.get("id") == wanted:
            return e
    return None


def _unit_of(path: str) -> str | None:
    """Reduce a legislation.gov.uk id path to a unit id (section level) or the work."""
    parts = path.strip("/").split("/")
    if len(parts) >= 5 and parts[3] in UNIT_KINDS:
        return "/".join(parts[:5])
    return "/".join(parts[:3]) if len(parts) >= 3 else None


def _cites(target: etree._Element, self_id: str) -> list[str]:
    found = set()
    for c in target.iter(NS + "Citation"):
        m = re.search(r"legislation\.gov\.uk/id/(.+)$", c.get("URI", ""))
        if m and (unit := _unit_of(m.group(1))) and unit != self_id:
            found.add(unit)
    return sorted(found)


_KINDS = {"s": "section", "reg": "regulation", "art": "article", "Sch": "schedule"}


def _affected(text: str) -> set[str]:
    """Provisions named by an UnappliedEffect's AffectedProvisions, e.g. 's. 128A(4)', 'Sch. 2 para. 4'."""
    out: set[str] = set()
    pattern = r"\b(s|reg|art|Sch)\. ?((?:\d+[A-Za-z]*(?:\(\w+\))*(?:[ ,]+(?=\d))?)+)"
    for m in re.finditer(pattern, text):
        for tok in re.findall(r"\d+[A-Za-z]*", re.sub(r"\(\w+\)", "", m.group(2))):
            out.add(f"{_KINDS[m.group(1)]}/{tok}")
    return out


def _unapplied(root: etree._Element, uri: str) -> int:
    effects = [e for e in root.iter(UKM + "UnappliedEffect") if e.get("RequiresApplied") != "false"]
    if not _is_unit(uri):
        return len(effects)  # whole instrument: all of them
    parts = uri.split("/")
    key = "/".join(parts[-2:]) if _element_id(uri) != parts[-1] else parts[-1] + "/1"
    return sum(1 for e in effects if key in _affected(e.get("AffectedProvisions", "")))


def _title(root: etree._Element, target: etree._Element, uri: str) -> str:
    if target is root:
        return root.findtext(f".//{DC}title") or uri
    if target.tag == NS + "Schedule":
        number = target.find(NS + "Number")
        label = inline(number).title() if number is not None else ""
        t = target.find(f"{NS}TitleBlock/{NS}Title")
        return f"{label}: {inline(t)}" if t is not None else label
    group = target.getparent()
    t = group.find(NS + "Title") if group is not None else None
    return inline(t) if t is not None else uri


def parse(xml: bytes, uri: str, level: str) -> Provision:
    root = etree.fromstring(xml)
    target = _target(root, uri)
    if target is None:
        raise ValueError(f"{uri}: target element not found in XML")

    review: list[str] = []
    renderer = Renderer()
    if target is root:
        bodies = [c for c in root if isinstance(c.tag, str) and etree.QName(c).localname in ("Primary", "Secondary")]
        text = "\n\n".join(renderer.render(c) for c in bodies)
        review.append("whole instrument, not a single unit")
    else:
        text = renderer.render(target)

    extent = _extent(_nearest(target, "RestrictExtent"))
    if not extent:
        review.append("extent missing")
    valid_from = _nearest(target, "RestrictStartDate") or root.findtext(f".//{DCT}valid")
    status = "prospective" if (_nearest(target, "Status") or "").lower() == "prospective" else "in-force"
    if not text.strip():
        status = "repealed"
        review.append("no text: repealed or empty")
    review.extend(sorted(renderer.flags))

    parts = uri.split("/")
    return Provision(
        id=uri,
        title=_title(root, target, uri),
        level=level,
        parent="/".join(parts[:3]) if _is_unit(uri) else None,
        extent=extent,
        valid_from=valid_from,
        status=status,
        unapplied_changes=_unapplied(root, uri),
        cites=_cites(target, uri),
        snapshot=root.findtext(f".//{DCT}valid"),
        text=text,
        review=review,
    )
