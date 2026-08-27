"""
SEQUENTIAL -- a skeleton you can run, then take apart.

    A  ->  B  ->  C

Each agent's output is the next one's input. Nothing runs at the same time and
nothing loops back. Use this shape when the steps have a real order that cannot
be shuffled: you cannot edit a draft that does not exist yet.

This file also shows how to give an agent a TOOL of your own.

As written, the three agents just pass the text along and add a line each --
enough to watch the chain work. Replace the TODOs with a chain that does
something you care about.

Run:  uv run 01_sequential.py          (Korean)
      uv run 01_sequential.py --en     (English)
"""

import asyncio

from dotenv import load_dotenv
from openai.types.shared.reasoning import Reasoning

from agents import Agent, ModelSettings, Runner, function_tool
from common import MODEL, require_key, speak, stream, wrapped

load_dotenv()
require_key()

THINK = ModelSettings(reasoning=Reasoning(effort="medium", summary="auto"))

TASK = "TODO: the text this chain starts from."


# ---------------------------------------------------------------------------
# A tool of your own.
#
# @function_tool hands a plain Python function to the model. The TYPE HINTS AND
# DOCSTRING are the interface -- the model reads them to decide when to call it
# and what to pass, so write them for a stranger.
#
# Reach for a tool when the job needs something a model is bad at: exact
# arithmetic, real dates, a lookup with a right answer.
# ---------------------------------------------------------------------------
@function_tool
def my_tool(argument: str) -> str:
    """TODO: one line saying what this does.

    Args:
        argument: TODO: what goes in here.
    """
    return f"TODO: a real result for {argument}"


step_one = Agent(
    name="StepOne",
    instructions=speak(
        "TODO: replace me. For now: repeat what you were given, then add one "
        "sentence of your own. Nothing else."
    ),
    tools=[my_tool],  # TODO: keep, replace, or drop
    model=MODEL,
    model_settings=THINK,
)

step_two = Agent(
    name="StepTwo",
    instructions=speak(
        "TODO: replace me. For now: repeat what you were given, then add one "
        "more sentence. Nothing else."
    ),
    model=MODEL,
    model_settings=THINK,
)

step_three = Agent(
    name="StepThree",
    instructions=speak(
        "TODO: replace me. For now: repeat what you were given, then say how "
        "many sentences you can count. Nothing else."
    ),
    model=MODEL,
    model_settings=THINK,
)


async def main():
    print("=" * 70)
    print(f"TASK  {TASK}")
    print("=" * 70)

    # The chain starts from the raw input.
    first = await stream("STEP 1  StepOne  --  TODO", step_one, TASK)

    # The PREVIOUS output is the input here. This line is the whole pattern.
    second = await stream("STEP 2  StepTwo  --  TODO", step_two, first.final_output)

    # And again. Add or remove links freely -- the shape does not change.
    third = await stream("STEP 3  StepThree  --  TODO", step_three, second.final_output)

    print(f"\n{'=' * 70}\nRESULT\n{'=' * 70}")
    print(wrapped(third.final_output))


asyncio.run(main())
