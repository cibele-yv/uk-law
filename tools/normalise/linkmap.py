"""Map a hyperlink to the unit ID it points at, for any source we hold.

  https://www.legislation.gov.uk/ukpga/1988/52/section/172   -> ukpga/1988/52/section/172
  https://www.gov.uk/guidance/the-highway-code/annex-5-penalties
                                                              -> govuk/guidance/the-highway-code/annex-5-penalties
  /penalty-points-endorsements/new-drivers (on GOV.UK)        -> govuk/penalty-points-endorsements
  https://www.sentencingcouncil.org.uk/guidelines/speeding-revised-2017/?source=1
                                                              -> sentencing/guidelines/speeding-revised-2017

A link to part of a page we hold as a whole (a guide part, a subsection) resolves to
the longest known prefix, so it still links to the unit.
"""
import re

LEGISLATION = re.compile(r"legislation\.gov\.uk/(?:id/)?((?:ukpga|uksi|asp|anaw|nisi|ukla)/\d{4}/\d+(?:/[a-z]+(?:/[0-9A-Za-z.]+)?)*)")
GOVUK = re.compile(r"^(?:https?://www\.gov\.uk)?/(?!/)([^?#]+)")
SENTENCING = re.compile(r"sentencingcouncil\.org\.uk/([^?#]+)")


def _longest_known(prefix: str, path: str, known: set[str] | None) -> str | None:
    """prefix + path, cut back to the longest form that is a known unit (any form if known is None)."""
    parts = ([prefix] if prefix else []) + [p for p in path.strip("/").split("/") if p]
    floor = 2 if prefix else 1  # never resolve to the bare source prefix
    if len(parts) < floor:
        return None
    if known is None:
        return "/".join(parts)
    for n in range(len(parts), floor - 1, -1):
        if "/".join(parts[:n]) in known:
            return "/".join(parts[:n])
    return None


def unit_for(href: str, known: set[str] | None = None, relative_to: str = "govuk") -> str | None:
    """Unit ID for a link, or None. `relative_to` says which site a bare /path belongs to."""
    if m := LEGISLATION.search(href):
        return _longest_known("", m.group(1), known)
    if m := SENTENCING.search(href):
        return _longest_known("sentencing", m.group(1), known)
    if href.startswith("/") and relative_to == "sentencing":
        return _longest_known("sentencing", href.split("?")[0].split("#")[0], known)
    if m := GOVUK.match(href):
        return _longest_known("govuk", m.group(1), known)
    return None
