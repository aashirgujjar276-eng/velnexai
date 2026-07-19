import streamlit as st
import json
import re
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
from groq import Groq

# ---------------------------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Velnex AI — Chat with us", page_icon="🤖", layout="centered")

# ---------------------------------------------------------------------------
# SYSTEM PROMPT — everything the AI knows about Velnex AI lives here
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """
You are the AI assistant for Velnex AI, an agency that builds custom AI
chatbots and AI agents for businesses (like AI receptionists, customer
support bots, and automated booking assistants).

STRICT SCOPE — READ CAREFULLY
- You ONLY answer questions related to Velnex AI: our services, how AI
  agents work, our process, privacy policy, or how to get started/buy.
- If someone asks anything unrelated to Velnex AI or AI agents (general
  knowledge, homework, unrelated coding help, personal advice, other
  companies, jokes, etc.), politely decline and steer back, e.g.:
  "I'm just here to help with Velnex AI and our services — is there
  something about that I can help with?"
- Do not answer unrelated questions even if the user insists or rephrases.

WHAT VELNEX AI DOES
- Builds custom AI chatbots and AI agents for businesses across any
  industry — AI receptionists, customer support bots, lead-capture
  agents, and automated booking assistants
- Each agent is tailored to the client's specific business needs
- Examples: AI receptionists for clinics, agents connected to email/SMS/
  booking systems, and full automation workflows

PRIVACY POLICY (tell users this if asked)
- Information shared in this chat (name, email, phone, project details)
  is only used to contact you about your inquiry
- We do not sell or share your information with third parties
- Your details are stored securely and only accessed by the Velnex AI team

PRICING AND BUYING — IMPORTANT
- Never quote a specific price or price range under any circumstances
- If someone asks about pricing, cost, or says they want to buy/start a
  project, tell them pricing is custom-scoped, and that you'll take a few
  details so the owner can follow up directly with a quote
- In that case, collect exactly these four things, one at a time if needed:
  1. Full name
  2. Email address
  3. Phone number
  4. A short description of what they want built/what their business needs
- Once you have all four, confirm the details back to the user, tell them
  the owner will personally review and reply soon, and end your reply with
  exactly this line:
  [LEAD] Name: <name> | Email: <email> | Phone: <phone> | Description: <description>

GENERAL BEHAVIOR
- Be professional, confident, and concise — you are the first impression
  of a real AI agency
- Don't force the contact-form questions on someone just browsing or
  asking casual questions about what Velnex AI does
- Only start collecting contact details once they've clearly asked about
  pricing or said they want to move forward
""".strip()

# ---------------------------------------------------------------------------
# CLIENT
# ---------------------------------------------------------------------------
client = Groq(api_key=st.secrets["GROQ_API_KEY"])


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------
def parse_lead(reply_text: str):
    """Extract the [LEAD] line into a dict, or None if not present."""
    match = re.search(r"\[LEAD\]\s*(.+)", reply_text)
    if not match:
        return None

    fields_text = match.group(1)
    parts = [p.strip() for p in fields_text.split("|")]
    lead = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    for part in parts:
        if ":" in part:
            key, value = part.split(":", 1)
            lead[key.strip().lower()] = value.strip()
    return lead


def send_email_notification(lead: dict):
    """Email the owner using Gmail SMTP with an App Password."""
    try:
        sender_email = st.secrets["SENDER_EMAIL"]
        sender_password = st.secrets["SENDER_PASSWORD"]
        owner_email = st.secrets["OWNER_EMAIL"]

        body = (
            f"New contact request from the Velnex AI website chat!\n\n"
            f"Name: {lead.get('name', 'N/A')}\n"
            f"Email: {lead.get('email', 'N/A')}\n"
            f"Phone: {lead.get('phone', 'N/A')}\n"
            f"Description: {lead.get('description', 'N/A')}\n"
            f"Submitted at: {lead.get('timestamp', 'N/A')}\n"
        )

        msg = MIMEText(body)
        msg["Subject"] = f"New Velnex AI Contact Request: {lead.get('name', 'Unknown')}"
        msg["From"] = sender_email
        msg["To"] = owner_email

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, owner_email, msg.as_string())
        return True
    except Exception as e:
        st.session_state.setdefault("errors", []).append(f"Email error: {e}")
        return False


def get_ai_reply(messages):
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        max_tokens=600,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
    )
    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------------------------------------------------------------------------
# UI — HEADER
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div style="text-align:center; padding: 10px 0 20px 0;">
        <h1 style="margin-bottom:0;">🤖 Velnex AI</h1>
        <p style="color:#666; margin-top:4px;">Ask us anything about our AI agents and services</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# CHAT HISTORY
# ---------------------------------------------------------------------------
for msg in st.session_state.messages:
    avatar = "🧑" if msg["role"] == "user" else "🤖"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["display_content"])

# ---------------------------------------------------------------------------
# CHAT INPUT
# ---------------------------------------------------------------------------
user_input = st.chat_input("Type your message here...")

if user_input:
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "display_content": user_input,
    })
    with st.chat_message("user", avatar="🧑"):
        st.markdown(user_input)

    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Thinking..."):
            api_messages = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ]
            reply = get_ai_reply(api_messages)

        lead = parse_lead(reply)
        display_reply = reply.split("[LEAD]")[0].strip() if lead else reply

        st.markdown(display_reply)

        if lead:
            email_ok = send_email_notification(lead)
            if email_ok:
                st.success("Thanks! The owner has been notified and will reply soon.")
            else:
                st.info("Thanks for the details — please also feel free to reach out directly if you don't hear back soon.")

    st.session_state.messages.append({
        "role": "assistant",
        "content": reply,
        "display_content": display_reply,
    })
