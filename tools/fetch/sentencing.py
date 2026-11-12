"""HTTP access to sentencingcouncil.org.uk. Knows nothing about areas or storage.

Unit IDs are the page path with a 'sentencing/' prefix:
  sentencing/guidelines/speeding-revised-2017
  sentencing/supplementary-information/approach-to-fines

Content is Crown copyright under the Open Government Licence v3 (site terms and
conditions, 'Re-using content'); it must be acknowledged as Crown copyright with
the title of the source. The site's robots.txt allows general crawling and
signals ai-train=no: we store and cite the text, we do not train models on it.
"""
import re
import time
from datetime import datetime, timezone

import httpx
from lxml import html

from tools.fetch.legislation import Fetched, user_agent

BASE = "https://www.sentencingcouncil.org.uk"
PREFIX = "sentencing"
EXT = ".html"
DELAY = 2  # seconds between requests
SOURCE = {
    "publisher": "Sentencing Council for England and Wales (Crown copyright)",
    "format": "HTML",
    "licence": "OGL-3.0",
}
MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"], 1)}


def handles(uri: str) -> bool:
    return uri.split("/")[0] == PREFIX


def page_url(uri: str) -> str:
    return f"{BASE}/{uri.split('/', 1)[1]}/"


def main_content(content: bytes):
    """The guideline itself: the page's <main> element, or None."""
    found = html.fromstring(content).xpath("//main")
    return found[0] if found else None


def canonical(content: bytes) -> bytes:
    """Compare pages on the visible text of <main> only: the rest of the page
    (navigation, form tokens, scripts) changes on every request."""
    main = main_content(content)
    if main is None:
        return content
    for e in main.xpath(".//script|.//style|.//form|.//input"):
        e.drop_tree()
    return re.sub(r"\s+", " ", main.text_content()).strip().encode("utf-8")


def _iso(day: str, month: str, year: str) -> str | None:
    m = MONTHS.get(month.lower())
    return f"{int(year):04d}-{m:02d}-{int(day):02d}" if m else None


def version_date(content: bytes) -> str | None:
    """'Effective from 24 April 2017 (last updated on 5 October 2026)': the last
    update if given, else the effective date."""
    main = main_content(content)
    text = re.sub(r"\s+", " ", main.text_content() if main is not None else "")
    m = re.search(r"last updated on (\d{1,2}) (\w+) (\d{4})", text) or re.search(r"Effective from:? (\d{1,2}) (\w+) (\d{4})", text)
    return _iso(*m.groups()) if m else None


class SentencingClient:
    def __init__(self) -> None:
        self._http = httpx.Client(headers={"User-Agent": user_agent()}, timeout=60, follow_redirects=True)
        self._last = 0.0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self._http.close()

    def _wait(self) -> None:
        pause = self._last + DELAY - time.monotonic()
        if pause > 0:
            time.sleep(pause)
        self._last = time.monotonic()

    def get(self, uri: str) -> Fetched:
        """Fetch one guideline page; retry once on network errors. Never raises."""
        url = page_url(uri)
        res = Fetched(uri, url)
        for _ in (1, 2):
            self._wait()
            try:
                r = self._http.get(url)
            except httpx.HTTPError as e:
                res.error = f"{type(e).__name__}: {e}"
                continue
            res.error, res.status, res.content = None, r.status_code, r.content
            break
        if res.status is not None and res.status != 200:
            res.error = f"HTTP {res.status}"
        elif res.ok:
            main = main_content(res.content)
            if main is None:
                res.error = "no <main> element: page layout changed"
                return res
            h1 = main.xpath(".//h1")
            res.title = re.sub(r"\s+", " ", h1[0].text_content()).strip() if h1 else None
            # Some supplementary pages show no date at all. Use the day we retrieved the
            # page; the normaliser flags those units for review. A new version file is
            # only written if the text changes (see canonical).
            res.version = version_date(res.content) or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return res
