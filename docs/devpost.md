# Devpost draft

Ready to paste. Before posting: add the AI coding tools line, fill in the live app and video links, and if Gemma isn't working live, add "The demo runs on our offline fallback."

---

## Project name

Argue With My Data

## Tagline

Most AI data analysts give you an answer. Ours tries to prove its own explanation wrong first.

## Inspiration

AI data tools sound confident even when they're wrong. When revenue drops right after a big customer leaves, everyone blames that customer, even if they explain only a fraction of the drop. We wanted an analyst that questions its own explanations, shows its working, and admits when the data can't answer.

## What it does

Upload a CSV or Excel file and ask *"Why did revenue fall in March?"*. The app:

1. calculates the real change in code
2. proposes competing explanations
3. fixes a pass/fail threshold for each **before** testing it
4. tests and verifies each one with deterministic analysis
5. labels each **SUPPORTED**, **WEAKENED**, **REJECTED** or **UNTESTABLE**, with an evidence trace

On our demo data, the obvious suspect, a lost customer, explains only **8%** of the drop (**WEAKENED**). The real driver is a **product mix shift** at **67%** (**SUPPORTED**), and seasonality is honestly **UNTESTABLE**.

## How we built it

- **LangGraph** orchestrates the investigation as a state machine.
- **Gemma 4** (via the Gemini API and LangChain) interprets the question, proposes hypotheses and acts as a critic. It never does the maths or changes a verdict.
- **pandas, NumPy and DuckDB** compute every number, and **Pydantic** validates every model response.
- **Streamlit and Plotly** show the verdicts, the evidence, and whether Gemma actually answered each step.

## Challenges we ran into

- A Gemma call that hung for minutes, which we fixed with timeouts and a safe fallback.
- Keeping the AI from deciding verdicts after seeing the numbers.
- Merging two versions of the project built in parallel.
- Code that passed tests on one Python version and crashed on another.

## Accomplishments that we're proud of

It rejects the tempting explanation and finds the real one, with numbers anyone can verify. And it can say "I can't test this" instead of making something up.

## What we learned

Plausible isn't the same as correct. Let the AI suggest ideas, let code do the maths, and always test on a clean machine.

## What's next

A "challenge mode" that attacks its own conclusion, letting users argue their own theory, and support for longer data histories.

## Built with

python, gemma, gemini-api, langgraph, langchain, pandas, numpy, duckdb, pydantic, streamlit, plotly

## Links

- **GitHub:** https://github.com/whatsyourname909/hacktoberfest_-hack-day-coimbatore-x-init-club-and-idea-club
- **Live app:** TODO, add after deploying
- **Demo video:** TODO, add after recording

## AI coding tools (add to the description)

Built with help from Claude Code, OpenAI Codex, ChatGPT and Gemini.
