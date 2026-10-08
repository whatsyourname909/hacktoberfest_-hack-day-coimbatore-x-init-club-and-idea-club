# Argue With My Data

> An AI data investigation agent that tries to falsify its own explanations before it answers. Upload a CSV or Excel file, ask why a metric changed, and it tests competing explanations with deterministic calculations to show which ones the evidence supports, weakens, rejects or can't test.

## Team

**Team Name:** Training with Vibes


| Member                   | Contribution |
| ------------------------ | ------------ |
| Krishav JS (Team Leader) | Backend development |
| Pranav Senthil           | Documentation, README and submission |
| Rahul Srinivasan         | Troubleshooting and debugging |
| Mohal Raj                | Frontend development |


## Problem Statement

### The Problem

When a business metric changes, people ask "why?". AI data assistants are good at producing a plausible answer, such as "revenue fell because a major customer stopped ordering". A plausible answer isn't necessarily correct. A single dramatic event may account for only a small share of a change, while the real driver is spread thinly across the data. Analysts, managers and founders who act on the plausible answer can make the wrong decision.

### Why We Chose This Problem

- **AI answers can sound right without being right.** AI data tools are spreading fast, and they answer with the same confidence whether they're right or wrong. A convincing wrong explanation is worse than no answer, because people act on it. We wanted an AI analyst that has to doubt its own explanations.
- **The most obvious explanation is often wrong.** When a metric drops, people latch onto the most memorable event, like a large customer leaving, even when it accounts for only a small part of the change. We wanted a tool that measures how much each explanation actually accounts for.
- **People can't check how an AI reached its answer.** Most "chat with your data" tools give a final answer with no way to inspect the reasoning. We wanted every claim to be traceable to a specific test and calculation.
- **AI tools rarely admit what the data can't answer.** We wanted a system that can say an explanation is untestable, for example seasonality with only three months of data, instead of inventing an answer.

## Solution

Argue With My Data treats a "why" question as an investigation instead of a chat. It proposes several competing explanations, defines in advance how each one could be falsified, runs deterministic tests on the data, checks the calculations, has a critic challenge the results, and only then reports which explanations hold up. It also says when an explanation can't be tested with the data available.

### Key Features

- **Competing hypotheses:** several measurable explanations are tested, not just the first plausible one.
- **Falsification contracts:** each hypothesis gets a structured test with explicit, visible thresholds for support and rejection.
- **Deterministic evidence:** aggregations, percentages and contributions are calculated in code, never by the language model.
- **Four verdicts:** SUPPORTED, WEAKENED, REJECTED or UNTESTABLE, with an evidence trace (claim → test → calculation → result → verdict) for each.
- **Causality guardrail:** results are reported as contribution ("accounts for 40% of the decline"), not causation.

## Innovation and Differentiation

Most AI data tools follow CSV → LLM → answer. Argue With My Data puts an adversarial loop between the question and the answer: the model proposes explanations and tests, code computes the evidence, a verification step checks it, and a critic challenges the explanations before any conclusion is given. The system can weaken or reject its own first explanation, and can return UNTESTABLE instead of forcing an answer when the data is insufficient.

## Technical Implementation

### Architecture

```mermaid
flowchart TD
    S([START]) --> Q[validate_question<br/>rejects only unusable questions]
    Q --> A[profile_data<br/>code]
    A --> B[parse_question<br/>Gemma]
    B --> C[calculate_baseline<br/>code]
    C --> D[generate_hypotheses<br/>Gemma]
    D --> E[plan_tests<br/>falsification contracts]
    E --> F[execute_test<br/>registered analysis tools]
    F --> G[verify_result<br/>code recomputes every result]
    G --> H[critic<br/>code applies thresholds, Gemma adds challenges]
    H --> R{route_next}
    R -->|hypotheses still untested, at most 2 rounds| E
    R -->|all tested| I[final_synthesis]
    I --> Z([END])
```

Any node that reports an error ends the run with a clear message instead of continuing.

The same flow, as the user experiences it:

![Argue With My Data flow: choose data, ask a question, test hypotheses, verify, critic verdicts, evidence-based summary](mermaid-diagram.png)

### Technology Stack


| Category        | Technologies                                                     |
| --------------- | ---------------------------------------------------------------- |
| Frontend        | Streamlit, Plotly                                                |
| Backend         | Python 3.11+, LangGraph, pandas, NumPy, DuckDB, Pydantic         |
| Database        | N/A                                                              |
| AI / ML         | Gemma 4 (`gemma-4-26b-a4b-it` by default) via LangChain (`langchain-google-genai`) |
| Infrastructure  | TODO: deployment                                                 |
| APIs / Services | Google Gemini API (serves the Gemma model)                       |


### How It Works

