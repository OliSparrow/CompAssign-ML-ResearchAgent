import os

import httpx

from research_agent.models import Paper, SearchConstraints

OPENALEX_URL = "https://api.openalex.org/works"

# Only ask OpenAlex for the fields that are actually used (faster + cheaper)
FIELDS = "id,display_name,publication_year,cited_by_count,doi,authorships,abstract_inverted_index,primary_location"

MAX_ABSTRACT_LENGTH = 1000


def build_filter(constraints: SearchConstraints) -> str | None:
    """Turn constraints into an OpenAlex filter string, like 'publication_year:<2021,cited_by_count:>499'."""
    filters = []

    if constraints.min_year is not None:
        filters.append(f"publication_year:>{constraints.min_year - 1}")
    if constraints.max_year is not None:
        filters.append(f"publication_year:<{constraints.max_year + 1}")

    # OpenAlex only has strict > and <, so we shift by 1 to make our limits inclusive
    if constraints.min_citations is not None:
        filters.append(f"cited_by_count:>{constraints.min_citations - 1}")
    if constraints.max_citations is not None:
        filters.append(f"cited_by_count:<{constraints.max_citations + 1}")

    if not filters:
        return None
    return ",".join(filters)


def rebuild_abstract(inverted_index: dict[str, list[int]] | None) -> str | None:
    """OpenAlex stores abstracts as {word: [positions]}. Put the words back in order."""
    if not inverted_index:
        return None

    words_by_position = {}
    for word, positions in inverted_index.items():
        for position in positions:
            words_by_position[position] = word

    ordered_words = [words_by_position[i] for i in sorted(words_by_position)]
    return " ".join(ordered_words)


def parse_work(work: dict) -> Paper:
    """Convert one raw OpenAlex result (a dict) into the Paper model."""
    authors = []
    for authorship in work.get("authorships") or []:
        name = (authorship.get("author") or {}).get("display_name")
        if name:
            authors.append(name)

    location = work.get("primary_location") or {}
    url = work.get("doi") or location.get("landing_page_url") or work["id"]

    abstract = rebuild_abstract(work.get("abstract_inverted_index"))
    if abstract and len(abstract) > MAX_ABSTRACT_LENGTH:
        abstract = abstract[:MAX_ABSTRACT_LENGTH] + "..."

    return Paper(
        openalex_id=work["id"],
        title=work.get("display_name") or "Untitled",
        authors=authors,
        year=work.get("publication_year"),
        citation_count=work.get("cited_by_count"),
        citation_source="OpenAlex",
        url=url,
        abstract=abstract,
    )


def search_papers(constraints: SearchConstraints, limit: int = 10) -> list[Paper]:
    """Search OpenAlex for papers matching the topic, year and citation constraints."""
    params = {
        "search": constraints.topic,
        "per_page": limit,
        "select": FIELDS,
    }

    paper_filter = build_filter(constraints)
    if paper_filter:
        params["filter"] = paper_filter

    api_key = os.getenv("OPENALEX_API_KEY")
    if api_key:
        params["api_key"] = api_key

    response = httpx.get(OPENALEX_URL, params=params, timeout=20)
    response.raise_for_status()

    data = response.json()
    return [parse_work(work) for work in data.get("results", [])]


# Quick manual test: run with  python -m research_agent.tools
if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    test = SearchConstraints(
        topic="retrieval augmented generation",
        year=2020,
        year_operator="before",
        min_citations=500,
    )
    for paper in search_papers(test, limit=5):
        print(f"{paper.year} | {paper.citation_count:>6} citations | {paper.title}")
