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

### Try it in Claude Desktop (as a new user)

1. Install Python 3.12+ and Claude Desktop.
2. Clone and build (the first build downloads a ~70 MB search model and takes about 2 minutes):
   ```
   git clone https://github.com/cibele-yv/uk-law.git
   cd uk-law
   pip install -e ".[search]"
   python -m tools.index.build
   ```
3. Open `%APPDATA%\Claude\claude_desktop_config.json` (create it if missing; or Claude Desktop >
   Settings > Developer > Edit Config) and add, with your own paths:
   ```json
   {
     "mcpServers": {
       "uk-law": {
         "command": "C:\Python313\python.exe",
         "args": ["-m", "tools.mcp.server"],
         "env": { "PYTHONPATH": "C:\path\to\uk-law" }
       }
     }
   }
   ```
   `command` must be the Python where step 2 installed the packages (`where python`). On macOS/Linux
   use the `python3` path and a `/path/to/uk-law` PYTHONPATH.
4. Quit Claude Desktop completely (tray icon > Quit) and reopen it. In a new chat, the tools icon
   should list `uk-law`. Ask, for example: *"I have an £800 fine and a court summons for missing a
   speeding payment deadline. What are my options?"* and check that the answer cites the URLs the
   tool returned.

Tools: `get_evidence(question)`, `search(query)`, `get_provision(id)`, `get_related(id)`.
This is legal information, not legal advice.