0. **Check the question** (`analysis/question_validator.py`): rejects only clearly unusable input, such as an empty or one-word question. With a Gemma key, Gemma also checks whether the question fits the dataset, with a 5-second limit.
1. **Profile the data** (`analysis/profiling.py`): row count, data types, date columns, likely metrics and dimensions, missing values and date range.
2. **Parse the question** (`parse_question`): Gemma turns the question into a `QuestionPlan` (metric, date column, two periods, question type, candidate dimensions). Column names are checked against the data, and a requested month that isn't in the data is reported, never silently replaced.
3. **Calculate the baseline** (`calculate_baseline`): code computes both period totals, the absolute change and the percentage change.
4. **Generate hypotheses** (`generate_hypotheses`): Gemma proposes 3–5 explanations, each tied to one test: `contribution`, `mix`, `data_quality` or `trend`.
5. **Plan tests** (`plan_tests`): each hypothesis becomes a falsification contract with visible, test-specific thresholds:

   | Test | SUPPORTED | WEAKENED | REJECTED |
   |---|---|---|---|
   | contribution, mix | explains ≥ 50% of the change | ≥ 5% | < 5% |
   | data quality | ≥ 20% missing values or ≥ 10% duplicates | other material issues | < 5% missing, < 2% duplicates and no missing months |
   | trend (seasonality) | n/a | history available but not conclusive | **UNTESTABLE** with fewer than 24 months |

6. **Execute tests** (`execute_test`): every contract runs in one pass through the controlled registry in `tools/registry.py`. No model-generated code is executed.
7. **Verify** (`verify_result`): code recomputes the baseline and every test result independently. Any hypothesis whose evidence fails verification is reported as UNTESTABLE instead of evidence-backed.
8. **Critic** (`critic`): the verdict is computed in code from the contract's thresholds. Gemma then reviews the evidence as an adversarial critic; its challenge and any alternative explanation are attached as notes, but it can't change a verdict. Notes containing numbers or causal words ("caused", "proves") are discarded.
9. **Route** (`route_next`): if any hypothesis is still untested, the graph plans and runs tests again, for at most 2 rounds.
10. **Final synthesis** (`final_synthesis`): a report built from the verified verdicts. Gemma may only pick which SUPPORTED hypothesis to lead with. The report always ends by stating that the results show contribution and association, not causation.

If no `GEMMA_API_KEY` is set, or a Gemma call fails, each Gemma step falls back to a local, schema-validated rule: hypotheses are generated from the dataset's own columns, and verdicts are still computed from the data.

#### Demo result (verified)

Running "Why did revenue fall in March?" on the bundled `data/demo_sales.csv`, with the local fallback (no Gemma key), produces:

| Hypothesis | Test | Result | Verdict |
|---|---|---|---|
| Revenue change | baseline | ₹10,000,000 → ₹7,940,000 (−₹2,060,000, −20.6%) | — |
| A departing customer | contribution by customer | lost customers account for 8.0% of the change | WEAKENED |
| Product mix shift | mix by product | the unit-share shift accounts for 67.0% of the change | SUPPORTED |
| Regional decline | contribution by region | the largest region accounts for 14.0% of the change | WEAKENED |
| Data quality | data quality | 0% missing values, 0% duplicates, 0 missing months | REJECTED |
| Seasonality | trend | only 2 monthly periods available; 24 needed | UNTESTABLE |

All results passed verification. The demo dataset is synthetic and is regenerated by `data/generate_demo.py`. It's a 33-row monthly summary built to make the investigation easy to follow, not realistic order-level history: its customer and region names are illustrative, and its two monthly snapshots can't test seasonality.

The three other demo datasets give these results with their suggested questions (local fallback, verified):

| Dataset | Question | Change | Result |
|---|---|---|---|
| Marketing | "Why did spend increase in March?" | spend +74.7% | channel SUPPORTED, campaign type WEAKENED (37%) |
| Marketing | "Which channels drove the change in conversions in March?" | conversions +63.5% | channel SUPPORTED (51%), campaign type WEAKENED (36%) |
| HR attrition | "Why did departures increase in April?" | departures +180.0% | department and seniority each WEAKENED (41%): no single explanation supported |
| E-commerce | "Why did revenue drop in April?" | revenue −44.1% | device WEAKENED (40%), traffic source WEAKENED (36%): no single explanation supported |

When no single factor reaches the 50% threshold, the app says so instead of forcing an answer.

### Technical Decisions

- **The language model never calculates.** Gemma parses, proposes and challenges; pandas and DuckDB compute every number.
- **Verdicts are applied in code** from thresholds fixed in each contract, so the model can't move the goalposts after seeing the results.
- **Verification gates every claim:** results are recomputed independently, and unverified evidence is reported as UNTESTABLE.
- **A controlled tool registry** (`tools/registry.py`) instead of model-generated code.
- **LangGraph owns the investigation state** and routing, with a hard limit of 2 test rounds and an early stop on errors.
- **All model output is validated** against Pydantic schemas (`models/schemas.py`) before it's used.
- **An offline fallback** keeps the app usable without an API key, and still computes verdicts from the data.

