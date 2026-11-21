from research_agent.models import Paper, RejectedPaper, SearchConstraints, SearchResult


def check_paper(paper: Paper, constraints: SearchConstraints) -> list[str]:
    """Check one paper against the constraints.
    Returns a list of reasons why it fails. An empty list means the paper is ok.
    """
    reasons = []

    # Year check
    has_year_limit = constraints.min_year is not None or constraints.max_year is not None

    if has_year_limit and paper.year is None:
        reasons.append("publication year is unknown")
    elif has_year_limit:
        if constraints.min_year is not None and paper.year < constraints.min_year:
            reasons.append(f"published in {paper.year}, before the earliest allowed year {constraints.min_year}")
        if constraints.max_year is not None and paper.year > constraints.max_year:
            reasons.append(f"published in {paper.year}, after the latest allowed year {constraints.max_year}")

    # Citation check
    has_citation_limit = constraints.min_citations is not None or constraints.max_citations is not None

    if has_citation_limit and paper.citation_count is None:
        reasons.append("citation count is unknown")
    else:
        if constraints.min_citations is not None and paper.citation_count < constraints.min_citations:
            reasons.append(f"has {paper.citation_count} citations, below minimum of {constraints.min_citations}")
        if constraints.max_citations is not None and paper.citation_count > constraints.max_citations:
            reasons.append(f"has {paper.citation_count} citations, above maximum of {constraints.max_citations}")

    return reasons


def filter_papers(papers: list[Paper], constraints: SearchConstraints) -> SearchResult:
    """Split papers into accepted and rejected, keeping the reasons for each rejection."""
    result = SearchResult()

    for paper in papers:
        reasons = check_paper(paper, constraints)
        if reasons:
            result.rejected.append(RejectedPaper(title=paper.title, reasons=reasons))
        else:
            result.accepted.append(paper)

    return result


# Quick manual test with fake papers: python -m research_agent.filters
if __name__ == "__main__":
    test_papers = [
        Paper(openalex_id="W1", title="Good paper", year=2023, citation_count=150),
        Paper(openalex_id="W2", title="Too old", year=2020, citation_count=900),
        Paper(openalex_id="W3", title="Too few citations", year=2024, citation_count=12),
        Paper(openalex_id="W4", title="Missing data", year=None, citation_count=None),
    ]
    test_constraints = SearchConstraints(topic="anything", min_year=2023, min_citations=100)

    outcome = filter_papers(test_papers, test_constraints)

    print("ACCEPTED:")
    for paper in outcome.accepted:
        print(f"  - :D {paper.title}")
    print("REJECTED:")
    for rejected in outcome.rejected:
        print(f"  -  >:/ {rejected.title}: {'; '.join(rejected.reasons)}")