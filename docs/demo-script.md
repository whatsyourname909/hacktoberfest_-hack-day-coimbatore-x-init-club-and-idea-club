# Demo video script (about 2 minutes)

For the submission's demo video. Record the screen with the app open, ideally the deployed version. Practise once before recording.

**Before recording**

- Open the app and wait until it has fully loaded. If it's the deployed version, open it a minute early so it's awake.
- In the sidebar, choose **Select Demo Dataset** and pick **Sales Revenue Analysis**.
- Close other tabs and notifications.
- Decide honestly which version you're showing:
  - **With Gemma working:** the **AI Pipeline Status** panel shows green dots and a count above 0/5 stages. Use the Gemma lines below.
  - **Without Gemma:** say that this run uses the offline fallback. Don't claim Gemma produced it.

---

## 0:00–0:15 · Introduction

> "Hi, we're Training with Vibes, and this is our demo for **Hacktoberfest Hack Day Coimbatore**, hosted by INIT Club and iDEA Club with MLH. Our project is **Argue With My Data**."

*(MLH asks for the event name at the start of demo videos.)*

## 0:15–0:35 · The problem

> "AI data tools are good at giving a plausible explanation, but plausible isn't the same as correct. If revenue drops right after a big customer leaves, an AI will happily blame that customer, even when they explain only a small part of the drop. We built an analyst that has to try to prove its own explanations wrong before it answers."

## 0:35–0:50 · The data and question

*Show the sidebar's dataset overview, then click the suggested query **"Why did revenue fall in March?"**.*

> "Here's a sales dataset. A customer stopped ordering in March, so that's the obvious suspect. Let's ask why revenue fell."

*Click **Execute Analysis**.*

## 0:50–1:05 · The baseline

*Point at the baseline comparison.*

> "First, code, not the AI, calculates what actually changed: revenue fell from 10 million to 7.94 million, down 20.6%."

## 1:05–1:35 · The key moment: the verdicts

*Scroll to the hypothesis verdicts. Pause on the customer line.*

> "It tested five competing explanations. The obvious one, the lost customer, accounts for only **8%** of the drop, so it's **weakened**, not confirmed."

*Move to the product line.*

> "The real driver is a **product mix shift**, customers moving to cheaper products, which accounts for **67%**. That's **supported**."

> "Regions explain 14% at most, data quality is ruled out, and seasonality is **untestable**, because two months of data can't show a seasonal pattern. It says so, instead of guessing."

## 1:35–1:50 · Why you can trust it

*Open one item in the **Evidence Trace**, then point at the **Synthesis** and "All calculations independently verified".*

> "Every verdict comes from thresholds fixed before the test ran, and every number is recalculated and verified. The final answer talks about contribution, never causation."

**If Gemma was used**, point at the **AI Pipeline Status** panel:

> "Gemma 4 interprets the question, proposes the explanations and challenges the evidence as a critic, but it never does the maths and can't change a verdict."

**If running on the fallback**, say instead:

> "Gemma 4 normally interprets the question and acts as the critic; this run uses our offline fallback, and the verdicts are still calculated the same way."

## 1:50–2:00 · Close

> "LLM proposes, code tests, the critic challenges, and the evidence decides. That's Argue With My Data. Thanks for watching!"

---

**After recording:** upload it (YouTube unlisted or public, or a shared Google Drive link that anyone can view), then send the link to Pranav for the README and the MLH submission. The video should stay public after the event.
