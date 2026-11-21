# Spike: sentencing and fine sources for Scotland and Northern Ireland

Question: is there an official, fetchable source for "what is the usual fine" in Scotland and Northern Ireland, like the Sentencing Council guidelines the knowledge base holds for England and Wales? Research only: nothing was built. Done 2026-11-20 from web search results (search result text, not full page reads) plus a check of what `data/` already holds. Items marked **unconfirmed** were not read at source and must be checked before anything is built on them.

## Findings

| | Scotland | Northern Ireland |
|---|---|---|
| Sentencing guideline body | Scottish Sentencing Council (statutory, guidelines approved by the High Court of Justiciary) | No equivalent body found. Guidance is Court of Appeal and Crown Court decisions published on judiciaryni.uk (case law, level 5 in our scheme) |
| Road traffic guidelines published | **Statutory offences of causing death by driving**, in force 16 January 2024 (High Court approved 31 October 2023). Principles and purposes of sentencing, effective 26 November 2018 (from a secondary footnote: **unconfirmed**) | None found as a formal guideline. The Lady Chief Justice's Sentencing Group section exists on judiciaryni.uk but what it holds on road traffic is **unconfirmed** |
| Speeding, no insurance, mobile phone, drink drive (the common questions) | **No Scottish guideline found.** The Council's speeding page is an educational "If you were the judge" case study, not a guideline | Nothing found |
| Plain-English fixed penalty amounts | mygov.scot, safetycameras.gov.scot, Scottish Courts and Tribunals Service: £100 and 3 points for speeding. Sources disagree on the payment period for a police fixed penalty notice (21 days on mygov.scot, 28 days on scotcourts.gov.uk): check the notice | nidirect.gov.uk and justice-ni.gov.uk. **Different from Great Britain:** nidirect describes a £60 conditional offer with 3 points for camera-detected speeding, and fixed penalties of £60 to £200 for endorsable offences; careless driving is £100 and 3 points. All **unconfirmed** at source |
| Reuse licence | Scotland.gov.uk, mygov.scot and Scottish Sentencing Council licences **not checked** | nidirect says its content, except logos, can be reused under the Open Government Licence (confirmed from search result text; read the page before fetching) |
| Statutory maximums (standard scale) | Not in `data/`: no Scottish standard scale or Scottish offence maxima | The NI Order tables of penalties are partly held; the NI fixed penalty amounts are set by an Order that is **not** in `data/` |

## What is already in the knowledge base
- Scotland: 15 units (Criminal Procedure (Scotland) Act 1995 ss.77, 136, 136B, 176, 211-215, 219, 226A, 226C; SSI 2014/328 regs 2-3; SSI 2019/83 reg 2, new in this branch).
- Northern Ireland: 67 units from its own Orders (72 after option 4, below). `nisi/1996/1320/article/59` says the fixed penalty is "such amount as the Department may by order prescribe" or half the maximum fine; the Order that prescribes it was not held when this spike was written; it is now (see Update).

## Why it matters
Nothing in Scotland or Northern Ireland should be answered with the England and Wales figure. The NI speeding conditional offer is reported as £60, not £100, so applying GB amounts to NI would be wrong. The partial-coverage warning and `answer_check` already tell the model to say the usual fine cannot be given; this spike says whether that can change.

## Options, ranked

| # | Option | Gain | Cost | Risk |
|---|---|---|---|---|
| 1 | **Fetch the Scottish death-by-driving guideline** (Scottish Sentencing Council PDF, effective 16 January 2024) | Binding guidance for the most serious driving offences. Covers sections 1, 2B, 3ZB, 3ZC, 3A | Medium. A new publisher, PDF parsing (the fetchers cover legislation.gov.uk, GOV.UK and the Sentencing Council only), licence check | Low legal risk, but serious offences are rare questions |
| 2 | **Fetch NI plain-English pages from nidirect** (fixed penalties for motoring offences; speed limits and penalties) as `guidance` level | Answers "what is the fixed penalty" for NI, the most common question | Low to medium. Same shape as the GOV.UK fetcher; read the Crown copyright page first | Medium: amounts change by Order. Needs `extent: [NI]` recorded and a review flag like GOV.UK |
| 3 | **Fetch the Scottish equivalents** (mygov.scot speeding and fixed penalty pages) | The same for Scotland | Low to medium after #2 | Licence of mygov.scot **unchecked**. The 21 vs 28 day conflict must be preserved, not smoothed over |
| 4 | **Fetch the NI order that prescribes fixed penalty amounts and the Scottish standard scale of fines** from legislation.gov.uk | The legal basis for the amounts | Low. The existing legislation fetcher works | Low |
| 5 | NI Court of Appeal sentencing decisions (judiciaryni.uk) | Real sentencing practice | High. Case law, level 5, which does not exist yet | High. Not binding as a tariff in the way a guideline is |

