"""Fetch legislation.gov.uk units listed in an area file and save them to raw/.

Usage: python tools/fetch/legislation.py [areas/road-traffic.yaml]

Each unit is saved as raw/legislation/<id>/current.xml, exactly as served.
An identical re-fetch (same SHA-256) is not saved again. Set UKLAW_CONTACT
to add contact details to the User-Agent, as legislation.gov.uk asks.
"""
import hashlib
import os
import sys
import time
from pathlib import Path

import httpx
import yaml
from lxml import etree

DC_TITLE = "{http://purl.org/dc/elements/1.1/}title"
DELAY = 5  # seconds between requests, per legislation.gov.uk robots.txt
RAW = Path("raw/legislation")


def user_agent() -> str:
    contact = os.environ.get("UKLAW_CONTACT")
    return f"uk-law-kb (contact: {contact})" if contact else "uk-law-kb"


def fetch(client: httpx.Client, uri: str, date: str | None = None) -> dict:
    """Fetch one unit. Returns a result dict; never raises on HTTP errors."""
    url = f"https://www.legislation.gov.uk/{uri}" + (f"/{date}" if date else "") + "/data.xml"
    result = {"id": uri, "url": url, "status": None}
    r = None
    for attempt in (1, 2):  # one retry on network errors
        try:
            r = client.get(url)
            break
        except httpx.HTTPError as e:
            result["error"] = f"{type(e).__name__}: {e}"
            if attempt == 1:
                time.sleep(DELAY)
    if r is None:
        result["outcome"] = "FAILED"
        return result
    result["status"] = r.status_code
    result.pop("error", None)
    if r.status_code != 200:
        result["outcome"] = "FAILED"
        return result

    try:
        root = etree.fromstring(r.content)
    except etree.XMLSyntaxError as e:
        result.update(outcome="FAILED", error=f"invalid XML: {e}")
        return result

    title = root.findtext(f".//{DC_TITLE}")
    digest = hashlib.sha256(r.content).hexdigest()
    out = RAW / uri / f"{date or 'current'}.xml"
    result.update(title=title, sha256=digest, path=str(out))

    if out.exists() and hashlib.sha256(out.read_bytes()).hexdigest() == digest:
        result["outcome"] = "unchanged"
        return result

    changed = out.exists()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(r.content)
    # A new hash for an existing file is a silent source change: flag it.
    result["outcome"] = "CHANGED (review)" if changed else "saved"
    return result


def main(area_file: str) -> int:
    area = yaml.safe_load(Path(area_file).read_text(encoding="utf-8"))
    units = [u["id"] for u in area["units"] if u["id"].split("/")[0] in ("ukpga", "uksi", "asp", "anaw", "nisi", "ukla")]
    failures = 0
    with httpx.Client(headers={"User-Agent": user_agent()}, timeout=90, follow_redirects=True) as client:
        for i, uri in enumerate(units):
            if i:
                time.sleep(DELAY)
            res = fetch(client, uri)
            print(f"{res['outcome']:<17} {uri}  [{res['status']}]  {res.get('title') or res.get('error', '')}")
            if res["outcome"] == "FAILED":
                failures += 1
    print(f"\n{len(units) - failures}/{len(units)} units fetched")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "areas/road-traffic.yaml"))
