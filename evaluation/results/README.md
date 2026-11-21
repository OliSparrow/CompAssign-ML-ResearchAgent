# Evaluation: Before vs. After Improvements

This folder contains two evaluation runs of the Research Scout agent on the same 13 test cases
(see `evaluation/test_prompts.py`):

| File | Description |
|---|---|
| `Results_Before_Improvements.csv` | Baseline: the first working version of the agent |
| `Results_After_Improvements.csv` | After four improvements based on the baseline results |

Each test case was run once per version. Runs that crashed because of API errors (503/429) were
re-run and merged into the file, so both files contain a complete result for all 13 tests.

## What I changed

| # | Change | Motivated by |
|---|---|---|
| 1 | Replaced `year` + `year_operator` with `min_year` / `max_year`, so year ranges are fully enforced by code | T08: a 2015-2018 range could only be checked on one side |
| 2 | Instruction: only state facts that appear in the tool results | T05: explanation claimed a journal name that the tool never returned |
| 3 | Instruction: prefer well-cited, peer-reviewed papers when several are equally relevant | T03: picked a paper with 0 citations |
| 4 | Swapped the models: `gemini-3.5-flash-lite` became the main model | Every baseline answer came from the backup anyway, after waiting for the overloaded main model |

## Automatic checks

Counted over tests where the check applies (e.g. no year check when the prompt has no year rule).

| Check | Before | After |
|---|---|---|
| Found / refused as expected | 12/12 | 12/12 |
| Year constraint respected | 7/7 | 7/7 |
| Citation constraint respected | 6/6 | 6/6 |
| Valid source (link + citation source) | 10/10 | 10/10 |
| Paper verified again on OpenAlex | 10/10 | 10/10 |
| Average tool calls per test | 1.54 | 1.31 |
| Average time per test | 11.8 s | 7.3 s |

Both versions pass every automatic check. The improvements targeted problems these checks cannot detect:
invented details in explanations, paper quality, and whether constraints are guaranteed by code or by luck.

## Per-test comparison

| Test | Category | Before | After | Change |
|---|---|---|---|---|
| T01 | after + min citations | Demystifying LLM-Based SE Agents (2025, 1087) | same paper | = |
| T02 | before + min citations | RAG for Knowledge-Intensive NLP (2020, 10564) | same paper | = |
| T03 | vague year ("recent") | UNDO: Recoverability Layer... (2026, 0) | Agentic AI for SE: A Systematic Survey (2026, 0) | Uncertainty note now correct, still 0 citations |
| T04 | exact year + min citations | Weisfeiler and Leman Go Neural (2019, 1738) | GNNs for Social Recommendation (2019, 2811) | Different paper, both valid |
| T05 | narrow topic + after | Single-sequence protein structure prediction (2022, 162) | same paper | Invented journal name removed |
| T06 | exact year + max citations | Federated Learning in Healthcare (2022, 43) | same paper | = |
| T07 | approximate citations | DiffusionCLIP (2022, 1119) | same paper | = |
| T08 | year range | Deep RL for robotic manipulation (2017, 1971) | same paper | Range now enforced by code, 2 → 1 tool calls |
| T09 | no result (impossible year) | correctly refused | correctly refused | = |
| T10 | no result (contradiction) | correctly refused | correctly refused | 2 → 1 tool calls |
| T11 | no result (future year) | correctly refused | correctly refused | = |
| T12 | ambiguous (very broad) | Digital twins to embodied AI (2025, 82) | A Brief History of AI (2019, 4428) | Much better-cited paper |
| T13 | ambiguous ("highly cited") | Hierarchical Attention Networks (2016, 5981) | Attention in NLP (2020, 844) | More on-topic, but fewer citations |

## Effect of each improvement

**1. Year ranges in code (T08).** T08 already passed in the baseline, but only because the LLM happened to
pick a 2017 paper; the code checked just one side of the range. Now both sides are checked by
deterministic code. The agent also needed fewer searches (T08 and T10: 2 → 1 tool calls).

**2. Facts-only explanations (T05).** Worked. The baseline explanation stated the paper was published in
*Nature Machine Intelligence*, a detail from the LLM's own memory, not from our tool. After the change,
the explanation only mentions the title, authors and year. The instruction reduces this kind of
hallucination but cannot guarantee it, because the LLM can still ignore instructions.

**3. Quality preference (T03, T12, T13).** Partly worked.
- T12 improved clearly: 82 → 4428 citations.
- T13 picked a survey that is more directly about attention in NLP, but with fewer citations (5981 → 844).
- T03 still picked a paper with 0 citations. "Recent" papers have had little time to be cited, so for
  this request "recent" and "well-cited" conflict. The uncertainty note is now accurate though
  ("publication year >= 2023" instead of the incorrect "2026").

**4. Model swap.** The average time per test dropped from 11.8 s to 7.3 s, because the agent no longer
waits for the overloaded model before falling back. Both runs were in practice answered by
`gemini-3.5-flash-lite`, so the answer quality was not affected by this change.

## Reliability

| | Before | After |
|---|---|---|
| Tests that crashed on the first run | 1 / 13 | 5 / 13 |
| Runs needed to complete all 13 | 2 | 3 |

The crashes were caused by the free-tier API, not by our code. In the worst case, the main model
was overloaded (503 "high demand") while the backup model's free quota was used up (429), so both
fallback options failed at the same time. Faster requests made this more likely. A paid tier or a
backup model from a second provider would make the agent more reliable.

## Manual scores

| Check | Before  | After   |
|---|---------|---------|
| Relevant paper (y) | 8 / 10  | 9 / 10  |
| Hallucination-free explanation (y) | 11 / 13 | 13 / 13 |
| Average explanation usefulness (1-3) | 2.31       | 2.46       |

Scored by hand using these rules: *relevant* = the paper is about the requested topic;
*hallucination-free* = every claim in the explanation and uncertainty note is true (checked against the
paper's abstract and metadata on OpenAlex); *usefulness* 1 = vague or contains a wrong fact,
2 = correct but generic or missing a requested format, 3 = specific and answers the user's question.
Borderline cases were scored as "no".

The improvements removed both hallucinations (T03, T05) and made the agent pick a more relevant paper
for the broad request in T12. One weakness was not fixed: in T02 the user asked for a 5-7 sentence
summary, but the agent gave 3 sentences before and only 2 after.

## Limitations of this evaluation

- **One run per test.** LLM output varies between runs (e.g. T04 picked a different, equally valid paper),
  so small differences may be chance rather than improvement.
- **One human judge** scored relevance and usefulness.
- **Automatic checks cannot judge relevance or quality.** In T10, OpenAlex returned papers about ChatGPT
  with wrong publication years; our code filter accepted them and only the LLM rejected them.
- **Citation counts change over time**, so re-running the evaluation later may give different numbers.

## Conclusion

The improvements fixed the two clearest problems from the baseline (an invented detail in T05 and a year
range only checked by luck in T08), improved paper quality for broad requests (T12) and made the agent
about 38% faster. The quality preference did not help for "recent" requests (T03), and faster requests
made the agent more vulnerable to free-tier API errors.