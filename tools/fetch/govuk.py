"""HTTP access to the GOV.UK Content API. Knows nothing about areas or storage.

Unit IDs look like 'govuk/speeding-penalties' (the page path on www.gov.uk).
The API returns JSON with the page's HTML body (or one body per part for a
multi-part guide). Content is Crown copyright under the Open Government Licence v3.
"""
import json
import time

import httpx

from tools.fetch.legislation import Fetched, user_agent

API = "https://www.gov.uk/api/content"
PREFIX = "govuk"
EXT = ".json"
DELAY = 1  # seconds between requests; GOV.UK allows far more, this keeps us polite
SOURCE = {"publisher": "GOV.UK", "format": "GOV.UK Content API JSON", "licence": "OGL-3.0"}


def handles(uri: str) -> bool:
    return uri.split("/")[0] == PREFIX


def page_path(uri: str) -> str:
    return uri.split("/", 1)[1]


def _content(doc: dict) -> dict:
    """The parts of a response that are the page itself (not navigation or link expansions)."""
    d = doc.get("details", {})
    return {
        "title": doc.get("title"),
        "description": doc.get("description"),
        "body": d.get("body"),
        "parts": [{"slug": p.get("slug"), "title": p.get("title"), "body": p.get("body")} for p in d.get("parts", [])],
    }


def canonical(content: bytes) -> bytes:
    """Compare pages on their text only: the API also returns related links and
    timestamps that change without the guidance changing."""
    return json.dumps(_content(json.loads(content)), sort_keys=True, ensure_ascii=False).encode("utf-8")


def version_date(content: bytes) -> str | None:
    """Date of the last edit (updated_at). public_updated_at is only moved for
    'major' changes, so it can be years older than the text actually served."""
    stamp = json.loads(content).get("updated_at")
    return stamp[:10] if stamp else None


class GovukClient:
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
        """Fetch one page as JSON; retry once on network errors. Never raises."""
        url = f"{API}/{page_path(uri)}"
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
            try:
                doc = json.loads(res.content)
            except ValueError as e:
                res.error = f"invalid JSON: {e}"
                return res
            if doc.get("document_type") == "redirect":
                res.error = "page is a redirect; list the page it points to instead"
            elif not (doc.get("details", {}).get("body") or doc.get("details", {}).get("parts")):
                res.error = f"no body text (document_type {doc.get('document_type')})"
            res.title = doc.get("title")
            res.version = version_date(res.content)
            if not res.version and not res.error:
                res.error = "no updated_at date"
        return res
