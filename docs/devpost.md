# Devpost draft

Drafted from README.md. Before submitting, update anything that describes features which aren't working yet, and fill in every TODO. Remove items from "What's next" that the team doesn't want to promise.

---

## Project name

Argue With My Data

## Tagline

Most data agents give you an answer. Ours tries to falsify the explanation before it gives you one.

---

## Inspiration

AI data tools are spreading fast, and they answer with the same confidence whether they're right or wrong. A convincing wrong explanation is worse than no answer, because people act on it.

We noticed three problems in particular:

- **The most obvious explanation is often wrong.** When a metric drops, people latch onto the most memorable event, like a large customer leaving, even when it accounts for only a small part of the change.
- **People can't check how an AI reached its answer.** Most "chat with your data" tools give a final answer with no way to inspect the reasoning.
- **AI tools rarely admit what the data can't answer.** They'll explain seasonality from three months of data rather than say it can't be tested.

So we set out to build an AI analyst that has to doubt its own explanations.

## What it does

You upload a CSV and ask a question like *"Why did revenue fall in March?"* Instead of answering straight away, Argue With My Data runs an investigation:

1. It profiles the data and works out what the question is asking.
2. It calculates the actual change between the two periods.
3. It proposes several competing explanations, such as customer churn, a product mix shift, a regional decline, fewer orders, or a data-quality problem.
4. For each explanation, it writes a **falsification contract**: which test to run, and the explicit thresholds that would support or reject it.
5. It runs deterministic tests on the data, verifies the calculations, and has a critic challenge the explanations.
6. Each explanation gets a verdict: **SUPPORTED**, **WEAKENED**, **REJECTED** or **UNTESTABLE**, with a full evidence trace (claim → test → calculation → result → verdict).

The answer reports how much each factor accounts for, not what caused the change, because contribution isn't causation.

## How we built it

- **LangGraph** runs the investigation as a state machine: profile → parse question → baseline → hypotheses → plan tests → execute test → verify → critic → route. The router either runs more tests (with a limit on rounds) or moves to the final synthesis.
- **Gemma** interprets the question, proposes hypotheses, writes the test plans, acts as the critic and writes the final explanation. It never computes the numbers.
- **pandas, NumPy and DuckDB** do every calculation: period comparisons, breakdowns, contributions to the change, mix analysis, trends and data-quality checks.
- **A controlled tool registry** validates every test request before running it. No model-generated code is ever executed.
- **Pydantic** validates all model output that drives execution.
- **Streamlit and Plotly** show the investigation step by step, with the evidence table and trace.

## Challenges we ran into

TODO. Fill this in at the end with what actually happened. Possible candidates if they turn out true:

- getting reliable structured JSON out of Gemma
- designing a demo dataset where the tempting explanation is genuinely wrong, verified by calculation
- deciding how the critic and the fixed thresholds share the job of reaching a verdict
- keeping the LangGraph loop from running forever

## Accomplishments that we're proud of

TODO. Fill this in once things work. For example: *"The system weakened the obvious explanation (a lost customer) and identified the real driver from the evidence"*, but only if it did so in the demo.

## What we learned

TODO. Fill this in at the end.

## What's next for Argue With My Data

- **Challenge mode:** the system deliberately attacks its own final conclusion.
- **Users can bring their own theory** ("I think it's Customer X") and the system argues back.
- **More analysis tools**, and support for datasets with longer history so seasonality becomes testable.
- **Connecting directly to databases and spreadsheets**, not only CSV uploads.

## Built with

python, langgraph, langchain, gemma, pandas, numpy, duckdb, pydantic, streamlit, plotly

## Links

- **GitHub:** https://github.com/whatsyourname909/hacktoberfest_-hack-day-coimbatore-x-init-club-and-idea-club
- **Live app:** TODO
- **Demo video:** TODO
