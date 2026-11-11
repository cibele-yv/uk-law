# uk-law

Verified, versioned UK law for AI retrieval. Every unit is verbatim text from an official source, with its source URL, fetch time, version dates and SHA-256 hash, so any answer can be traced back to the publisher.

## Source levels

1. Acts (primary legislation)
2. Statutory instruments (regulations, orders, rules)
3. Rules and codes made under an Act (Highway Code, sentencing guidelines)
4. Guidance (GOV.UK, DVLA)
5. Case law (later)

## Scope

Only **road traffic** is covered for now. See `areas/road-traffic.yaml` for the units, `schema/provision.schema.json` for the metadata schema and `SOURCES.md` for sources and licences.

## Pipeline

```
python -m tools.fetch.run         # download changed units into raw/ (versioned, never overwritten)
python -m tools.normalise.run     # raw XML -> data/ Markdown with front matter
python -m tools.validate.run      # schema, hashes, links, dates, coverage
```

## Search and MCP server

Answers come from search, not from a model: the question is matched against every unit
(keyword + meaning, using a small free model that runs locally), and the provisions they
refer to are added. The MCP server returns that evidence, verbatim and with source URLs;
the calling application's LLM writes the answer, so the server costs nothing to run.

```
pip install -e ".[search]"
python -m tools.index.build       # data/ -> index/kb.sqlite (rebuilt from scratch, not committed)
python -m tools.evaluate.run      # do test questions find their expected sources?
python -m tools.mcp.server        # MCP server over stdio
```

To use it from Claude Desktop, add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "uk-law": {
      "command": "python",
      "args": ["-m", "tools.mcp.server"],
      "cwd": "C:/path/to/uk-law"
    }
  }
}
```

Tools: `get_evidence(question)`, `search(query)`, `get_provision(id)`, `get_related(id)`.
This is legal information, not legal advice.
