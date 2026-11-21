"""Split a provision's text into search-sized chunks.

Short provisions stay whole. Long ones (schedules, tables) are cut at paragraph
boundaries, and an over-long table at row boundaries, so each chunk stays readable
on its own. Every chunk starts with the provision title so a chunk taken out of
context still says where it comes from.
"""

MAX_CHARS = 1500


def _split_long(para: str, max_chars: int) -> list[str]:
    """Cut one over-long paragraph (in practice a table) at line breaks. A Markdown table's
    header and separator rows are repeated on every piece so each row keeps its column names."""
    lines = para.split("\n")
    header = ""
    if len(lines) > 2 and lines[0].startswith("|") and set(lines[1].replace("|", "").strip()) <= set("-: "):
        header, lines = "\n".join(lines[:2]), lines[2:]
    pieces: list[str] = []
    current = header
    for line in lines:
        if len(current) + len(line) + 1 > max_chars and current != header:
            pieces.append(current)
            current = header
        current = f"{current}\n{line}" if current else line
    if current != header:
        pieces.append(current)
    return pieces


def chunks(title: str, body: str, max_chars: int = MAX_CHARS) -> list[str]:
    head = f"{title}\n\n"
    if len(body) <= max_chars:
        return [head + body]
    out: list[str] = []
    current = ""
    paras = [piece for para in body.split("\n\n")
             for piece in (_split_long(para, max_chars) if len(para) > max_chars else [para])]
    for para in paras:
        if current and len(current) + len(para) + 2 > max_chars:
            out.append(head + current)
            current = ""
        current = f"{current}\n\n{para}" if current else para
    if current:
        out.append(head + current)
    return out