## Implementation During the Hackathon

The current codebase contains:

- the LangGraph investigation graph (`graph/`)
- the deterministic analysis tools (`analysis/`) and tool registry (`tools/`)
- the Gemma integration and its schema validation (`agents/llm.py`, `models/schemas.py`)
- the Streamlit interface (`app.py`, `ui/`)
- four synthetic demo datasets (sales, marketing, HR attrition, e-commerce) with their generators and suggested questions (`data/`)
- 13 automated tests (`tests/test_pipeline.py`)

All of this was built during the Hack Day (October 8, 2026, 9:00 AM – 5:00 PM IST). The timeline below comes from the repository's git history and the timestamps of the project files (times in IST):

| Time | Work |
|---|---|
| from 10:56 | First project files created: the LangGraph pipeline, analysis tools, schemas, Streamlit UI, demo dataset and tests |
| 11:22–11:34 | README set up: project description, architecture, team and problem statement |
| 12:38 | First version of the app added to the repository |
| 12:43–13:20 | Krishav's version of the app and its verification notes, merged into `main` through pull request #1 (merged by Rahul) |
| 14:04–14:07 | Improved version merged into `main`: redesigned interface, Gemma request timeout and safe fallback, source-archive script |
| 14:23–14:48 | Fixes and documentation: clearer fallback wording, unused dependency removed, MIT license, AI tool disclosure, challenges and learnings, team contributions, per-step reporting of real Gemma use, Excel and TSV uploads, and text-encoding detection |

The repository's first commit (05:24) is the organizers' submission template, not team work.

### Team Contributions

- **Krishav JS (Team Leader):** Led backend development: the LangGraph investigation pipeline, the deterministic analysis tools and the Gemma integration.
- **Pranav Senthil:** Owned documentation and submission: organized and wrote the README, prepared the MLH submission materials, and managed the repository's branches and merges.
- **Rahul Srinivasan:** Led troubleshooting and debugging: tracked down and fixed issues in the code as the versions came together.
- **Mohal Raj:** Led frontend development: the Streamlit interface, including the dataset overview, verdict display and evidence trace.

## Working Application

**Live Application:** TODO

TODO: how to access the deployed application and what can be tested.

## Demo Video

**Demo Video:** TODO

## Open Source and AI Usage

### AI / Models

- **Gemma 4 (Google),** default model `gemma-4-26b-a4b-it`, called through the Google Gemini API using `langchain-google-genai`. It parses the question, proposes hypotheses, reviews the evidence as a critic, and chooses which supported explanation to lead with. It doesn't compute numbers or assign verdicts. Responses are requested as JSON and validated with Pydantic; the integration doesn't rely on the API's native structured-output mode. See Google's [Gemma on the Gemini API guide](https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api). TODO: confirm a successful live run with Gemma before the demo.
- **AI coding assistants used by the team while building the project:**
  - Claude Code (Anthropic, Claude Opus 5.5): planning, repository setup, testing and documentation
  - OpenAI Codex
  - ChatGPT (OpenAI)
  - Gemini / Gemini CLI (Google)

  The team reviewed, tested and integrated all AI-assisted code. TODO: add what each tool was used for, if known.

### Open Source Components

- **LangGraph:** orchestration of the investigation state machine
- **LangChain (`langchain-google-genai`):** the connection to the Gemma model
- **pandas, NumPy:** data processing and calculations
- **DuckDB:** analytical queries in the comparison tools
- **Pydantic:** validation of structured model output
- **Streamlit:** user interface
- **Plotly:** charts
- **python-dotenv:** loading environment variables
- **openpyxl, xlrd:** reading uploaded Excel files (.xlsx and .xls)
- **chardet:** detecting the text encoding of uploaded CSV and TSV files
- **Demo dataset:** synthetic, created by the team with `data/generate_demo.py`

Licenses, as declared in each package's metadata (versions installed from `requirements.txt` during testing):

| Component | Version tested | License |
|---|---|---|
| Streamlit | 1.65.0 | Apache-2.0 |
| LangGraph | 1.2.14 | MIT |
| langchain-google-genai | 4.4.0 | MIT |
| pandas | 3.0.6 | BSD-3-Clause |
| NumPy | 2.5.3 | BSD-3-Clause (with bundled components under other permissive licenses) |
| Pydantic | 2.13.5 | MIT |
| python-dotenv | 1.2.4 | BSD-3-Clause |
| DuckDB | 1.5.6 | MIT |
| Plotly | 6.9.0 | MIT |
| openpyxl | 3.1.5 | MIT |
| xlrd | 2.0.2 | BSD |
| chardet | 5.2.0 | LGPL (used unmodified, as a separately installed dependency) |

