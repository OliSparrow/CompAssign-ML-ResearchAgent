# CompAssign-ML-ResearchAgent
AI Research Agent Using PydanticAI
## Scenario: Research Scout Agent

You are building an AI research assistant for a software company.

The company often needs to make technical decisions based on research, but manually searching for relevant papers is slow. Your task is to build an agent that can search for research papers, apply constraints, and return a short evidence-based recommendation.

The agent should be able to solve tasks such as:

    Find a research paper about LLM agents for software engineering that was published after 2022 and has at least 100 citations. Explain why the paper is relevant and provide the source of the citation count.

Or:

    Find a paper about retrieval-augmented generation published before 2021 with more than 500 citations. Summarize its contribution in 5-7 sentences.

Or:

    Find a recent paper about AI agents using tools and explain whether it would be useful for someone building autonomous software agents.

### Placeholders
The topic, year, citation count, and comparison operators are placeholders. Your agent should support different combinations of these constraints.

## Assignment Description

The goal of this assignment is to apply the concepts from the course to design, implement, and evaluate an AI agent that can use external tools to solve a realistic research task.

Your agent must not rely only on the LLM’s internal knowledge. It must use at least one implemented tool to search for and verify information.
## 01. Implement an AI Research Agent

Using the PydanticAI framework, implement an AI agent that can:

    Understand a user request about research papers.

    Extract relevant search constraints, such as:
        topic
        publication year
        before / after / in a specific year
        minimum, maximum, or approximate citation count

    Use one or more tools to search for candidate papers.

    Select a paper that satisfies the constraints.

    Return a structured answer containing:
        paper title
        authors
        publication year
        citation count
        source of the citation count
        link to the paper or paper page
        short explanation of why the paper matches the request

The agent should be able to reject results that do not satisfy the constraints.
## 02. Implement the Required Tooling

To solve the task, your agent needs access to external information.

You must implement at least one tool that gives the agent access to research paper data.

Possible tool options include:

    A web search tool
    A Semantic Scholar API tool
    An OpenAlex API tool
    A Crossref API tool
    A custom scraper or search wrapper
    Another relevant research paper search API

Your tool should support searching for papers by topic and should provide enough metadata to evaluate whether a paper satisfies the user’s constraints.

At minimum, your tool should be able to return:

    title
    authors
    publication year
    citation count, if available
    URL or DOI
    abstract or short description, if available

Important

Citation counts must come from your implemented tool or an external source. The LLM must not invent citation counts.
## 03. Design the Agent Workflow

You must describe and implement the workflow your agent follows.

For example:

    Parse the user request.
    Identify constraints.
    Search for candidate papers.
    Filter candidates by year and citation count.
    Ask the LLM to reason about relevance.
    Return the best matching paper.
    Explain any uncertainty.

Your implementation should make it clear which parts are handled by the LLM and which parts are handled by deterministic code.
## 04. Evaluate the Agent

Once you have implemented your agent, you must evaluate how well it performs.

Create a small evaluation set with at least 10 test prompts. The prompts should include different combinations of:

    broad topics
    narrow topics
    before / after / exact year constraints
    minimum citation constraints
    cases where no good paper can be found
    ambiguous user requests

For each test prompt, evaluate whether the agent:

    found a relevant paper
    respected the year constraint
    respected the citation constraint
    provided a valid source
    avoided hallucinated information
    gave a useful explanation

You must also briefly research how AI agents can be evaluated and use that to justify your evaluation method.

Your evaluation does not need to be perfect, but it must be systematic.
## 05. Reflection

Include a short reflection in your README or report.

Discuss:

    What worked well?
    What failed or was unreliable?
    How often did the agent need tool calls?
    Did the LLM ever hallucinate?
    How did you prevent incorrect answers?
    What would you improve with more time?

## LLM and setup

Use a capable LLM that supports tool calling with PydanticAI. Choose a suitable provider and model from the list of free LLM APIs. Check the provider's current limits and model capabilities, and explain your choice in the README.

Install and configure PydanticAI and your chosen model provider using the PydanticAI documentation. Register your research tool with the agent so it can retrieve external evidence. Use a structured output model where appropriate.
### API key

Keep API keys in environment variables or another secure local configuration. Do not commit them to GitHub.
Requirements

Your project must include:

    A PydanticAI-based agent.
    At least one custom tool for searching or retrieving research paper information.
    A clear agent workflow.
    A test set with at least 10 evaluation prompts.
    A short evaluation of the agent’s performance.
    A README explaining how to run the project.
    A short video demonstration.

## Deliverables

Submit the following:

    A link to a public GitHub repository containing your code.

    A short video recording, maximum 5 minutes, explaining:
        what your agent does
        which tool or API you implemented
        how the agent workflow works
        one successful demo
        one limitation or failure case

    A README containing:
        setup instructions
        dependency installation
        how to configure the API key
        how to run the agent
        evaluation results
        group member contributions

### Contribution

Contributions must be visible in the GitHub commit history. Each group member should make meaningful commits.
