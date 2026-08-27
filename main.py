"""
Your multi-agent system starts here.

Everything below is a skeleton. The helpers in common.py already work -- they
handle printing, wrapping, and language -- so you can spend your time on the
part that matters: what your agents are, what they can do, and how they hand
work to each other.

Run:  uv run main.py          (Korean output, the default)
      uv run main.py --en     (English output)
"""

import asyncio

from dotenv import load_dotenv
from openai.types.shared.reasoning import Reasoning

from agents import Agent, ModelSettings, WebSearchTool, function_tool
from common import MODEL, require_key, run_many, speak, stream, strip_citations, wrapped

load_dotenv()  # pulls OPENAI_API_KEY out of .env
require_key()  # ...and says so plainly if you have not made that file yet

# Asking the model to summarise its own thinking, so you can watch it work.
# Drop to "low" if it talks too much, raise to "high" if it thinks too little.
THINK = ModelSettings(reasoning=Reasoning(effort="medium", summary="auto"))


# ===========================================================================
# 1. TOOLS -- what your agents can do that words alone cannot
# ===========================================================================
#
# A tool is a plain Python function. @function_tool hands it to the model, and
# the TYPE HINTS AND DOCSTRING become the interface the model reads: it decides
# from them when to call your function and what to pass. So write them for a
# stranger, because that is exactly who is reading.
#
# Good candidates are things a language model is bad at: exact arithmetic, real
# dates, looking something up, anything with a right answer.

@function_tool
def my_tool(argument: str) -> str:
    """TODO: say what this does, in one line.

    Args:
        argument: TODO: say what goes in here.
    """
    return f"TODO: do something real with {argument}"


# WebSearchTool() is built in and needs no code from you. Give it to any agent
# that needs to know something that happened after its training data ended.
#     tools=[WebSearchTool(search_context_size="low")]


# ===========================================================================
# 2. AGENTS -- who is on your team
# ===========================================================================
#
# One agent, one job. An agent asked to do three things does all three worse.
# The instructions are the whole personality: what it owns, what it must not
# do, how long the answer should be, what to do when it is unsure.
#
# speak() bolts the output-language rule on for you. Keep it.

worker = Agent(
    name="TODO-Worker",
    instructions=speak(
        "TODO: tell this agent what it owns, and what it must not do. "
        "Say how long the answer should be -- models are long-winded by default."
    ),
    tools=[my_tool],
    model=MODEL,
    model_settings=THINK,
)

# TODO: add the rest of your team. Two agents is a system; six is a committee.


# ===========================================================================
# 3. THE SHAPE -- how work moves between them
# ===========================================================================
#
# Your system must use ALL THREE. They are not alternatives you choose between;
# they nest, and any system big enough to be interesting contains all of them at
# different levels.
#
#   SEQUENTIAL    you decide the order       A -> B -> C, every time
#   PARALLEL      you decide the pieces      A, B, C at once, every time
#   ORCHESTRATOR  the agent decides          A -> ? -> ?, worked out as it goes
#
# The three answer the same question -- who decides what happens next? -- and
# give three different answers. That is why one system can want all three: some
# steps have an order you already know, some have none, and some cannot be known
# until an earlier answer comes back.
#
# One arrangement that works. The outer shape is sequential; its first step fans
# out in parallel, and its second hands control to an orchestrator:
#
#     STAGE 1  parallel      gather independent things at once
#        |
#     STAGE 2  orchestrator  dig in: call one, read it, decide who is next
#        |
#     STAGE 3  sequential    draft -> check -> rewrite, in that fixed order
#
# That is AN arrangement, not THE arrangement. Nest them however your problem
# actually wants. What does not count: a parallel stage whose pieces secretly
# depend on each other, or an orchestrator whose next call was never in doubt.
# Those are the pattern in name only, and they are easy to spot.
#
# ---------------------------------------------------------------------------
# SEQUENTIAL -- each agent's output is the next one's input.
#
#     first = await stream("STEP 1  ...", agent_a, TASK)
#     second = await stream("STEP 2  ...", agent_b, first.final_output)
#
# ---------------------------------------------------------------------------
# PARALLEL -- independent work, launched together, nobody waiting.
# run_many() takes (label, agent, input) triples, narrates progress instead of
# text (three agents streaming into one terminal is unreadable), and returns
# results in the order you gave them.
#
#     results = await run_many([
#         ("LabelA", agent_a, "..."),
#         ("LabelB", agent_b, "..."),
#     ])
#
# ---------------------------------------------------------------------------
# ORCHESTRATOR -- one agent calls ONE specialist, reads the answer, and only
# then decides who is worth calling next. Give it a budget of handoffs, or it
# will keep asking for help forever.
#
#     for handoff in range(1, MAX_HANDOFFS + 1):
#         move = (await stream(..., orchestrator, transcript, show_answer=False)).final_output
#         if move.call == "DONE":
#             break
#         answer = await stream(..., SPECIALISTS[move.call], move.ask)
#         transcript.append(...)
#
# To make an agent answer in a shape Python can branch on, give it a pydantic
# model as output_type -- otherwise you get a paragraph you cannot use in an
# if-statement:
#
#     from pydantic import BaseModel
#     class Move(BaseModel):
#         call: str
#         ask: str
#     orchestrator = Agent(..., output_type=Move)
# ===========================================================================

TASK = "TODO: what are you actually asking this system to do?"
MAX_HANDOFFS = 4  # the orchestrator stage never gets more calls than this


async def main():
    print("=" * 70)
    print(f"TASK  {TASK}")
    print("=" * 70)

    # -- STAGE 1: PARALLEL ---------------------------------------------------
    # TODO: what can be gathered at the same time because no piece needs any
    # other piece's answer? Replace these with your own agents.
    gathered = await run_many(
        [
            ("TODO-A", worker, TASK),
            ("TODO-B", worker, TASK),
        ]
    )
    notes = "\n\n".join(strip_citations(r.final_output) for r in gathered)

    # -- STAGE 2: ORCHESTRATOR -----------------------------------------------
    # TODO: build the loop. One agent reads what stage 1 found, calls a single
    # specialist, reads the answer, and only then chooses the next one. Stop
    # early when it has what it needs -- unused handoffs are a win.
    #
    #   for handoff in range(1, MAX_HANDOFFS + 1):
    #       ...
    findings = notes  # TODO: replace with what the loop actually turned up

    # -- STAGE 3: SEQUENTIAL -------------------------------------------------
    # TODO: a fixed chain to finish with. Each output feeds the next.
    result = await stream("STAGE 3  TODO-Worker  --  TODO: what it does", worker, findings)

    print(f"\n{'=' * 70}\nRESULT\n{'=' * 70}")
    print(wrapped(result.final_output))


asyncio.run(main())
