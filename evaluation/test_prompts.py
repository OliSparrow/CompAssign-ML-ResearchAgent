from dataclasses import dataclass


@dataclass
class TestCase:
    """One evaluation prompt, plus what a correct answer must satisfy (written by hand)."""

    id: str
    category: str
    prompt: str
    min_year: int | None = None
    max_year: int | None = None
    min_citations: int | None = None
    max_citations: int | None = None
    expect_found: bool | None = True  # True = should find a paper, False = should find none, None = either is fine


TEST_CASES = [
    # Examples from the assignment brief
    TestCase(
        id="T01",
        category="after + min citations",
        prompt="Find a research paper about LLM agents for software engineering that was published after 2022 "
               "and has at least 100 citations. Explain why the paper is relevant and provide the source of the citation count.",
        min_year=2023,
        min_citations=100,
    ),
    TestCase(
        id="T02",
        category="before + min citations",
        prompt="Find a paper about retrieval-augmented generation published before 2021 with more than 500 citations. "
               "Summarize its contribution in 5-7 sentences.",
        max_year=2020,
        min_citations=501,
    ),
    TestCase(
        id="T03",
        category="vague year ('recent')",
        prompt="Find a recent paper about AI agents using tools and explain whether it would be useful "
               "for someone building autonomous software agents.",
        min_year=2023,  # "recent" = last 3 years
    ),

    # Different constraint types
    TestCase(
        id="T04",
        category="exact year + min citations",
        prompt="Find a paper about graph neural networks published in 2019 with at least 1000 citations.",
        min_year=2019,
        max_year=2019,
        min_citations=1000,
    ),
    TestCase(
        id="T05",
        category="narrow topic + after",
        prompt="Find a paper about using transformers for protein structure prediction published after 2020.",
        min_year=2021,
    ),
    TestCase(
        id="T06",
        category="exact year + max citations",
        prompt="Find a paper about federated learning in healthcare published in 2022 with fewer than 50 citations.",
        min_year=2022,
        max_year=2022,
        max_citations=49,
    ),
    TestCase(
        id="T07",
        category="approximate citations",
        prompt="Find a paper about diffusion models for image generation with around 1000 citations.",
        min_citations=800,
        max_citations=1200,
    ),
    TestCase(
        id="T08",
        category="year range (known weakness)",
        prompt="Find a paper about reinforcement learning for robotics published between 2015 and 2018 "
               "with at least 200 citations.",
        min_year=2015,
        max_year=2018,
        min_citations=200,
    ),

    # --- Cases where NO paper should be found ---
    TestCase(
        id="T09",
        category="no result (impossible year)",
        prompt="Find a paper about quantum knitting algorithms published in 1850 with at least 10000 citations.",
        max_year=1850,
        min_citations=10000,
        expect_found=False,
    ),
    TestCase(
        id="T10",
        category="no result (contradiction)",
        prompt="Find a paper about ChatGPT published before 2015.",
        max_year=2014,
        expect_found=False,
    ),
    TestCase(
        id="T11",
        category="no result (future year)",
        prompt="Find a paper about prompt engineering published after 2030.",
        min_year=2031,
        expect_found=False,
    ),

    # --- Ambiguous requests ---
    TestCase(
        id="T12",
        category="ambiguous (very broad)",
        prompt="Find me a good paper about AI.",
        expect_found=None,
    ),
    TestCase(
        id="T13",
        category="ambiguous ('highly cited')",
        prompt="Find a highly cited paper about attention mechanisms in natural language processing.",
    ),
]