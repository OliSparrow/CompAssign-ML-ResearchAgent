import textwrap

from dotenv import load_dotenv

# Load the API keys from .env BEFORE importing the agent, because the agent reads the key when it is created.
load_dotenv()

from research_agent.agent import AgentMemory, research_agent
from research_agent.models import ResearchAnswer


def print_answer(answer: ResearchAnswer) -> None:
    """Print the agent's structured answer in a readable way."""
    if not answer.found or answer.paper is None:
        print("\n>:/ No paper found that matches all constraints.")
        print(f"Reason: {answer.explanation}")
    else:
        paper = answer.paper
        print("\n:D Paper found!")
        print(f"Title:     {paper.title}")
        print(f"Authors:   {', '.join(paper.authors) or 'Unknown'}")
        print(f"Year:      {paper.year}")
        print(f"Citations: {paper.citation_count} (source: {paper.citation_source})")
        print(f"Link:      {paper.url}")
        print(f"\nWhy it matches:\n{textwrap.fill(answer.explanation, width=100)}")

    if answer.uncertainty:
        print(f"\n:/ Uncertainty: {answer.uncertainty}")


def main() -> None:
    print("Research Scout Agent - type 'quit' to exit.")

    while True:
        question = input("\nYour question: ").strip()

        if question.lower() in {"quit", "exit", ""}:
            print("Bye!")
            break

        try:
            result = research_agent.run_sync(question, deps=AgentMemory())
            print_answer(result.output)
        except Exception as error:
            print(f"\nSomething went wrong: {error}")


if __name__ == "__main__":
    main()