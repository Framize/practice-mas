"""
PARALLEL -- a skeleton you can run, then take apart.

    A ┐
    B ┼--  all at once, nobody waiting
    C ┘

Independent work, launched together. Use this shape when no piece needs any
other piece's answer. If one of them does, it is not parallel -- it is a chain
you have hidden.

What happens to the results afterwards is up to you. Merging them into one
document is a choice, not a requirement: three answers to three different
questions are often better left as three answers.

This file also shows the built-in WEB SEARCH tool.

As written, three agents answer three throwaway questions -- enough to watch
them run together. Replace the TODOs.

Run:  uv run 02_parallel.py          (Korean)
      uv run 02_parallel.py --en     (English)
"""

import asyncio
from pathlib import Path

from dotenv import load_dotenv
from openai.types.shared.reasoning import Reasoning

from agents import Agent, ModelSettings, WebSearchTool
from common import MODEL, require_key, run_many, speak, strip_citations, wrapped

load_dotenv()
require_key()

THINK = ModelSettings(reasoning=Reasoning(effort="medium", summary="auto"))


def worker(name: str, brief: str, searches: bool = False) -> Agent:
    """One shape, several workers. Handy when they differ only in their brief."""
    return Agent(
        name=name,
        instructions=speak(
            f"{brief} Answer in at most three bullet points, one sentence each. "
            f"No URLs and no citation links."
        ),
        # WebSearchTool() is built in and needs no code from you. Give it to any
        # agent that must know something newer than its training data.
        tools=[WebSearchTool(search_context_size="low")] if searches else [],
        model=MODEL,
        model_settings=THINK,
    )


# TODO: replace these three with your own. Each label doubles as the progress
# tag on screen and, below, as a filename -- so keep them short.
JOBS = [
    ("TODO-A", worker("WorkerA", "TODO: what this one investigates."), "TODO: its question."),
    ("TODO-B", worker("WorkerB", "TODO: what this one investigates.", searches=True), "TODO: its question."),
    ("TODO-C", worker("WorkerC", "TODO: what this one investigates."), "TODO: its question."),
]


async def main():
    print("=" * 70)
    print(f"RUNNING {len(JOBS)} JOBS AT THE SAME TIME")
    print("=" * 70)

    # run_many launches every job before any of them finishes. It prints
    # PROGRESS rather than text, because three agents streaming into one
    # terminal would interleave into nonsense. Watch the 'done' lines come back
    # in a different order from the 'started' ones -- that shuffle is the proof
    # they really did run together.
    results = await run_many([(label, agent, question) for label, agent, question in JOBS])

    # Only now, with everything finished, do we touch the bodies.
    out = Path("out")
    out.mkdir(exist_ok=True)

    for (label, _, _), result in zip(JOBS, results):
        report = strip_citations(result.final_output)
        path = out / f"{label}.md"
        path.write_text(f"# {label}\n\n{report}\n", encoding="utf-8")
        print(f"\n{'-' * 70}\n{label}  ->  {path}\n{'-' * 70}")
        print(wrapped(report))

    # TODO: decide what happens next. Leave them as separate files, or feed
    # them into one more agent that merges them -- but only if merging them
    # actually makes the answer better.
    print(f"\n{'=' * 70}\nWrote {len(JOBS)} files into {out}/\n{'=' * 70}")


asyncio.run(main())
