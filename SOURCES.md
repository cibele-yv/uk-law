# Sources

| Source | Used for | Access | Licence | Refresh |
|---|---|---|---|---|
| legislation.gov.uk | Acts, SIs (incl. Criminal Procedure Rules 2025), explanatory notes (not yet) | `/data.xml` on any URL, 5 s between requests | Open Government Licence v3 | Monthly |
| GOV.UK Content API | Guidance pages; the Highway Code (`level: code`, `binding: evidential`, RTA 1988 s.38(7)) | `www.gov.uk/api/content/<path>`, 1 s between requests. Version = `updated_at` date (`public_updated_at` only moves on major changes) | Open Government Licence v3 | Monthly |
| Sentencing Council | Magistrates' court guidelines and supplementary information (fine bands, disqualification) | HTML pages `sentencingcouncil.org.uk/<path>/`, 2 s between requests; text of `<main>` only. Version = "last updated" date, else "effective from" | Open Government Licence v3, Crown copyright (site terms, "Re-using content", checked 12 Nov 2026). Must be acknowledged as Crown copyright with the source title | Monthly |

Normaliser design (extent mapping, paragraph layout) follows i-dot-ai/lex (MIT licence, Copyright (c) 2025 i.AI). The code is rewritten on lxml, not copied; lex is not a dependency.

Refresh is monthly, plus a manual run whenever a new law or a change in a listed unit is known. Between refreshes an answer can be up to a month behind legislation.gov.uk, so answers should show the version date of the text they cite.

GOV.UK pages are guidance (`binding: guidance`), not law. They are kept because they use the same plain words people use in questions, and search returns them alongside, never instead of, the legislation. The Content API has no territorial extent field, so pages are recorded as England and Wales, the scope of this knowledge base.

Sentencing Council: the site's terms license its content under the Open Government Licence v3 and ask that it be acknowledged as Crown copyright with the title of the source; every data file records the publisher as "Sentencing Council for England and Wales (Crown copyright)", its title and URL. Third-party material on the site is excluded from the licence; none is used here. The site's robots.txt allows general crawling and declares `ai-train=no`: this project stores and cites the text for retrieval and does not train models on it. Guidelines are recorded as `binding: binding` because courts must follow them unless that would be contrary to the interests of justice (Sentencing Code s.59).
