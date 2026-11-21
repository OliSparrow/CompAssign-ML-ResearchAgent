from dataclasses import dataclass, field
from datetime import date

import httpx
from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.google import GoogleModel

from research_agent.filters import filter_papers
from research_agent.models import Paper, ResearchAnswer, SearchConstraints, SearchResult
from research_agent.tools import search_papers

# Give the main model a short deadline, so we switch to the backup quickly when it's overloaded
main_model = GoogleModel("gemini-3.5-flash-lite", settings={"request_timeout": 30})
backup_model = GoogleModel("gemini-3.8-flash", settings={"request_timeout": 60})

model = FallbackModel(main_model, backup_model)

CURRENT_YEAR = date.today().year

INSTRUCTIONS = f"""
You are a Research Scout: you find research papers that match a user's request.
The current year is {CURRENT_YEAR}.

Follow this workflow:
1. Read the request and extract the constraints: topic, earliest/latest publication year (min_year/max_year),
   and citation limits. If the user says "recent", use min_year={CURRENT_YEAR - 3},
   and state exactly this assumption in 'uncertainty'.
2. Call the search_research_papers tool with those constraints.
3. If no papers were accepted, you may retry up to 2 more times with a different wording of the topic
   (synonyms, broader terms). NEVER loosen the year or citation constraints.
4. From the ACCEPTED papers only, choose the one most relevant to the topic, based on its title and abstract.
   Ignore accepted papers that are off-topic. If several papers are similarly relevant, prefer the one with
   more citations, and avoid non-peer-reviewed uploads (e.g. Zenodo) or papers with 0 citations when better options exist.
5. Return a ResearchAnswer:
   - Copy the chosen paper exactly as the tool returned it. Never invent or change titles, authors, years,
     citation counts or links.
   - The explanation should say why the paper matches the topic and the constraints. If the user asked for
     a specific format (e.g. "5-7 sentences"), follow it. Otherwise use 2-4 sentences.
   - Only state facts that appear in the tool results (title, authors, year, citation count, abstract).
     Do NOT add details from your own memory, such as the journal or conference name.
   - If no relevant paper satisfies all constraints, set found=false, paper=null, and explain why.
   - Use 'uncertainty' for doubts: ambiguous requests, assumptions you made, or duplicate versions of a paper.
"""


@dataclass
class AgentMemory:
    """Remembers every accepted paper the tool returned during ONE agent run."""

    seen_papers: dict[str, Paper] = field(default_factory=dict)


research_agent = Agent(
    model,
    deps_type=AgentMemory,
    output_type=ResearchAnswer,
    instructions=INSTRUCTIONS,
    retries=2,
)


@research_agent.tool
def search_research_papers(ctx: RunContext[AgentMemory], constraints: SearchConstraints) -> SearchResult:
    """Search OpenAlex for research papers

    Papers that break the year or citation constraints are rejected by code,
    and the reasons are listed. Only choose from the 'accepted' papers
    """
    try:
        papers = search_papers(constraints)
    except httpx.HTTPError as error:
        raise ModelRetry(f"The paper search failed ({error}). Try again, maybe with a simpler topic.")

    result = filter_papers(papers, constraints)

    for paper in result.accepted:
        ctx.deps.seen_papers[paper.openalex_id] = paper

    return result


@research_agent.output_validator
def check_answer(ctx: RunContext[AgentMemory], answer: ResearchAnswer) -> ResearchAnswer:
    """Make sure the final answer only uses a paper that really came from the tool"""
    if not answer.found:
        answer.paper = None
        return answer

    if answer.paper is None:
        raise ModelRetry("You set found=true but gave no paper. Choose an accepted paper or set found=false.")

    real_paper = ctx.deps.seen_papers.get(answer.paper.openalex_id)
    if real_paper is None:
        raise ModelRetry(
            "That paper was not in the accepted search results. "
            "Only choose a paper from the 'accepted' list returned by the tool."
        )

    # Overwrite with the tool's exact data, so the LLM can't have changed any numbers
    answer.paper = real_paper
    return answer