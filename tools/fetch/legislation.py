"""HTTP access to legislation.gov.uk. Knows nothing about areas or storage."""
import os
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
from lxml import etree

from tools.common import paths

BASE = "https://www.legislation.gov.uk"
PREFIXES = {"ukpga", "uksi", "asp", "anaw", "nisi", "ukla"}
DELAY = 5  # seconds between requests, per legislation.gov.uk robots.txt
EXT = ".xml"
SOURCE = {"publisher": "legislation.gov.uk", "format": "CLML XML", "licence": "OGL-3.0"}
DC_TITLE = "{http://purl.org/dc/elements/1.1/}title"
DCT_VALID = "{http://purl.org/dc/terms/}valid"


@dataclass
class Fetched:
    uri: str
    url: str
    status: int | None = None
    content: bytes = b""
    title: str | None = None
    version: str | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.status == 200


def handles(uri: str) -> bool:
    return uri.split("/")[0] in PREFIXES


def canonical(content: bytes) -> bytes:
    """C14N form: legislation.gov.uk varies attribute order between requests."""
    return etree.tostring(etree.fromstring(content), method="c14n")


def raw_dir(uri: str) -> Path:
    return paths.raw_dir(uri)


def version_date(content: bytes) -> str | None:
    """The snapshot's effective date (dct:valid), used to name the saved version."""
    return etree.fromstring(content).findtext(f".//{DCT_VALID}")


def user_agent() -> str:
    contact = os.environ.get("UKLAW_CONTACT")
    return f"uk-law-kb (contact: {contact})" if contact else "uk-law-kb"


class LegislationClient:
    def __init__(self) -> None:
        self._http = httpx.Client(headers={"User-Agent": user_agent()}, timeout=90, follow_redirects=True)
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

    def get(self, uri: str, date: str | None = None) -> Fetched:
        """Fetch one unit's CLML XML; retry once on network errors. Never raises."""
        url = f"{BASE}/{uri}" + (f"/{date}" if date else "") + "/data.xml"
        res = Fetched(uri, url)
        for attempt in (1, 2):
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
            try:
                res.title = etree.fromstring(res.content).findtext(f".//{DC_TITLE}")
                res.version = version_date(res.content)
                if not res.version:
                    res.error = "no dct:valid version date in XML"
            except etree.XMLSyntaxError as e:
                res.error = f"invalid XML: {e}"
        return res
