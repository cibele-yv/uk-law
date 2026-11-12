"""Parse one raw Sentencing Council page into a Provision. No file writing here.

Page layout (checked November 2026): <main> holds a header block (h1 title, a
line naming the Act and section, 'Effective from ... (last updated on ...)')
and the guideline body. Collapsible sections are a <button> (the heading) next
to a hidden <div> (the text); hidden text is part of the guideline, so it is kept.
Navigation, the feedback form and print/bookmark controls are dropped.
"""
import copy
import re

from lxml import html

from tools.fetch.sentencing import main_content, version_date
from tools.normalise.clml import Provision
from tools.normalise.htmlmd import Markdown, clean
from tools.normalise.linkmap import unit_for

EXTENT = ["E", "W"]  # the Sentencing Council's guidelines apply in England and Wales

# Acts named in a guideline's header line, mapped to legislation IDs, so a guideline
# links to the section that creates the offence ('Road Traffic Act 1988, s.172').
ACTS = {
    "road traffic act 1988": "ukpga/1988/52",
    "road traffic regulation act 1984": "ukpga/1984/27",
    "road traffic offenders act 1988": "ukpga/1988/53",
    "sentencing act 2020": "ukpga/2020/17",
    "magistrates' courts act 1980": "ukpga/1980/43",
}


def offence_sections(line: str) -> list[str]:
    """'Road Traffic Act 1988 ss.14 and 15' -> [ukpga/1988/52/section/14, .../15]."""
    out = []
    for name, act in ACTS.items():
        m = re.search(re.escape(name) + r",?\s*ss?\.\s*([0-9A-Z]+(?:\(\w+\))*(?:\s*(?:,|and|or)\s*[0-9A-Z]+(?:\(\w+\))*)*)", line, re.I)
        if m:
            for num in re.findall(r"(\d+[A-Z]*)(?:\(\w+\))*", m.group(1)):
                out.append(f"{act}/section/{num}")
    return out


def _prepare(main):
    """Copy <main> and turn the site's widgets into plain HTML the renderer understands."""
    main = copy.deepcopy(main)
    for e in main.xpath('.//*[contains(@class,"print:hidden")]|.//form|.//script|.//svg|.//input|.//label'):
        e.drop_tree()
    # Collapsible section: <div class="my-8"><button>Heading</button><div class="hidden">text</div></div>
    for b in main.xpath('.//div[contains(concat(" ", normalize-space(@class), " "), " my-8 ")]/button'):
        b.attrib.clear()
        b.tag = "h3"
    # Inline explanation: <button>Factor</button><div class="hidden">explanation</div>
    for b in main.xpath(".//button"):
        b.tag = "strong"
        b.attrib.clear()
    return main


def parse(raw: bytes, uri: str, known: set[str] | None = None, file_version: str = "") -> Provision:
    main = main_content(raw)
    if main is None:
        raise ValueError("no <main> element: page layout changed")
    main = _prepare(main)
    h1 = main.xpath(".//h1")
    title = clean(h1[0].text_content()).strip() if h1 else uri

    md = Markdown()
    text = md.render(html.tostring(main, encoding="unicode"))
    # The h1 is the title (the renderer makes it '## title'). Everything before it is
    # page furniture ("Magistrates", print/bookmark buttons); the title itself is
    # already in the front matter.
    heading = re.search(r"^##\s+" + re.escape(title) + r"\s*$", text, re.M)
    if heading is None:
        raise ValueError(f"title heading {title!r} not found: page layout changed")
    text = text[heading.end():].strip()

    header = " ".join(clean(p.text_content()) for p in main.xpath(".//h1/following-sibling::p[1]"))
    cites = {t for href in md.links if (t := unit_for(href, known, relative_to="sentencing")) and t != uri}
    cites |= {s for s in offence_sections(header) if known is None or s in known}

    review = []
    if md.unhandled:
        review.append(f"unhandled HTML elements: {', '.join(sorted(md.unhandled))}")
    if "<table" in html.tostring(main, encoding="unicode"):
        review.append("table")  # check the rendered table against the page
    version = version_date(raw)
    if not version:
        version = file_version  # the date we retrieved the page
        review.append("page shows no publication date: version date is the date it was retrieved")
    return Provision(
        id=uri,
        title=f"Sentencing Council guideline: {title}" if "/guidelines/" in uri else f"Sentencing Council: {title}",
        level="guideline",
        parent=None,
        extent=EXTENT,
        valid_from=version,
        status="in-force",
        unapplied_changes=0,
        cites=sorted(cites),
        snapshot=version,
        text=text,
        review=review,
        # Courts must follow sentencing guidelines unless that would be contrary to
        # the interests of justice (Sentencing Code s.59).
        binding="binding",
    )
