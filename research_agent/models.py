from typing import Literal

from pydantic import BaseModel, Field


class Paper(BaseModel):
    """One research paper, as returned by our search tool (OpenAlex)."""

    openalex_id: str = Field(description="Unique OpenAlex ID, e.g. 'https://openalex.org/W123'")
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    citation_count: int | None = None
    citation_source: str = "OpenAlex"
    url: str | None = Field(default=None, description="DOI link or paper page")
    abstract: str | None = None


class SearchConstraints(BaseModel):
    """The constraints extracted from the user's request."""

    topic: str = Field(description="Short search query, e.g. 'retrieval-augmented generation'")

    year: int | None = Field(default=None, description="The year mentioned by the user, if any")
    year_operator: Literal["before", "after", "in"] | None = Field(
        default=None,
        description="How to compare publication year with 'year'",
    )

    min_citations: int | None = Field(
        default=None,
        description="Minimum citation count, inclusive. 'More than 500' means 501, 'at least 500' means 500. For 'around N', use roughly 0.8*N",
    )
    max_citations: int | None = Field(
        default=None,
        description="Maximum citation count. For 'around N', use roughly 1.2*N",
    )


class ResearchAnswer(BaseModel):
    """The final structured answer the agent must return."""

    found: bool = Field(description="True only if a paper satisfying ALL constraints was found")
    paper: Paper | None = Field(
        default=None,
        description="The chosen paper, copied exactly from the tool results. None if not found",
    )
    explanation: str = Field(description="Why this paper matches the request (or why none was found)")
    uncertainty: str | None = Field(
        default=None,
        description="Any doubts, e.g. ambiguous request or missing citation data",
    )

class RejectedPaper(BaseModel):
    """A paper that has failed the constraints + why"""
    title: str
    reasons: list[str]

class SearchResult(BaseModel):
    """What the search tool has handed back to the LLM afer filtering"""
    accepted: list[Paper] = Field(default_factory=list)
    rejected: list[RejectedPaper] = Field(default_factory=list)