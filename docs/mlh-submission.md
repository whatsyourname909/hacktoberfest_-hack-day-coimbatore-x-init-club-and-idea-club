# MLH submission draft

For **Hacktoberfest Hack Day Coimbatore x (INIT Club & IDEA Club)**. Submission page: https://www.mlh.com/events/hacktoberfest-hack-day-coimbatore-x-init-club/submissions/new

Deadline: **5:00 PM IST, October 8, 2026.** Submissions go through MLH, not Devpost. Each field below is ready to paste.

---

## Project name

Argue With My Data

## Short description (one-line pitch)

An AI data analyst that tries to prove its own explanations wrong before it answers. Gemma proposes, code tests, the evidence decides.

## Description

Ask an AI data tool "Why did revenue fall in March?" and it gives you one plausible story. Plausible isn't the same as correct.

Argue With My Data treats the question as an investigation. Upload a CSV or Excel file and ask your question. A LangGraph pipeline calculates the real change in code, then Gemma 4 proposes competing explanations: a lost customer, a product mix shift, a regional decline, a data-quality problem or seasonality. Each explanation gets a pass/fail threshold fixed **before** it's tested. Deterministic pandas and DuckDB tools test every explanation, every result is recomputed and verified, and each one is labelled SUPPORTED, WEAKENED, REJECTED or UNTESTABLE, with an evidence trace.

Gemma also acts as an adversarial critic, but it never does the maths and can't change a verdict. The app shows, step by step, whether Gemma actually answered.

On our demo data, the obvious suspect (a customer who stopped ordering) explains only 8% of the drop and is WEAKENED. A product mix shift explains 67% and is SUPPORTED. Seasonality is honestly marked UNTESTABLE, because two months of data can't show a seasonal pattern.

Built with help from AI coding tools: Claude Code, OpenAI Codex, ChatGPT and Gemini.

## Technologies (built with)

python, gemma, gemini-api, langgraph, langchain, pandas, numpy, duckdb, pydantic, streamlit, plotly, openpyxl

## Links

- **Repository:** https://github.com/whatsyourname909/hacktoberfest_-hack-day-coimbatore-x-init-club-and-idea-club
- **Live demo:** TODO, after deploying (see `docs/deployment.md`)
- **Demo video:** TODO, after recording (see `docs/demo-script.md`)

## AI tools

If the form asks which AI tools were used, list all four the team used:

- Claude Code (Anthropic, Claude Opus 5.5)
- OpenAI Codex
- ChatGPT
- Gemini / Gemini CLI

---

## Prize categories

### Best Use of Gemma 4

Gemma 4 (`gemma-4-26b-a4b-it`), called through the Gemini API, is the reasoning engine of our investigation: it turns the business question into a validated plan, proposes competing explanations, and challenges the evidence as an adversarial critic. Code does every calculation and applies pre-committed thresholds, so Gemma's ideas are tested against the data instead of trusted blindly, and the app shows which steps Gemma actually answered.

**Only enter this category if a live run shows Gemma answering** (the **AI Pipeline Status** panel shows more than 0/5 stages).

### Best Open-Source AI Project

Open-weight AI is central to how the project works: Gemma 4 generates and critiques the hypotheses that drive the whole investigation. The project is MIT-licensed, published in a public GitHub repository, and built on open-source tools (LangGraph, pandas, DuckDB, Pydantic, Streamlit), so anyone can rerun an investigation and check every number.

Meets the category's rules: public GitHub repository ✅, open-source (MIT) license ✅, open-weight AI as an important part ✅.

---

## Before submitting

1. **Deploy the app and record the video,** then add both links above and in the README.
2. **Confirm Gemma works live.** Run one investigation with the API key and check the **AI Pipeline Status** panel: green dots show the stages Gemma answered, and 0/5 stages means it didn't answer at all. If Gemma isn't answering, skip "Best Use of Gemma 4", and in the description say the demo runs on the offline fallback.
3. **Make sure `main` is up to date** before submitting, since the repository link opens `main`.
4. **Check the team:** all four members must be on the MLH submission (the event requires exactly 4).