## Recommendation
Do #4 first (cheap, uses the existing fetcher, gives the legal basis), then #2 and #3 as guidance units with their licences confirmed, then #1. Leave #5 until case law (level 5) is built. None of these gives "the usual fine" the way the Sentencing Council's Band tables do for England and Wales, so even after all of them the partial-coverage warning should stay: Scotland and Northern Ireland would still lack court sentencing guidance for the common offences.

## To do before building (not done here)
1. Open each candidate page and read its licence statement (scottishsentencingcouncil.org.uk, mygov.scot, nidirect.gov.uk, justice-ni.gov.uk).
2. Identify the NI Order prescribing motoring fixed penalty amounts and the current standard scale references in Scotland and Northern Ireland, on legislation.gov.uk.
3. Confirm the £60 and £100 NI figures against nidirect and the Order itself.
4. Check the Scottish Sentencing Council guideline list for anything newer than the death-by-driving guideline.

## Sources used
- Scottish Sentencing Council: https://www.scottishsentencingcouncil.org.uk/news-and-media/news/the-councils-death-by-driving-guideline-is-now-in-force , https://scottishsentencingcouncil.org.uk/sentencing-guidelines/approved-guidelines , https://www.scottishsentencingcouncil.org.uk/gillian-speeding/
- Northern Ireland Judicial Office: https://www.judiciaryni.uk/judiciary-decision-types/type/road-traffic-offences-47
- nidirect: https://nidirect.gov.uk/articles/fixed-penalties-motoring-offences , https://www.nidirect.gov.uk/articles/speed-limits-and-penalties-breaking-them , https://nidirect.gov.uk/content/crown-copyright
- Scotland: https://www.mygov.scot/parking-bus-lane-fine/fixed-penalty-notice , https://scotcourts.gov.uk/taking-action/paying-a-fine/police-scotland-fixed-penalty-notices/
- legislation.gov.uk: https://www.legislation.gov.uk/ssi/2019/83/made , https://www.legislation.gov.uk/uksi/1993/176/data.htm

## Update: option 4 done (2026-11-21)

Added from legislation.gov.uk with the existing fetcher (6 units, test questions rt-035 to rt-038):
- `nisr/2007/319` article 2 and Schedule 1: the Road Traffic (Fixed Penalty) Order (Northern Ireland) 2007, as amended (text as at 2023-05-15, no unapplied changes). **The NI £60 and £100 figures are confirmed in law:** item 54 "Any other fixed penalty offence involving obligatory endorsement | £60"; item 25A (Article 12 of the 1995 Order, careless driving) "£100".
- `nisr/1997/369` article 2 and Schedule 1: the Road Traffic (Fixed Penalty) (Offences) Order (Northern Ireland) 1997 (as made, 1997-08-14), which lists "Article 43 ... Contravening speed limit" as a fixed penalty offence. Together with item 54 this makes £60 the NI speeding fixed penalty. The 1997 text is as made: amendments are not shown.
- `nisi/1984/703` article 5: the NI standard scale (level 3 £1,000). It has 2 unapplied changes.
- `ukpga/1995/46` section 225: the Scottish standard scale (level 3 £1,000).

Still open: the nidirect and mygov.scot pages (options 2 and 3), the Scottish death-by-driving guideline (option 1), and the GB-wide fixed penalty Order is `uksi/2000/2792` (already held). The Schedule 2 graduated fixed penalties (drivers' hours, goods vehicles) of the 2007 Order were not fetched. The partial-coverage warning stays: neither nation has court sentencing guidance for the common offences.

