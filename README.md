# practice-mas

A starting point for building your own **multi-agent system**: several LLM
agents, each with one job, handing work to each other.

This repository is deliberately almost empty. The plumbing is done — printing,
text wrapping, running agents side by side — so that the part you write is the
part worth writing: who your agents are, what they can do, and how work moves
between them.

---

## What you will build

A system of your own that uses **all three patterns** — sequential, parallel,
and orchestrator — each doing the part of the work it actually suits.

That is the brief, and the "all three" is the hard part. Any one of them alone
is a few lines. Making one problem want all three means finding the piece of it
whose order is fixed, the piece whose order does not matter, and the piece
whose next step cannot be known until something comes back.

Pick a subject you would actually like the answer to. Some directions people
take:

- a research desk that gathers sources, digs into the promising one, then
  drafts and checks what it found
- an incident investigator that reads several logs, follows the trail into
  whichever one looks worst, then writes the report
- a trip planner that prices several options at once, interrogates the
  cheapest, then produces an itinerary
- a code reviewer that runs several kinds of check, chases the failure that
  matters, then writes the review

Start smaller than you think. Get two agents talking end to end first, then
grow the shape around them.

---

## Setup

You need a terminal and about five minutes. Everything is driven by
[uv](https://docs.astral.sh/uv/), a Python package manager that also installs
Python itself — so there is no separate Python install step and no virtual
environment to activate by hand.

### 1. Install uv

**macOS / Linux**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell)**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Close the terminal and open a new one, then check it worked:

```bash
uv --version
```

If the command is not found, the installer told you to add a directory to your
`PATH`; scroll up in the installer output and follow that line.

### 2. Get the code

```bash
git clone <this-repository-url>
cd practice-mas
```

### 3. Install the packages

```bash
uv sync
```

This reads `pyproject.toml`, downloads the right Python version if you do not
have it, creates a `.venv` folder, and installs everything into it. You never
activate it yourself — `uv run` does that for you.

It installs two things:

| Package | What it is for |
| --- | --- |
| `openai-agents` | the Agents SDK: `Agent`, `Runner`, tools, handoffs |
| `python-dotenv` | reads your API key out of `.env` |

### 4. Add your API key

Copy the example file:

```bash
cp .env.example .env
```

**Windows (PowerShell)**

```powershell
Copy-Item .env.example .env
```

Open `.env` in any editor and paste your key after `OPENAI_API_KEY=`:

```
OPENAI_API_KEY=sk-proj-...
OPENAI_DEFAULT_MODEL=gpt-5-nano
```

Three things about that file:

- **`.env` is in `.gitignore`.** It stays on your machine and is never
  committed. Keep it that way.
- **Never paste a key anywhere else** — not into `main.py`, not into a chat, not
  into a screenshot. A key that reaches a public repository is a key someone
  else is already spending.
- **`OPENAI_DEFAULT_MODEL` is optional but recommended.** Every agent uses that
  model unless its own code overrides it, and `gpt-5-nano` is the cheapest one
  available. Learn on the cheap model; switch later if you genuinely need to.

### 5. Check it runs

```bash
uv run main.py
```

You should see a banner, an agent thinking out loud, and a `RESULT` block. The
answer will be nonsense — `main.py` is a skeleton full of `TODO` — but if you
got that far, your setup is finished and the rest is yours.

---

## What is in the box

```
01_sequential.py    one pattern each. Runnable skeletons: fill in the TODOs
02_parallel.py      and each one works on its own. Read them first, steal
03_orchestrator.py  from them freely.

main.py             your workspace. Where all three come together.
common.py           the plumbing. Works already; you should not need to edit it.
pyproject.toml      the package list.
.env.example        copy this to .env and put your key in it.
```

**Start with the numbered files.** Each one is the smallest thing that shows its
pattern working, and each carries one extra mechanic you will want later:

| File | Pattern | Also shows |
| --- | --- | --- |
| `01_sequential.py` | a fixed chain | writing a tool of your own with `@function_tool` |
| `02_parallel.py` | independent work at once | the built-in `WebSearchTool` |
| `03_orchestrator.py` | the agent decides as it goes | structured output with `output_type` |

Run each one as it comes, unchanged, to see the mechanic move. Then fill in its
TODOs. Then build the real thing in `main.py`, where all three have to work
together.

### The helpers in `common.py`

| Helper | What it does |
| --- | --- |
| `MODEL` | the model every agent uses. One line to change them all. |
| `speak(instructions)` | bolts the output-language rule onto an agent's instructions. Korean by default, English with `--en`. |
| `stream(label, agent, input)` | runs one agent and narrates it live — thinking, tool calls, answer — then returns the result. Pass `show_answer=False` when the agent returns structured output. |
| `run_many([(label, agent, input), ...])` | runs several agents at once. Prints progress rather than text, because three agents streaming into one terminal is unreadable. Returns results in the order you gave them. |
| `wrapped(text)` | wraps finished text to the same width, counting Korean characters as two columns. |
| `strip_citations(text)` | removes the `([site](url))` markers the web search tool appends. |

