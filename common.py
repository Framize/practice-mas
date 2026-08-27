"""
Shared helpers. You should not need to edit this file.

The interesting thing here is stream(): it runs an agent and prints what is
happening WHILE it happens -- the thinking as it forms, the tool calls as they
fire, the answer one token at a time. It lives here so that your own files stay
about your agents instead of about printing.
"""

import asyncio
import os
import re
import sys
import time
import unicodedata

from agents import Runner

# The model every agent uses unless its own code says otherwise. gpt-5-nano is
# the cheapest one available, which is what you want while you are learning.
# Change it here once and everything follows.
MODEL = "gpt-5-nano"

LABEL_WIDTH = 14  # "[thinking]    " -- how wide the lane label column is
BODY_INDENT = LABEL_WIDTH  # wrapped lines sit exactly under the first one
WRAP_AT = 94  # hard wrap column, counted in display columns

# Language of the answers. Korean by default; run with --en for English.
LANG = "en" if "--en" in sys.argv else "ko"

_LANGUAGE_RULE = {
    "ko": "Answer in Korean, and do your thinking in Korean as well.",
    "en": "Answer in English.",
}


def speak(instructions: str) -> str:
    """Bolt the language rule onto an agent's instructions.

    Kept in one place so switching every agent between Korean and English is a
    single flag rather than an edit in every file.
    """
    return f"{instructions}\n\n{_LANGUAGE_RULE[LANG]}"


def _pad(text: str, width: int) -> str:
    """Pad to a display width. str.ljust counts characters, which leaves Korean
    labels short by one column per syllable."""
    return text + " " * max(0, width - _w(text))


def _w(text: str) -> int:
    """Display width, not character count. A Korean syllable occupies two
    terminal columns, so counting characters would wrap far too late."""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)


def _tool_label(raw) -> str:
    """Tool calls arrive in different shapes. A function we defined carries a
    name and arguments; a hosted web search carries an action instead. Try both,
    and fall back to the class name so nothing ever crashes in here."""
    name = getattr(raw, "name", None)
    if name:
        return f"{name}({getattr(raw, 'arguments', '')})"

    action = getattr(raw, "action", None)
    if action is not None:
        query = getattr(action, "query", None)
        return f"web_search({query!r})" if query else f"web_search({action})"

    return type(raw).__name__


class _Printer:
    """Word-wraps text that arrives a few characters at a time.

    Wrapping normally needs the whole paragraph up front, which is exactly what
    a stream does not give you. The trick is to hold back only the last partial
    word: everything before it is safe to print now, and the held-back piece
    gets glued to the front of the next chunk.
    """

    def __init__(self) -> None:
        self.lane: str | None = None  # which labelled block we are inside
        self.col = 0  # cursor column, so we know when to wrap
        self.fresh = True  # sitting at the start of a line?
        self.partial = ""  # a word cut in half by the end of a chunk

    def _newline(self) -> None:
        print("\n" + " " * BODY_INDENT, end="", flush=True)
        self.col, self.fresh = BODY_INDENT, True

    def _word(self, word: str) -> None:
        if self.col + _w(word) > WRAP_AT:
            self._newline()
        print(word, end="", flush=True)
        self.col += _w(word)
        self.fresh = False

    def write(self, lane: str, text: str) -> None:
        if lane != self.lane:
            self._flush()
            if self.lane is not None:
                print("\n")  # close the block, then one blank line between blocks
            print(_pad(f"[{lane}]", LABEL_WIDTH), end="", flush=True)
            self.lane, self.col, self.fresh = lane, LABEL_WIDTH, True

        text, self.partial = self.partial + text, ""
        pieces = re.split(r"(\s+)", text)

        # A chunk that does not end on whitespace ends mid-word. Keep that last
        # piece for next time rather than wrapping on a word we cannot measure.
        if pieces and pieces[-1] and not pieces[-1].isspace():
            self.partial = pieces.pop()

        for piece in pieces:
            if not piece:
                continue
            if "\n" in piece:  # the model's own line breaks, kept as they are
                print("\n" * piece.count("\n") + " " * BODY_INDENT, end="", flush=True)
                self.col, self.fresh = BODY_INDENT, True
            elif piece.isspace():
                if not self.fresh:  # never open a line with spaces
                    print(piece, end="", flush=True)
                    self.col += _w(piece)
            else:
                self._word(piece)

    def _flush(self) -> None:
        """Print the half-word we were holding back, if there is one."""
        if self.partial:
            word, self.partial = self.partial, ""
            self._word(word)

    def break_block(self) -> None:
        """Force the next write to open a fresh labelled block."""
        if self.lane is not None:
            self._flush()
            print("\n")
            self.lane = None

    def close(self) -> None:
        self._flush()
        print()


