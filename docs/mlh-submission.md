# MLH submission draft

For **Hacktoberfest Hack Day Coimbatore x (INIT Club & IDEA Club)**, event slug `hacktoberfest-hack-day-coimbatore-x-init-club`. Deadline: **Oct 8, 5:00 PM IST**.

Nothing here has been submitted. Resolve the items under "Before submitting" first.

---

## name

Argue With My Data

## short_description

An AI data analyst that tries to falsify its own explanations before it answers: Gemma proposes, code tests, the evidence decides.

## description

Ask "Why did revenue fall in March?" and most AI data tools give you one plausible story. Argue With My Data runs an investigation instead.

Upload a CSV and ask a question. A LangGraph state machine profiles the data, has Gemma 4 turn the question into a structured plan, and calculates the real change between the two periods in code. Gemma then proposes 3–5 competing explanations, such as a lost customer, a product mix shift, a regional decline, a data-quality problem or seasonality. Each one becomes a falsification contract with visible thresholds.

Deterministic pandas and DuckDB tools run every test, and a verification step recomputes every result independently. Verdicts (SUPPORTED, WEAKENED, REJECTED or UNTESTABLE) are applied in code from the contract's thresholds. Gemma acts as an adversarial critic that challenges the evidence and suggests alternatives, but it can't change a verdict or introduce numbers. The final report states how much each factor accounts for, never what caused the change.

On our synthetic demo dataset, the obvious explanation (a customer who stopped ordering) accounts for only 8.0% of the decline and is WEAKENED, while a product mix shift accounts for 67.0% and is SUPPORTED. Seasonality is reported as UNTESTABLE, because two months of data can't establish a seasonal pattern.

## built_with

python, gemma, google-gemini-api, langgraph, langchain, pandas, numpy, duckdb, pydantic, streamlit, plotly

## source_url

https://github.com/whatsyourname909/hacktoberfest_-hack-day-coimbatore-x-init-club-and-idea-club

## demo_live_url

TODO

## demo_video_url

TODO

## extra_links

None yet.

## ai_tools

- claude-code
- coding:anthropic/claude-opus-5.5

---

## Prize categories (sponsor_usage answers)

The event's official category descriptions haven't been checked yet, because DevRelay isn't connected to MLH. Compare these answers with the sponsors' descriptions before entering.

### Best Use of Gemma 4

Gemma 4 (`gemma-4-26b-a4b-it`, via the Gemini API and LangChain) drives every reasoning step of our LangGraph investigation: it parses the business question into a validated plan, proposes competing hypotheses, and acts as an adversarial critic on the evidence. We deliberately keep it away from arithmetic and verdicts: code computes every number and applies pre-committed thresholds, so Gemma's reasoning is checked against the data instead of trusted blindly.

### Best Open-Source AI Project

Argue With My Data is built entirely on open-source components (LangGraph, LangChain, pandas, DuckDB, Pydantic, Streamlit) and an open-weight model, Gemma 4. Its code, tests and demo dataset generator are public, so anyone can rerun an investigation and check every number.

---

## Before submitting

1. **Push the code.** It's only on the local `pranav` branch. Commit, push and merge it into `main`, so the GitHub link shows it.
2. **Confirm Gemma works live.** The one live attempt stalled, and the README still says TODO. Don't enter "Best Use of Gemma 4" unless a real Gemma run succeeds.
3. **Add a license.** "Best Open-Source AI Project" needs one, and the README's License section is still TODO. MIT is the usual choice.
4. **Add the live app link and demo video** if you have them. The demo video should say the event name at the start.
5. **Complete the README's TODOs:** team contributions, AI tools used by every teammate, challenges and learnings.
6. **List teammates' AI tools.** `ai_tools` above covers only Claude Code with Claude Opus 5.5. If teammates used other tools (for example Codex, which may have written the original code), MLH requires disclosing them, in the README and on Devpost.
