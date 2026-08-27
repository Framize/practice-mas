"""
ORCHESTRATOR -- a skeleton you can run, then take apart.

    Orchestrator  ->  ?  ->  reads the answer  ->  ?  ->  reads the answer  ...

This is NOT a fan-out. Nothing here runs at the same time, and that is the
point. The orchestrator calls ONE specialist, waits, reads what came back, and
only then works out who is worth asking next. The second call cannot be chosen
before the first one answers -- which is exactly what 02 cannot do, because 02
knows all of its jobs before it starts.

The test: if you could have written the sequence down before running it, this
is a chain in disguise and you should use 01.

It gets a BUDGET. An agent that can keep calling for help forever will.

This file also shows STRUCTURED OUTPUT -- making an agent answer in a shape
Python can branch on.

Run:  uv run 03_orchestrator.py          (Korean)
      uv run 03_orchestrator.py --en     (English)
"""

import asyncio

from dotenv import load_dotenv
from openai.types.shared.reasoning import Reasoning
from pydantic import BaseModel

from agents import Agent, ModelSettings, function_tool
from common import MODEL, require_key, speak, stream, wrapped

load_dotenv()
require_key()

# Spend reasoning where the judgement is. The orchestrator decides; the
# specialists mostly look things up and report.
DECIDE = ModelSettings(reasoning=Reasoning(effort="medium", summary="auto"))
REPORT = ModelSettings(reasoning=Reasoning(effort="low", summary="auto"))

GOAL = "TODO: the question the orchestrator has to get to the bottom of."
MAX_HANDOFFS = 4


# ---------------------------------------------------------------------------
# Give your specialists something real to look at, or they will invent it.
# A dict of canned data behind a tool is enough, and it makes the run fast,
# free, and the same every time.
# ---------------------------------------------------------------------------
FACTS = {
    "alpha": "TODO: what the Alpha specialist can find out.",
    "beta": "TODO: what the Beta specialist can find out.",
    "gamma": "TODO: what the Gamma specialist can find out.",
}


@function_tool
def look_up(area: str) -> str:
    """Look up what is known about one area.

    Args:
        area: one of alpha, beta, gamma.
    """
    return FACTS.get(area, f"no such area: {area}")


def specialist(name: str, owns: str) -> Agent:
    """Every specialist is the same agent walking a different beat."""
    return Agent(
        name=name,
        instructions=speak(
            f"You own {owns}. Use the look_up tool on your own area before "
            f"answering -- always. Report only what it actually says, in at "
            f"most three sentences. If what you found points at someone else's "
            f"area, say that area's name plainly."
        ),
        tools=[look_up],
        model=MODEL,
        model_settings=REPORT,
    )


# TODO: replace these with your own team.
SPECIALISTS = {
    "AlphaExpert": specialist("AlphaExpert", "alpha"),
    "BetaExpert": specialist("BetaExpert", "beta"),
    "GammaExpert": specialist("GammaExpert", "gamma"),
}


# Structured output. An orchestrator that replies "I think we should ask Beta"
# is useless in an if-statement; one that replies {"call": "BetaExpert"} is not.
class Move(BaseModel):
    call: str  # a specialist's name, or DONE to stop
    ask: str  # the question to put to them
    why: str  # why this one, now -- one short sentence


orchestrator = Agent(
    name="Orchestrator",
    instructions=speak(
        "You are running an investigation. You cannot look at anything "
        "yourself; you can only call one specialist at a time and read what "
        "they send back.\n\n"
        f"Your specialists: {', '.join(SPECIALISTS)}.\n\n"
        "You will be shown the goal and every answer so far. Choose the ONE "
        "specialist to call next and the single question to put to them. "
        "Follow the evidence: when an answer names another area, that area is "
        "your next call. Never call the same specialist twice. Answer DONE as "
        "soon as you can settle the goal -- unused handoffs are a win."
    ),
    output_type=Move,
    model=MODEL,
    model_settings=DECIDE,
)

reporter = Agent(
    name="Reporter",
    instructions=speak(
        "You are given a goal and the trail of answers that came back. Settle "
        "the goal in one sentence, give the chain that got you there in one "
        "more, and say what to do first. Use only what is in the trail."
    ),
    model=MODEL,
    model_settings=DECIDE,
)


async def main():
    print("=" * 70)
    print(f"GOAL    {GOAL}")
    print(f"BUDGET  {MAX_HANDOFFS} handoffs")
    print("=" * 70)

    trail: list[str] = []
    seen: list[str] = []  # so the orchestrator cannot ask the same person twice
    used = 0

    for handoff in range(1, MAX_HANDOFFS + 1):
        so_far = "\n\n".join(trail) if trail else "(nothing yet -- this is the first call)"
        called = ", ".join(seen) if seen else "nobody yet"

        # show_answer=False because an agent with an output_type replies in raw
        # JSON. We print the parsed decision ourselves, just below.
        move = (
            await stream(
                f"HANDOFF {handoff}/{MAX_HANDOFFS}  Orchestrator  --  who next?",
                orchestrator,
                f"GOAL\n{GOAL}\n\nALREADY CALLED (do not call again)\n{called}"
                f"\n\nANSWERS SO FAR\n{so_far}",
                show_answer=False,
            )
        ).final_output

        if move.call == "DONE" or move.call not in SPECIALISTS:
            print(f"\n  -> Orchestrator stops after {used} handoffs")
            print(wrapped(move.why, indent=5))
            break

        print(f"\n  -> calls {move.call}")
        print(wrapped(f"why: {move.why}", indent=5))

        answer = await stream(f"          {move.call}  --  answers", SPECIALISTS[move.call], move.ask)
        used = handoff
        seen.append(move.call)
        trail.append(f"[{move.call}] {answer.final_output}")
    else:
        print(f"\n  -> budget of {MAX_HANDOFFS} handoffs is spent")

    final = await stream(
        "REPORT  Reporter  --  writes it up",
        reporter,
        f"GOAL\n{GOAL}\n\nTRAIL\n" + "\n\n".join(trail),
    )

    print(f"\n{'=' * 70}\nRESULT  (after {used} of {MAX_HANDOFFS} handoffs)\n{'=' * 70}")
    print(wrapped(final.final_output))


asyncio.run(main())