async def stream(label: str, agent, user_input: str, show_answer: bool = True):
    """Run one agent and narrate it live, then hand the finished result back.

    Runner.run_streamed() returns immediately and gives us events while the
    model is still working. Two kinds matter here:

      raw_response_event      the token-by-token feed (thinking, answer text)
      run_item_stream_event   whole things finishing (a tool call, a tool result)

    Everything below is just deciding which lane each chunk belongs in.
    """
    print(f"\n{'=' * 70}\n{label}\n{'=' * 70}")

    out = _Printer()
    result = Runner.run_streamed(agent, user_input)

    async for event in result.stream_events():
        if event.type == "raw_response_event":
            data = event.data

            # The model's summary of its own thinking, arriving as it forms.
            if data.type == "response.reasoning_summary_text.delta":
                out.write("thinking", data.delta)

            # The answer itself, one token at a time. This is exactly the
            # stream you watch in ChatGPT -- now you are holding it yourself.
            elif data.type == "response.output_text.delta":
                # An agent with an output_type answers in raw JSON. Readable to
                # a for-loop, not to a person -- so callers can switch it off
                # and print the parsed object themselves instead.
                if show_answer:
                    out.write("says", data.delta)

            # Hosted web search sends progress, not text.
            elif data.type == "response.web_search_call.searching":
                out.write("web", "searching the web...")

            # The model can think in several separate bursts. Start a new block
            # for each one instead of running them together.
            elif data.type == "response.reasoning_summary_part.added":
                if out.lane == "thinking":
                    out.break_block()

        elif event.type == "run_item_stream_event":
            # Hosted tools are already narrated above and their item event
            # arrives late, so only our own function tools go through here.
            if event.name == "tool_called" and getattr(event.item.raw_item, "name", None):
                out.write("tool call", _tool_label(event.item.raw_item))
            elif event.name == "tool_output":
                out.write("tool result", str(event.item.output).replace("\n", " "))

    out.close()
    return result


_CITATION = re.compile(r"\s*\(\[[^\]]+\]\([^)]+\)\)")


def strip_citations(text: str) -> str:
    """Drop the ([site](url)) markers the hosted web search appends.

    The search tool adds them itself, so asking the model not to does nothing.
    They are useful in real work and pure noise on a projector -- delete this
    call if you would rather show where the facts came from.
    """
    return _CITATION.sub("", text)


def wrapped(text: str, indent: int = 0) -> str:
    """Wrap finished text to the same width the live printer uses.

    stream() wraps while the words arrive; this one is for text we already have
    in full, which is the situation after a parallel run.
    """
    lines = []
    for raw_line in text.split("\n"):
        line, col = " " * indent, indent
        for word in raw_line.split():
            if col > indent and col + 1 + _w(word) > WRAP_AT:
                lines.append(line)
                line, col = " " * indent, indent
            if col > indent:
                line, col = line + " ", col + 1
            line, col = line + word, col + _w(word)
        lines.append(line)
    return "\n".join(lines)


async def run_many(jobs):
    """Run several agents at the same time and narrate the PROGRESS only.

    Streaming three agents word by word into one terminal would interleave them
    into nonsense, so this prints just what is happening -- who started, who is
    searching, who finished and when -- and leaves the bodies to the caller.

    The finishing order is the whole point. It comes out shuffled relative to
    the starting order, which is what "at the same time" looks like from here.

    jobs: a list of (label, agent, input). Results come back in that same order.
    """
    clock = time.perf_counter()

    # The labels come from whoever called us -- in 03 they are section titles an
    # agent invented -- so size the column to what actually turned up.
    column = max([LABEL_WIDTH] + [_w(f"[{job[0]}]") + 2 for job in jobs])

    def note(label: str, message: str) -> None:
        print(_pad(f"[{label}]", column) + message, flush=True)

    async def one(label, agent, user_input):
        note(label, "started")
        searches = 0
        result = Runner.run_streamed(agent, user_input)
        async for event in result.stream_events():
            if (
                event.type == "raw_response_event"
                and event.data.type == "response.web_search_call.searching"
            ):
                searches += 1
                if searches == 1:  # say it once, then just keep count
                    note(label, "searching the web...")
        elapsed = time.perf_counter() - clock
        note(label, f"done  ({elapsed:.1f}s, {searches} search" + ("" if searches == 1 else "es") + ")")
        return result

    # asyncio.gather launches every job before any of them finishes, and hands
    # the results back in the order they were given, not the order they landed.
    return await asyncio.gather(*(one(*job) for job in jobs))


def require_key() -> None:
    """Stop with a readable message instead of a traceback when .env is missing.

    A stack trace is a fine way to tell a library author something is wrong. It
    is a poor way to tell somebody that they have not made a file yet.
    """
    if os.getenv("OPENAI_API_KEY"):
        return
    raise SystemExit(
        "\nNo OPENAI_API_KEY found.\n\n"
        "  1. cp .env.example .env       (Windows: Copy-Item .env.example .env)\n"
        "  2. open .env and paste your key after OPENAI_API_KEY=\n"
        "  3. run this again\n\n"
        "The file must be named exactly .env and sit next to main.py.\n"
    )
