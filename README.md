# Research Scout Agent

An AI research assistant built with [PydanticAI](https://ai.pydantic.dev/). It finds research papers that match
a user's request (topic, publication year and citation count), checks the results with deterministic code,
and returns a structured, evidence-based answer.

Example question:

> Find a paper about retrieval-augmented generation published before 2021 with more than 500 citations.
> Summarize its contribution in 5-7 sentences.

Example answer (shortened):

```
:D Paper found!
Title:     Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks
Authors:   Patrick Lewis, Ethan Perez, Aleksandra Piktus, ...
Year:      2020
Citations: 10564 (source: OpenAlex)
Link:      https://doi.org/10.48550/arxiv.2005.11401
```

All paper data (title, authors, year, citation count, link) comes from the [OpenAlex](https://openalex.org/) API,
never from the LLM's own memory.

## Setup

### 1. Requirements

- Python 3.10 or newer (developed and tested with Python 3.13)
- A free Google AI Studio API key
- Optional, but recommended: a free OpenAlex API key

### 2. Clone the repository and create a virtual environment

```bash
git clone <repository-url>
cd CompAssign-ML-ResearchAgent
python -m venv .venv
```

Activate the virtual environment:

```bash
# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

(If you use PyCharm like me, do: **Settings → Project → Python Interpreter → Add Interpreter → Virtualenv**. :D)

### 3. Install the dependencies

```bash
pip install -r requirements.txt
```

The main dependencies are `pydantic-ai` (agent framework), `httpx` (HTTP requests to OpenAlex)
and `python-dotenv` (loading API keys from a `.env` file).

### 4. Configure the API keys

Copy `.env.example` to a new file called `.env` in the project root and fill in your keys:

```
GOOGLE_API_KEY=your-google-ai-studio-key
OPENALEX_API_KEY=your-openalex-key
```

- **Google API key:** create one at [aistudio.google.com](https://aistudio.google.com) → *Get API key*.
- **OpenAlex API key (optional):** create one at [openalex.org/settings/api](https://openalex.org/settings/api)
  and verify your email address. Without a key the agent still works, but shares a small daily budget
  with everyone on the same network.

## How to run

### The agent

```bash
python main.py
```

Type a question and press Enter. Type `quit` to exit.

### The evaluation

Run all 13 test cases:

```bash
python -m evaluation.run_eval
```

Or only specific test cases:

```bash
python -m evaluation.run_eval T02 T08
```

(T02 / T08 can be changed into any tests, or more added too)

Results are saved as a timestamped CSV file in `evaluation/results/`.

### Quick tests of the individual parts (no LLM needed)

```bash
python -m research_agent.filters
python -m research_agent.tools
```

## Model and API choice

### LLM: Google Gemini (free tier via Google AI Studio)

I use Gemini because the free tier requires no payment details, and the models support
**tool calling** and **structured output**, which PydanticAI needs for both my search tool and the
`ResearchAnswer` output model.

The agent uses a **fallback setup** (`FallbackModel`):

| Role | Model | Deadline |
|---|---|---|
| Main | `gemini-3.5-flash-lite` | 30 s |
| Backup | `gemini-3.8-flash` | 60 s |

I originally used `gemini-3.8-flash` as the main model, but on the free tier it was constantly overloaded
(503 errors and waits of 100+ seconds), and in my baseline evaluation every answer ended up coming from the
backup anyway. I therefore made the lighter, more available model the main one. Each model has a
request deadline, so the agent switches to the backup quickly instead of waiting.

Free-tier limits (checked on 21 November 2026 in Google AI Studio):

| Model | Requests per minute | Tokens per minute | Requests per day |
|---|---|---|---|
| `gemini-3.5-flash-lite` | 15 | 250K | 500 |
| `gemini-3.8-flash` | 5 | 250K | 20 |

One question uses about 2-4 model requests, so `gemini-3.5-flash-lite` allows roughly 4-7 questions per
minute. `gemini-3.8-flash` only allows 20 requests per day, which is another reason it works better as a
backup than as the main model. During the evaluation I hit both limits: `gemini-3.5-flash-lite` peaked at
15/15 requests per minute, and `gemini-3.8-flash` reached 22/20 requests per day, which caused the
429 "quota exceeded" errors.

### Paper data: OpenAlex API

I chose [OpenAlex](https://openalex.org/) because it is free, covers a very large number of papers, and
returns everything the assignment requires: title, authors, publication year, citation count, DOI/link and
abstract. It also supports filtering by year and citation count on the server side.

At the time of writing, OpenAlex can be used without a key (with a small shared daily budget). A free key
gives a personal budget of $1/day, and one search costs $0.001, so about 1,000 searches per day.

## Agent workflow

```
User asks question
   ↓
1. LLM: extracts the constraints (topic, min/max year, min/max citations)  ← LLM
   ↓
2. Tool: searches OpenAlex with these constraints                          ← code
   ↓
3. Filter: checks every paper again, records why papers are rejected        ← code
   ↓
4. LLM: picks the most relevant accepted paper and explains why            ← LLM
   ↓
5. Validator: checks that the chosen paper really came from the tool,
   and replaces it with the tool's exact data                              ← code
   ↓
ResearchAnswer (structured output)
```

If no paper is accepted, the LLM may retry the search up to 2 more times with a reworded topic, but it is
never allowed to loosen the year or citation constraints. If still nothing matches, it returns
`found = false` with an explanation.

### Which parts are LLM and which are deterministic code

| Task | Handled by | Where |
|---|---|---|
| Understanding the question, extracting constraints | LLM | `SearchConstraints` (filled in by the LLM as the tool's input) |
| Searching for papers | Code | `tools.py` → `search_papers()` |
| Year and citation filtering | Code | `tools.py` (OpenAlex filter) **and** `filters.py` (double-check) |
| Judging topic relevance and paper quality | LLM | Agent instructions, step 4 |
| Writing the explanation | LLM | `ResearchAnswer.explanation` |
| Checking that the answer uses a real paper | Code | `agent.py` → `check_answer()` (output validator) |
| Citation counts, years, authors, links | Code (OpenAlex) | Copied from the tool, never written by the LLM |

### How I prevent incorrect answers

- **Citation counts come only from OpenAlex.** The `Paper` model is filled in by my tool, not by the LLM.
- **Constraints are enforced twice by code:** once in the OpenAlex query, once in `filters.py`.
- **Output validator:** if the LLM picks a paper that was not in the accepted search results, it is told to
  try again (`ModelRetry`). The chosen paper is then replaced with the tool's exact data, so the LLM
  cannot change any numbers.
- **Missing data counts as a fail:** a paper without a known year or citation count is rejected when the
  request has such a constraint.
- **The agent may refuse:** `found = false` is a valid answer when nothing matches.
- **Instructions:** the LLM may only state facts that appear in the tool results.

## Evaluation

### Method
The evaluation uses 13 test prompts (`evaluation/test_prompts.py`) covering broad and narrow topics,
before/after/exact-year/range constraints, minimum, maximum and approximate citation counts, cases where
no paper should be found, and ambiguous requests. For each prompt, the expected constraints were written
down by hand.

- **Automatic checks (code):** found/refused as expected, year respected, citations respected, valid
  source, and the paper verified again on OpenAlex.
- **Manual checks (me):** relevant paper (y/n), hallucination-free explanation (y/n), and usefulness of
  the explanation (1-3). Scoring rules: see [`evaluation/results/README.md`](evaluation/results/README.md).

To design my evaluation, I looked at how AI agents are commonly evaluated in research:

- **Task success with clear criteria.** Agent benchmarks such as AgentBench (Liu et al., 2024) evaluate
  agents on many concrete tasks, each with a clear way to decide whether the task was completed.
  → For each of my test prompts, I wrote down the expected constraints by hand, so year, citation and
  found/refused checks have an objective right answer and can be checked automatically by code.
- **Reliability over repeated runs.** τ-bench (Yao et al., 2025) shows that agents which succeed once
  often fail on the same task in later attempts, and measures how consistently a task is solved over
  several runs.
  → I ran each test once per version because of API limits, and list this as a limitation: some
  differences between runs may be chance.
- **Checking for hallucinations against a source.** Ji et al. (2023) describe hallucinations as generated
  content that is unsupported by, or contradicts, the source information.
  → I check every returned paper again on OpenAlex automatically, and I compared each explanation
  with the paper's abstract and metadata by hand.

This leads to a **hybrid evaluation**: objective criteria are checked automatically by code, and
subjective criteria are scored by a human.

**References**

- Liu, X., Yu, H., Zhang, H., et al. (2024). *AgentBench: Evaluating LLMs as Agents.* ICLR 2024.
  https://doi.org/10.48550/arxiv.2308.03688
- Yao, S., Shinn, N., Razavi, P., & Narasimhan, K. (2025). *τ-bench: A Benchmark for Tool-Agent-User
  Interaction in Real-World Domains.* https://doi.org/10.48550/arxiv.2406.12045
- Ji, Z., Lee, N., Frieske, R., et al. (2023). *Survey of Hallucination in Natural Language Generation.*
  ACM Computing Surveys. https://doi.org/10.1145/3571730

### Results

I evaluated the agent twice: a **baseline**, and again **after four improvements** that were based on
the weaknesses the baseline revealed. Full details: [`evaluation/results/README.md`](evaluation/results/README.md).

| Check | Before | After |
|---|---|---|
| Found / refused as expected | 12/12 | 12/12 |
| Year constraint respected | 7/7 | 7/7 |
| Citation constraint respected | 6/6 | 6/6 |
| Valid source | 10/10 | 10/10 |
| Paper verified again on OpenAlex | 10/10 | 10/10 |
| Average tool calls per test | 1.54 | 1.31 |
| Average time per test | 11.8 s | 7.3 s |
| Tests that crashed on the first run (API errors) | 1/13 | 5/13 |

| Check | Before  | After   |
|---|---------|---------|
| Relevant paper (y) | 8 / 10  | 9 / 10  |
| Hallucination-free explanation (y) | 11 / 13 | 13 / 13 |
| Average explanation usefulness (1-3) | 2.31       | 2.46       |

## Reflection

**What worked well?**
The agent correctly refused all three impossible requests (a paper from 1850, a paper about ChatGPT before
2015, and a paper from after 2030) instead of inventing one. All year and citation constraints were
respected in every completed run, because they are enforced by code rather than left to the LLM.
Splitting the work between the LLM (understanding and judging) and code (searching, filtering, verifying)
made the agent both flexible and trustworthy.

**What failed or was unreliable?**
- **The free-tier LLM APIs** were the least reliable part: overloaded models (503), used-up quotas (429)
  and long waits. In one case both the main and the backup model were unavailable at the same time.
- **Keyword search:** OpenAlex matches words, not meaning, so a search for "retrieval augmented
  generation" also returned a paper about augmented reality. The LLM has to filter out these
  off-topic results.
- **Duplicate versions:** the same paper can appear twice (e.g. an arXiv preprint with 10,564 citations
  and the published version with 19,767), each with its own citation count.
- **Wrong metadata:** OpenAlex returned papers about ChatGPT dated before 2015. My code filter accepted
  them because the metadata said they matched; only the LLM noticed they were wrong.
- **"Recent" vs. "well-cited":** for requests about recent papers, the agent still chose papers with
  0 citations, because new papers have not had time to be cited.

**How often did the agent need tool calls?**
On average 1.3 search calls per question after the improvements (1.5 before). Most questions needed a
single search; the "no result" cases used up to 3, because the agent retried with reworded topics before
giving up, as instructed.

**Did the LLM ever hallucinate?**
It never invented a paper or a citation count: all 10 papers it returned were verified again on OpenAlex.
It did hallucinate *details in explanations*: in the baseline, it claimed a paper was published in
*Nature Machine Intelligence*, which my tool never returned (it is actually *Nature Computational Science*).
OpenAlex had no abstract for that paper, so the LLM only had the title to work with and filled the gap
from its own memory. It also once described its own assumption incorrectly ("recent means 2026", while it
actually searched from 2023). Both were fixed by stricter instructions, but instructions reduce this risk
rather than guarantee it.

**How did I prevent incorrect answers?**
See [How I prevent incorrect answers](#how-i-prevent-incorrect-answers): data only from the tool,
constraints enforced twice by code, an output validator that rejects papers not found by the tool, and
allowing the agent to answer "no paper found".

**What would I improve with more time?**
- Run each test case several times to measure reliability, since LLM output varies between runs.
- Use a backup model from a second provider, so one provider's outage doesn't stop the agent.
- Merge duplicate versions of the same paper and add the journal/venue to the tool's output.
- Add a second paper source (e.g. Semantic Scholar) or semantic search, for better relevance.
- Have multiple people (or an LLM judge) score the manual checks, to reduce single-judge bias.

## Video

The video demonstration (max. 5 minutes) is submitted separately via Moodle.

## Contributions

This project was made individually. Check the commit history for the development process, and my "Use of AI"
section below for how AI assistance was used!

## Use of AI
For this project I used Claude as a guide. I used it to help explain concepts step by step, suggest project structure, and for assistance with example code.
All code was typed in manually myself, and tested / adjusted where it was needed. I also used Claude to assist with debugging problems
(like the slow and failing model requests) and drafting documentation!
Claude also fact-checked the agent's explanations against the paper abstracts and suggested manual scores,
which I reviewed and decided on myself.

All the design decisions, running the agent + evaluation, judging results and the final choices in this repo were my own! :)