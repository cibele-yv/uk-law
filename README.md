# uk-law

Verified, versioned UK law for AI retrieval. Every unit is verbatim text from an official source, with its source URL, fetch time, version dates and SHA-256 hash, so any answer can be traced back to the publisher.

**Coverage: road traffic law only.** England and Wales are covered most fully (legislation, Criminal Procedure Rules, Sentencing Council guidelines, Highway Code, GOV.UK guidance). **Scotland and Northern Ireland are covered in part, from legislation only**: the offences, penalty points, disqualification, fixed penalties and court procedure on fines and appeals, but not sentencing guidance (so no usual fine amounts), court rules, or plain-English guidance. A question for either nation gets a "partial coverage" warning first, which the calling model must pass on.

## Source levels

1. Acts (primary legislation)
2. Statutory instruments (regulations, orders, rules)
3. Rules and codes made under an Act (Highway Code, sentencing guidelines)
4. Guidance (GOV.UK, DVLA)
5. Case law (later)

## Scope

Only the **road traffic** area exists so far (`areas/road-traffic.yaml`, 220 units), but the design is not tied to one area or one nation: every unit records where it applies (`extent`: E, W, S, NI) and how we know (`extent_basis`: `stated` by the source, or `assumed`). Without a nation, England and Wales is assumed and the answer says so.

| Nation | Units that apply | What is there | What is missing |
|---|---|---|---|
| England | most of them | Everything | Topic gaps only |
| Wales | all of England's, plus the 20 mph order | Same as England | Topic gaps only |
| Scotland | the Great Britain Acts, plus 14 Scottish units | Offences, points, disqualification, fixed penalties, Highway Code, time limits, fines and appeals (Criminal Procedure (Scotland) Act 1995), the Scottish drink drive limit | Scottish sentencing guidance, court rules, plain-English guidance |
| Northern Ireland | 67 units from its own Orders | Offences, points, disqualification, fixed penalties, speed limits, insurance, new drivers, fines and appeals (Magistrates' Courts (Northern Ireland) Order 1981) | Sentencing guidance, court rules, a Northern Ireland Highway Code, plain-English guidance |

The extent fields and the nation filter keep each nation's law apart: a Northern Irish Order is never returned to a question about England, and the reverse.

Not yet included: case law (level 5), explanatory notes, DVLA guidance, other areas of law.

Schema: `schema/provision.schema.json`. Sources and licences: `SOURCES.md`.

### What each unit records

`id`, `title`, `level`, `binding` (`binding` = legislation and Sentencing Council guidelines; `evidential` = Highway Code; `guidance` = GOV.UK), `extent`, `extent_basis`, `extent_evidence` (quoted sentence), `areas`, `version` (valid from, retrieved), `unapplied_changes` (amendments not yet applied to the text), `parent`, `made_under`, `relations` (`amended_by`, `cites`, `interprets`) and `source` (URL, publisher, retrieval time, SHA-256, licence).

Territory of GOV.UK, Highway Code and Sentencing Council pages is never guessed from the text; it is recorded in `curation/extent.yaml` only where the source states it. Instruments served "as made" (e.g. Welsh `wsi`) take their version date from the coming-into-force date and their extent from the legislature that made them (`assumed`, flagged for review). The fetcher and normaliser recognise `ukpga`, `uksi`, `wsi`, `asc`, `ssi`, `nia` and `nisr`.

## Review status

Nothing is legal advice and not everything is human-checked. `python -m tools.validate.run` flags units for review (tables, schedules, pages with no publication date). All test questions in `tests/road-traffic/questions.yaml` are still `verified: false` drafts. The monthly refresh opens a pull request for a person to review.

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
python -m tools.index.build       # data/ -> index/kb.sqlite (rebuilt from scratch, not committed; Act titles for cross-Act links come from raw/)
python -m tools.evaluate.run      # do test questions find their expected sources? (recall at k=6; questions may name a nation)
python -m tools.evaluate.server   # nation handling: coverage warnings and nation filtering
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
         "command": "C:\\Python313\\python.exe",
         "args": ["-m", "tools.mcp.server"],
         "env": { "PYTHONPATH": "C:\\path\\to\\uk-law" }
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

Tools: `get_evidence(question, nation)`, `search(query, nation)`, `get_provision(id)`, `get_related(id)`. `nation` (England, Wales, Scotland or Northern Ireland) keeps only sources that apply there; without it England and Wales are assumed and the answer should say so. For Scotland or Northern Ireland the response starts with `"coverage": "partial"` and a warning, saying what is and is not covered, that the calling model must give the person first. England, Wales and no nation return `"coverage": "full"`.

Results include `extent_basis` and `extent_evidence`, and the server tells the calling model to say when a territory is only assumed. The server loads the index into memory and finds it regardless of working directory. Rebuild the index after any schema change (an old index fails with `KeyError: extent_basis`), then restart the MCP client to load it.
This is legal information, not legal advice.
