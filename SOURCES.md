# Sources

| Source | Used for | Access | Licence | Refresh |
|---|---|---|---|---|
| legislation.gov.uk | Acts, SIs, explanatory notes | `/data.xml` on any URL, 5 s between requests | Open Government Licence v3 | Monthly |
| GOV.UK Content API | Guidance pages (fetched); Highway Code (not yet) | `www.gov.uk/api/content/<path>`, 1 s between requests. Version = `updated_at` date (`public_updated_at` only moves on major changes) | Open Government Licence v3 | Monthly |
| Sentencing Council | Magistrates' sentencing guidelines | HTML pages | To be checked before publishing | Monthly |

Normaliser design (extent mapping, paragraph layout) follows i-dot-ai/lex (MIT licence, Copyright (c) 2025 i.AI). The code is rewritten on lxml, not copied; lex is not a dependency.

Refresh is monthly, plus a manual run whenever a new law or a change in a listed unit is known. Between refreshes an answer can be up to a month behind legislation.gov.uk, so answers should show the version date of the text they cite.

GOV.UK pages are guidance (`binding: guidance`), not law. They are kept because they use the same plain words people use in questions, and search returns them alongside, never instead of, the legislation. The Content API has no territorial extent field, so pages are recorded as England and Wales, the scope of this knowledge base.
