# Velnex AI — Website Chat Agent

Streamlit + Groq + Gmail SMTP. No Google Sheets, no admin panel — just a
focused chatbot that answers questions about Velnex AI and, when someone
wants pricing or to start a project, collects their contact info and
emails it to you directly.

## What it does

1. Answers questions about Velnex AI's services, process, and privacy
   policy — and politely declines anything unrelated (weather, homework,
   other topics), staying on-topic.
2. If someone asks about pricing or says they want to buy/get started,
   it collects: name, email, phone, and a short project description.
3. Once it has all four, it emails you the details and tells the user
   the owner will personally follow up.

## Setup steps

### 1. Fill in secrets

Copy `secrets.toml.example` → rename to `secrets.toml`, fill in:
- `GROQ_API_KEY` — your Groq API key
- `SENDER_EMAIL` / `SENDER_PASSWORD` — a Gmail account + App Password
  (reuse the same one from your dental project if you like)
- `OWNER_EMAIL` — where contact requests should land (your inbox)

Never commit the real `secrets.toml` to GitHub.

### 2. Deploy

1. Push this folder to a new GitHub repo (e.g. `velnex-ai-agent`)
2. Streamlit Cloud → New app → point it at that repo → `app.py`
3. Paste your filled-in `secrets.toml` contents into the app's "Secrets" box
4. Deploy — you'll get a live URL to embed on your website

## Editing the AI's knowledge or behavior

Everything — scope rules, services, privacy policy wording, and exactly
when it asks for contact details — lives in the `SYSTEM_PROMPT` variable
near the top of `app.py`. Edit that text directly to change what it says
or how strict its topic boundaries are.

## Files in this folder

- `app.py` — the whole app
- `requirements.txt` — just `streamlit` and `groq`
- `secrets.toml.example` — template for your credentials
