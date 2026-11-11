"""Split a provision's text into search-sized chunks.

Short provisions stay whole. Long ones (schedules, tables) are cut at paragraph
boundaries so each chunk stays readable on its own. Every chunk starts with the
provision title so a chunk taken out of context still says where it comes from.
"""

MAX_CHARS = 1500


def chunks(title: str, body: str, max_chars: int = MAX_CHARS) -> list[str]:
    head = f"{title}\n\n"
    if len(body) <= max_chars:
        return [head + body]
    out: list[str] = []
    current = ""
    for para in body.split("\n\n"):
        if current and len(current) + len(para) + 2 > max_chars:
            out.append(head + current)
            current = ""
        current = f"{current}\n\n{para}" if current else para
    if current:
        out.append(head + current)
    return out