The Gemma models are provided by Google under Google's own terms for Gemma; check the terms for the model version you use. All of these components were developed by their respective authors, not by this team.

## Setup and Usage

### Prerequisites

- Python 3.11+
- Optional: a Google AI Studio API key with access to a Gemma 4 model. Without it, the app runs with the local fallback.

### Installation

```bash
git clone https://github.com/whatsyourname909/hacktoberfest_-hack-day-coimbatore-x-init-club-and-idea-club.git
cd hacktoberfest_-hack-day-coimbatore-x-init-club-and-idea-club
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Environment Variables

```env
GEMMA_API_KEY=
GEMMA_MODEL=gemma-4-26b-a4b-it
```

Copy `.env.example` to `.env` and fill in your key. `.env` is listed in `.gitignore`; never commit it.

### Creating a Source Archive

`.gitignore` only protects files from git, not from zips made by hand. To share the code as a zip, run this from the project root:

```bash
python package_source.py
```

It creates `dist/argue-with-data-source.zip`, leaving out `.env`, `.venv`, `.git`, Python caches, `dist/` and `.streamlit/secrets.toml`.

### Running the Project

```bash
streamlit run app.py
```

To run the tests:

```bash
python -m unittest discover -s tests -v
```

These setup steps were tested on a fresh clone of `main` (macOS, Python 3.13): installation succeeded, all tests passed (9 at the time; there are now 13), and the demo investigation in the app reproduced the verified results above without an API key.

### Usage

1. In the sidebar, pick one of the four demo datasets (sales, marketing, HR attrition, e-commerce) and try its suggested questions, or upload your own file: **CSV, TSV or Excel (.xlsx, .xls)**. CSV and TSV text encodings are detected automatically (UTF-8, Windows-1252, Latin-1 and others). The sidebar shows the dataset profile.
   The sidebar also shows whether a Gemma API key is set; whether Gemma actually answered each step is shown with the results.
2. Type a question, for example "Why did revenue fall in March?".
3. Click **Investigate**.
4. Read the baseline, the hypothesis table with verdicts, and the evidence for each hypothesis, then the final synthesis.

## Challenges and Learnings

- **Code that only worked on one Python version.** An earlier version of the app crashed on Python 3.13 because of an undefined type hint that Python 3.14 never evaluates. Its tests passed for its author and failed for us. **Learning:** run the tests on a fresh clone, on a different machine, before trusting "all tests pass".
- **A Gemma call that never returned.** The first live investigation sat waiting on the Gemini API for minutes, with no error and no timeout, because failed calls were retried silently. **Learning:** every model call needs a timeout and a fast, honest fallback, especially for a live demo. We added a 30-second timeout and a schema-validated local fallback.
- **Keeping the model honest.** Our first designs let the language model decide verdicts after seeing the numbers, the very thing the project argues against. **Learning:** fix the thresholds before the test runs and apply them in code. The model proposes and challenges, but it can't change a verdict.
- **Two versions of the same project.** Team members built separate versions in parallel, and they collided when both were merged into `main`. **Learning:** agree on one base early, work on branches, and merge often.
- **Secrets in shared zips.** A project zip shared between team members included the `.env` file with an API key. `.gitignore` protects git, not zips. **Learning:** share code through the repository or `package_source.py`, never a hand-made zip.

## Devpost Submission

**Devpost Project:** TODO

## Credits and License

### Credits

LangGraph, LangChain, pandas, NumPy, DuckDB, Pydantic, Streamlit, Plotly, python-dotenv, and Google's Gemma models.

### License

This project is licensed under the [MIT License](LICENSE).

## Verification

Run the local checks with:

```bash
python -m unittest discover -s tests -v
```

The 13 tests cover the bundled dataset's baseline, each analysis tool, verification, verdicts, validation of Gemma's JSON, the router's iteration limit, error handling, a complete LangGraph run, question validation, comparisons between two named months, and a full run of every suggested question for all four demo datasets. They run without an API key and don't make live Gemma calls.

## Submission Checklist

- [x] Project title and description added
- [x] All team members listed
- [x] Problem clearly explained
- [x] Reason for choosing the problem explained
- [x] Solution and key features documented
- [x] Innovation and differentiation explained
- [x] Architecture included
- [x] Technical implementation documented
- [x] Work completed during the hackathon documented
- [x] Team contributions documented
- [x] Working application is functional
- [ ] Live application link added where applicable
- [ ] Demo video added
- [x] AI and open-source components documented
- [x] Setup and usage instructions tested
- [x] Challenges and learnings documented
- [ ] Devpost submission completed
- [ ] Devpost link added
- [x] Credits added
- [x] License added
- [ ] Repository is organized and complete
