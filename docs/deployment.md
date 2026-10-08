# Deploying to Streamlit Community Cloud

This gives the project a public link for the README's "Live Application" and the MLH submission. It takes about 10 minutes. Streamlit Community Cloud is free for public repositories.

## Before you start

- The repository must be **public**. It already is.
- Deploy from the **`main`** branch, since that's what judges see.
- Have the **Gemma API key** ready (from Google AI Studio). It goes into Streamlit's Secrets, **never** into the repository.

## Steps

1. Go to **https://share.streamlit.io** and sign in with the GitHub account that can see the repository.
2. Click **Create app**, then choose to deploy a public app from a GitHub repository.
3. Fill in:
   - **Repository:** `whatsyourname909/hacktoberfest_-hack-day-coimbatore-x-init-club-and-idea-club`
   - **Branch:** `main`
   - **Main file path:** `app.py`
   - **App URL:** pick a short, readable name, for example `argue-with-my-data`
4. Open **Advanced settings**:
   - **Python version:** 3.11 or newer. The project was tested on 3.13.
   - **Secrets:** paste the following, with your real key:

     ```toml
     GEMMA_API_KEY = "your-key-here"
     GEMMA_MODEL = "gemma-4-26b-a4b-it"
     ```

     Streamlit also exposes top-level secrets like these as environment variables, which is how the app reads them, so no code changes are needed.
5. Click **Deploy**. The first build installs everything in `requirements.txt` and takes a few minutes.

## Check that it works

1. Open the app's URL. The sidebar should show **"🔑 Gemma API key set"** and the model name.
2. With the demo dataset selected, click the example **"Why did revenue fall in March?"**, then **Investigate**.
3. Check the results:
   - Baseline: 10,000,000 → 7,940,000 (−20.6%)
   - Customer: 8.0%, WEAKENED. Product mix: 67.0%, SUPPORTED. Region: 14.0%, WEAKENED. Data quality: REJECTED. Seasonality: UNTESTABLE.
   - The line **"Gemma AI actively used for:"** shows which steps Gemma really answered. **If every step says NO, Gemma isn't working** (wrong key, wrong model name, or the model isn't available on that key), and the app is running on its local fallback.

## After deploying

- Put the URL in the README under **Working Application → Live Application**, and in the MLH submission's demo link. Send it to Pranav, who can update the README.
- Apps on the free tier go to sleep when nobody uses them for a while. **Open the link shortly before judging** so it's awake.
- If you ever change the key, update it under the app's **Settings → Secrets**. Never commit it.

## If something goes wrong

| Problem | What to check |
|---|---|
| The build fails while installing packages | The Python version in Advanced settings (use 3.11 or newer), then redeploy |
| "Gemma API not configured" in the sidebar | The Secrets weren't saved, or `GEMMA_API_KEY` is misspelled |
| Every Gemma step says NO | The key is invalid, or `GEMMA_MODEL` isn't available for that key. Try the investigation locally with the same key to compare. |
| The app is slow to open | It was asleep. Wait for it to wake up, then reload. |