---

## The three shapes

They are not alternatives to choose between — your system uses all three. What
makes them different is that each gives a different answer to one question:
**who decides what happens next?**

### Sequential — you decide the order

```
A -> B -> C
```

Each agent's output is the next one's input. Use it when the steps have a real
order that cannot be shuffled: you cannot edit a draft that does not exist yet.

### Parallel — you decide the pieces

```
A ┐
B ┼-> (or nowhere at all)
C ┘
```

Independent work, launched together, nobody waiting on anybody. Use it when no
piece needs another piece's answer. You may merge the results at the end, or
simply let each agent finish its own job — not everything needs a summary.

### Orchestrator — the agent decides

```
A -> ? -> ? -> ...
```

One agent calls **one** specialist, reads what came back, and only then works
out who is worth calling next. The second call cannot be chosen before the
first one answers. This is the only shape where you do not know in advance what
will happen.

Give it a **budget** — a maximum number of handoffs. An agent that can keep
asking for help forever will do exactly that.

### Putting all three together

The patterns nest. One arrangement that works: the outer shape is sequential,
its first step fans out in parallel, and its second hands control to an
orchestrator.

```
STAGE 1  parallel       gather independent things at once
   |
STAGE 2  orchestrator   dig in: call one, read it, decide who is next
   |
STAGE 3  sequential     draft -> check -> rewrite, in that fixed order
```

That is *an* arrangement, not *the* arrangement — nest them however your
problem wants. Two things do not count, and both are easy to spot from the
outside:

- a **parallel** stage whose pieces secretly need each other's answers
- an **orchestrator** whose next call was never actually in doubt

If you could have written the sequence down before running it, that stage is
sequential wearing a costume.

---

## The building blocks

**An agent** is a name, a set of instructions, and optionally some tools.

```python
from agents import Agent

writer = Agent(
    name="Writer",
    instructions=speak("You turn notes into three short paragraphs."),
    model=MODEL,
)
```

**A tool** is a plain Python function. The type hints and docstring are the
interface — the model reads them to decide when to call it and what to pass.

```python
from agents import function_tool

@function_tool
def days_until(target: str) -> str:
    """Count the days from today until a date.

    Args:
        target: the date, written as YYYY-MM-DD.
    """
    ...
```

Reach for a tool whenever the job needs something a language model is bad at:
exact arithmetic, real dates, a lookup with a right answer.

**Web search** is built in and needs no code from you:

```python
from agents import WebSearchTool

researcher = Agent(..., tools=[WebSearchTool(search_context_size="low")])
```

**Structured output** makes an agent answer in a shape you can branch on. An
orchestrator that replies "I think we should ask the database team" is useless
in an `if`-statement; one that replies `{"call": "DatabaseEngineer"}` is not.

```python
from pydantic import BaseModel

class Move(BaseModel):
    call: str
    ask: str

orchestrator = Agent(..., output_type=Move)
```

---

## Cost, and not being surprised by it

Every agent turn is a paid API call, and a system that calls five agents costs
five times what one does. Three habits keep it boring:

- **Stay on the cheap model while you are building.** `gpt-5-nano` is
  roughly an order of magnitude cheaper than the larger ones.
- **Cap your loops.** Any `while` around an agent needs a maximum. This is the
  single most expensive mistake available to you.
- **Keep answers short.** "Answer in at most five bullet points, one sentence
  each" costs a fraction of what a model writes when left alone.

Set a spending limit on your key in the OpenAI dashboard before you start.

---

## Troubleshooting

**`uv: command not found`** — you did not open a new terminal after installing.
Do that first; if it still fails, add uv's directory to your `PATH` as the
installer instructed.

**`ModuleNotFoundError: No module named 'agents'`** — you ran `python main.py`
instead of `uv run main.py`. Always use `uv run`.

**`AuthenticationError: 401`** — your key is wrong, expired, or not being read.
Check that the file is named exactly `.env` (not `.env.txt`), sits next to
`main.py`, and has no quotes or spaces around the key.

**`RateLimitError: 429`** — too many requests at once, or no credit on the key.
If a parallel run triggers it, run fewer agents at a time.

**No `[thinking]` lines appear** — the model returned no reasoning summary that
turn. Raise `effort` in the `ModelSettings` from `"low"` towards `"medium"`.

**The agent ignores an instruction** — instructions compete. Shorten them, put
the rule that matters first, and say what the agent must *not* do as plainly as
what it must.
