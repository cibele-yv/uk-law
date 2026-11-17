"""Check the MCP server's nation handling without a model: coverage warnings and nation filtering.

Usage: python -m tools.evaluate.server        (exit code 1 if any check fails)
"""
import sys

from tools.mcp import server


def ids(question: str, nation: str | None) -> set[str]:
    return {s["id"] for s in server.get_evidence(question, nation)["sources"]}


def checks():
    for nation in (None, "England", "Wales", "England and Wales"):
        yield f"{nation or 'no nation'}: full coverage", server.get_evidence("drink drive limit", nation)["coverage"] == "full"
    for nation, word in (("Scotland", "SCOTLAND"), ("Northern Ireland", "NORTHERN IRELAND"), ("ni", "NORTHERN IRELAND")):
        r = server.get_evidence("drink drive limit", nation)
        yield f"{nation}: warning comes first", list(r)[:2] == ["coverage", "warning"]
        yield f"{nation}: partial coverage naming the nation", r["coverage"] == "partial" and word in r["warning"]
        yield f"{nation}: search warns too", server.search("drink drive limit", nation)["coverage"] == "partial"
    q = "What is the drink drive limit?"
    yield "Scotland gets the Scottish limit", "ssi/2014/328/regulation/2" in ids(q, "Scotland")
    yield "England does not get the Scottish limit", "ssi/2014/328/regulation/2" not in ids(q, "England")
    yield "Northern Ireland gets its own Order", "nisi/1995/2994/article/16" in ids(q, "Northern Ireland")
    yield "Wales does not get the Northern Ireland Order", "nisi/1995/2994/article/16" not in ids(q, "Wales")
    yield "unknown nation is an error", "error" in server.get_evidence("speed limit", "France")


def main() -> int:
    failed = 0
    for name, ok in checks():
        print(("PASS  " if ok else "FAIL  ") + name)
        failed += not ok
    print(f"\n{failed} failed" if failed else "\nall passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
