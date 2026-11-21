import csv
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

from pydantic_ai.messages import ModelResponse, ToolCallPart

from evaluation.test_prompts import TEST_CASES, TestCase
from research_agent.agent import AgentMemory, research_agent
from research_agent.models import Paper

RESULTS_DIR = Path(__file__).parent / "results"
PAUSE_BETWEEN_TESTS = 15  # seconds, to stay under the free-tier requests-per-minute limit

AUTO_CHECKS = ["found_as_expected", "year_ok", "citations_ok", "source_ok", "verified_on_openalex"]

COLUMNS = [
    "id", "category", "prompt",
    "found", *AUTO_CHECKS,
    "relevant (manual y/n)", "hallucination_free (manual y/n)", "useful_explanation (manual 1-3)",
    "title", "year", "citations", "url", "explanation", "uncertainty",
    "tool_calls", "models_used", "seconds", "error",
]


# Automatic checks

def check_year(paper: Paper | None, case: TestCase) -> bool | None:
    """True/False if there is a year rule to check, None if there is nothing to check."""
    if paper is None or (case.min_year is None and case.max_year is None):
        return None
    if paper.year is None:
        return False
    if case.min_year is not None and paper.year < case.min_year:
        return False
    if case.max_year is not None and paper.year > case.max_year:
        return False
    return True


def check_citations(paper: Paper | None, case: TestCase) -> bool | None:
    if paper is None or (case.min_citations is None and case.max_citations is None):
        return None
    if paper.citation_count is None:
        return False
    if case.min_citations is not None and paper.citation_count < case.min_citations:
        return False
    if case.max_citations is not None and paper.citation_count > case.max_citations:
        return False
    return True


def check_source(paper: Paper | None) -> bool | None:
    if paper is None:
        return None
    return bool(paper.url) and paper.citation_source == "OpenAlex"


def verify_on_openalex(paper: Paper | None) -> bool | None:
    """Independent hallucination check: look the paper up again by its ID and compare title + year."""
    if paper is None:
        return None

    work_id = paper.openalex_id.split("/")[-1]  # "https://openalex.org/W123" -> "W123"
    params = {"select": "id,display_name,publication_year"}
    api_key = os.getenv("OPENALEX_API_KEY")
    if api_key:
        params["api_key"] = api_key

    try:
        response = httpx.get(f"https://api.openalex.org/works/{work_id}", params=params, timeout=20)
    except httpx.HTTPError:
        return None  # couldn't check, so we don't count it as pass or fail

    if response.status_code != 200:
        return False

    data = response.json()
    return data.get("display_name") == paper.title and data.get("publication_year") == paper.year


def inspect_messages(messages: list) -> tuple[int, str]:
    """Count search tool calls and list which models answered, by reading the run's message history."""
    tool_calls = 0
    models = set()

    for message in messages:
        if isinstance(message, ModelResponse):
            models.add(message.model_name)
            for part in message.parts:
                if isinstance(part, ToolCallPart) and part.tool_name == "search_research_papers":
                    tool_calls += 1

    return tool_calls, ", ".join(sorted(models))


# Running

def run_case(case: TestCase) -> dict:
    row = {"id": case.id, "category": case.category, "prompt": case.prompt}
    start = time.perf_counter()

    try:
        result = research_agent.run_sync(case.prompt, deps=AgentMemory())
    except Exception as error:
        details = [str(error)]
        for sub_error in getattr(error, "exceptions", []):
            details.append(f"{type(sub_error).__name__}: {sub_error}")
        row["error"] = " | ".join(details)[:500]
        row["seconds"] = round(time.perf_counter() - start, 1)
        return row

    answer = result.output
    paper = answer.paper
    tool_calls, models = inspect_messages(result.all_messages())

    row.update({
        "found": answer.found,
        "found_as_expected": None if case.expect_found is None else answer.found == case.expect_found,
        "year_ok": check_year(paper, case),
        "citations_ok": check_citations(paper, case),
        "source_ok": check_source(paper),
        "verified_on_openalex": verify_on_openalex(paper),
        "title": paper.title if paper else "",
        "year": paper.year if paper else "",
        "citations": paper.citation_count if paper else "",
        "url": paper.url if paper else "",
        "explanation": answer.explanation,
        "uncertainty": answer.uncertainty or "",
        "tool_calls": tool_calls,
        "models_used": models,
        "seconds": round(time.perf_counter() - start, 1),
    })
    return row


def print_summary(rows: list[dict]) -> None:
    print("\n===== SUMMARY =====")
    for check in AUTO_CHECKS:
        values = [row.get(check) for row in rows if row.get(check) is not None]
        passed = sum(1 for value in values if value is True)
        print(f"{check:<22} {passed}/{len(values)} passed")

    errors = sum(1 for row in rows if row.get("error"))
    finished = [row for row in rows if not row.get("error")]
    print(f"{'errors':<22} {errors}/{len(rows)}")

    if finished:
        avg_tools = sum(row["tool_calls"] for row in finished) / len(finished)
        avg_seconds = sum(row["seconds"] for row in finished) / len(finished)
        print(f"{'avg tool calls':<22} {avg_tools:.1f}")
        print(f"{'avg seconds':<22} {avg_seconds:.1f}")


def main() -> None:
    # Optional: run only some tests, e.g.  python -m evaluation.run_eval T02 T08
    selected_ids = sys.argv[1:]
    cases = [case for case in TEST_CASES if not selected_ids or case.id in selected_ids]

    RESULTS_DIR.mkdir(exist_ok=True)
    rows = []

    for number, case in enumerate(cases, start=1):
        print(f"[{number}/{len(cases)}] {case.id} - {case.category} ...", flush=True)
        row = run_case(case)
        rows.append(row)

        if row.get("error"):
            print(f"    ERROR: {row['error'][:100]}")
        else:
            print(f"    found={row['found']}  year_ok={row['year_ok']}  citations_ok={row['citations_ok']}  "
                  f"tools={row['tool_calls']}  ({row['seconds']}s)")

        if number < len(cases):
            time.sleep(PAUSE_BETWEEN_TESTS)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    output_path = RESULTS_DIR / f"results_{timestamp}.csv"

    with open(output_path, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS, restval="")
        writer.writeheader()
        writer.writerows(rows)

    print_summary(rows)
    print(f"\nSaved results to {output_path}")


if __name__ == "__main__":
    main()