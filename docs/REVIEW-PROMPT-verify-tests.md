# Prompt: verify the road traffic test questions (run in a separate session)

Paste everything below the line into a new Claude Code session opened in `C:\Users\cibele\source\repos\uk-law`, on branch `verify-test-questions`.

---

You are an independent reviewer for the `uk-law` project, a verified, versioned UK law knowledge base for AI retrieval (road traffic area). You did not write this work. Be sceptical, and report problems rather than smoothing them over.

## Background
`tests/road-traffic/questions.yaml` holds 34 test questions. Each has a draft `expected_answer` and `expected_sources` (unit ids). All are `verified: false`: nobody has yet checked the expected answers against the source text. `python -m tools.evaluate.run` measures whether search returns the expected sources (recall 51/54 at k=6), which is meaningless if the expectations are wrong.

A worksheet generator was added: `tools/evaluate/worksheet.py` writes `docs/VERIFY-road-traffic.md` (regenerate with `python -m tools.evaluate.worksheet`). For each question it quotes the verbatim text of each expected source, with as-at date, extent and URL, plus what search returned.

## Job A: verify the questions
For EVERY question in `docs/VERIFY-road-traffic.md` (all 34), decide from the quoted source text alone:
1. Does the text support every part of the expected answer (numbers, time limits, amounts, points, ban lengths)? Quote the words that do. Where the text is cut at 60 lines, open the `data/` file named under the quote.
2. Is anything in the expected answer NOT in the listed sources (i.e. from memory)? Flag it.
3. Are the expected sources right: anything essential missing, anything irrelevant listed? Check the "also returned" list and use `get_provision` / `get_related` (uk-law MCP) or search `data/` if a better unit exists. Example to check first: rt-001 says "6 points within 2 years of passing the test" but cites only `ukpga/1995/13/section/2`; the 2-year period may be defined in another unit.
4. Does each source apply in the question's nation (`extent`, `extent_basis`) and is it in force (`valid_from`, `unapplied_changes`)? If `unapplied_changes` > 0, say whether the pending changes could affect the answer; if you cannot tell from `data/`, the verdict is `UNSURE`. Scotland and Northern Ireland questions (rt-011, rt-024 to rt-034): never accept England and Wales law as the basis.
5. Do any sources contradict each other (e.g. guidance vs legislation)? Legislation wins.

Give each question one verdict: `OK`, `FIX ANSWER`, `FIX SOURCES`, `UNSURE`. For every non-OK verdict propose the exact corrected `expected_answer` / `expected_sources`.

## Job B: review the worksheet tool
Read `tools/evaluate/worksheet.py` and check it:
- Does `find_current` resolve every expected id to the correct file? Confirm none render "NOT IN DATA" wrongly and that no wrong unit is matched (id-to-path mapping is by string replacement; look for collisions, e.g. section 136 vs 136B, or ids with other unit types).
- Does it ever alter `questions.yaml`? It must not.
- Is any text shown not verbatim, or truncated without saying so?
- Any crash on edge cases (a question with no nation, a source with no version block, an empty `expected_sources`)?
Report bugs with file:line and a concrete failing input.

## Rules
- Answer ONLY from the text in `data/` or returned by the uk-law MCP tools. Do not add law from memory. If the text does not settle something, the verdict is `UNSURE`.
- Do not set `verified: true` in `questions.yaml`. Only a person does that. Produce the verdict table instead.
- Do not change anything under `data/` or `raw/`.
- This is legal information, not legal advice; a solicitor should confirm questions marked `UNSURE`.
- Do not commit or push.

## Output
Write `docs/VERIFY-road-traffic-review.md` containing:
1. A summary: counts per verdict, and the 5 most serious problems.
2. A table: `id | verdict | reason (quote the supporting or contradicting words) | proposed fix`.
3. A "Tool review" section with the Job B findings.
4. A list of questions a human solicitor must look at, and why.
Then reply with the summary only.
