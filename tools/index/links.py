"""Find plain-text references to other provisions: of the same Act or instrument, and of
another Act named by its title ("section 14 of the Magistrates' Courts Act 1980").

legislation.gov.uk marks up references to *other* legislation (Citation elements,
already in front matter `relations.cites`), but references inside the same Act are
plain text: "section 75 of this Act", "sections 51 to 54", "Schedule 2".

A reference followed by "of the ..." or "to the ..." names another Act, so
same_act_refs skips it; named_act_refs links it when that Act is in the index. Notes
to the Criminal Procedure Rules cite Acts this way with no Citation markup, so without
this a rule and the sections it implements are not linked. Shorthand such as "the
1988 Act" is not resolved. Only targets that exist in the index become links.
"""
import re

_KIND = {"section": "section", "sections": "section", "regulation": "regulation",
         "regulations": "regulation", "article": "article", "articles": "article",
         "schedule": "schedule", "rule": "rule", "rules": "rule"}
_NUM = r"\d+(?:\.\d+)?[A-Z]*"  # 54, 3ZB, and Criminal Procedure Rules style 29.4
_ITEM = rf"{_NUM}(?:\(\w+\))*"  # 51 or 51(2)(a)
# The list is matched atomically (?>...) so the engine cannot drop the last items
# to dodge the "of the ..." check: "section 28 or 29 of the Road Traffic Act 1988"
# must be skipped whole, not linked as "section 28".
_REF = re.compile(
    rf"\b(sections?|regulations?|articles?|rules?|Schedule)\s+(?>({_ITEM}(?:(?:\s*,\s*|\s+(?:and|or|to)\s+){_ITEM})*))"
    r"(?!\s+(?:of|to)\s+(?:the|that)\b)",
    re.IGNORECASE,
)


def act_of(doc_id: str) -> str:
    """'ukpga/1988/53/section/54' -> 'ukpga/1988/53'."""
    return "/".join(doc_id.split("/")[:3])


def same_act_refs(doc_id: str, text: str, known: set[str]) -> set[str]:
    act = act_of(doc_id)
    found: set[str] = set()
    # Table rows are skipped: offence tables (e.g. RTOA Schedule 2) list sections of
    # other Acts under a heading, so the Act is not on the row and links would be wrong.
    prose = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("|"))
    for m in _REF.finditer(prose):
        kind = _KIND[m.group(1).lower()]
        nums = re.findall(_NUM, re.sub(r"\(\w+\)", "", m.group(2)))
        if " to " in m.group(2) and len(nums) == 2 and nums[0].isdigit() and nums[1].isdigit():
            nums = [str(n) for n in range(int(nums[0]), int(nums[1]) + 1)]
        for n in nums:
            target = f"{act}/{kind}/{n}"
            if target in known and target != doc_id:
                found.add(target)
    return found


_KIND_WORDS = r"sections?|regulations?|articles?|rules?|Schedule"
# The words just before "of the <Act title>": "sections 72(1), ... (6A), 73(1) and 74(2)",
# "section 14 or section 16E". Anchored at the end of the text before the title.
_BEFORE_TITLE = re.compile(
    rf"\b({_KIND_WORDS})\s+((?:{_ITEM}|\(\w+\)|\.\.\.|…|,|\s|\b(?:and|or|to|{_KIND_WORDS})\b)+?)\s*$",
    re.IGNORECASE,
)


def _plain(text: str) -> str:
    return text.replace("’", "'")


def named_act_refs(doc_id: str, text: str, act_titles: dict[str, str], known: set[str]) -> set[str]:
    """Targets of "section N of the <Act title>", for Acts in `act_titles` (act id -> title)."""
    found: set[str] = set()
    prose = _plain("\n".join(line for line in text.splitlines() if not line.lstrip().startswith("|")))
    for act, title in act_titles.items():
        for m in re.finditer(rf"\s+(?:of|to)\s+the\s+{re.escape(_plain(title))}", prose):
            before = _BEFORE_TITLE.search(prose[max(0, m.start() - 200):m.start()])
            if not before:
                continue
            kind = _KIND[before.group(1).lower()]
            for n in re.findall(_NUM, re.sub(r"\(\w+\)", "", before.group(2))):
                target = f"{act}/{kind}/{n}"
                if target in known and target != doc_id:
                    found.add(target)
    return found
