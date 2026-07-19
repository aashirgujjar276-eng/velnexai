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
# DARK MODE TOGGLE
# ---------------------------------------------------------------------------
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

toggle_col1, toggle_col2 = st.columns([5, 1])
with toggle_col2:
    st.session_state.dark_mode = st.toggle("🌙", value=st.session_state.dark_mode)

if st.session_state.dark_mode:
    st.markdown(
        """
        <style>
        .stApp {
            background-color: #0a1420 !important;
        }
        .stApp, .stApp p, .stApp li, .stApp span, .stApp label {
            color: #e8f0fe !important;
        }
        [data-testid="stChatMessage"] {
            background-color: #142943 !important;
            border-radius: 12px;
        }
        [data-testid="stChatInput"] textarea {
            background-color: #142943 !important;
            color: #e8f0fe !important;
        }
        .stButton button {
            background-color: #142943 !important;
            color: #e8f0fe !important;
            border: 1px solid #2a4a6b !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

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
  project, tell them pricing is custom-scoped, and ask them for these four
  things, one at a time if needed:
  1. Full name
  2. Email address
  3. Phone number
  4. A short description of what they want built/what their business needs
- CRITICAL RULE: Do NOT include the [LEAD] tag in the same message where
  you are asking these questions. Only include it in a LATER message,
  after the user has actually replied with their real name, real email,
  real phone number, and real description in their own words.
- NEVER write the [LEAD] tag with placeholder or example text of any kind.
  Only write it once you have the user's real, actual answers copied
  directly from what they typed.
- Once the user has given you all four real answers (across one or more
  of their own messages), confirm the details back to them, tell them the
  owner will personally review and reply soon, and only then end your
  reply with a line in this exact format, replacing each field with the
  user's real answer:
  [LEAD] Name: (their real name) | Email: (their real email) | Phone: (their real phone) | Description: (their real description)

GENERAL BEHAVIOR
- Be professional, confident, and concise — you are the first impression
  of a real AI agency
- Always reply in the same language the user is writing in. You are
  fluent in English, Spanish, and French — the most common languages
  among Velnex AI's US and Canadian visitors. If someone writes in
  Spanish, reply fully in Spanish; if French, reply fully in French.
  Never mix languages in a single reply unless the user does.
- If a lead is captured ([LEAD] tag), always write the tag itself in
  English regardless of the conversation language, so the owner can
  read it easily — only the visible reply to the user should be in
  their language.
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


def is_lead_valid(lead: dict) -> bool:
    """Reject placeholder/empty data so we never email junk leads."""
    required = ["name", "email", "phone", "description"]
    placeholder_markers = ["<", ">", "your name", "your email", "your phone",
                            "example", "xxx", "n/a", "unknown"]

    for field in required:
        value = lead.get(field, "").strip().lower()
        if not value:
            return False
        if any(marker in value for marker in placeholder_markers):
            return False

    # basic sanity checks
    if "@" not in lead.get("email", ""):
        return False
    if not any(ch.isdigit() for ch in lead.get("phone", "")):
        return False

    return True


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


def stream_ai_reply(messages):
    """Yields text chunks as they arrive, for use with st.write_stream."""
    stream = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        max_tokens=600,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


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
    <style>
    .velnex-hero {
        position: relative;
        overflow: hidden;
        background: linear-gradient(135deg, #0a2540 0%, #1565c0 55%, #7ec8f2 100%);
        border-radius: 20px;
        padding: 40px 30px;
        margin-bottom: 25px;
        text-align: center;
    }
    .velnex-hero::before {
        content: "";
        position: absolute;
        top: -60px; left: -60px;
        width: 220px; height: 220px;
        background: rgba(10, 37, 64, 0.55);
        border-radius: 50%;
    }
    .velnex-hero::after {
        content: "";
        position: absolute;
        bottom: -50px; right: -50px;
        width: 160px; height: 160px;
        background: rgba(255, 255, 255, 0.15);
        border-radius: 50%;
    }
    .velnex-logo-row {
        position: relative;
        z-index: 2;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 14px;
    }
    .velnex-title {
        color: white;
        font-size: 2.4rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .velnex-tagline {
        position: relative;
        z-index: 2;
        color: #cfe6ff;
        margin-top: 8px;
        font-size: 1rem;
    }
    </style>

    <div class="velnex-hero">
        <div class="velnex-logo-row">
            <svg width="46" height="46" viewBox="0 0 100 100">
                <polygon points="10,15 35,15 50,55 65,15 90,15 58,85 42,85" fill="#1b4d3e"/>
                <polygon points="50,40 62,40 50,68 38,40" fill="#d9a441"/>
            </svg>
            <h1 class="velnex-title">Velnex Ai</h1>
        </div>
        <p class="velnex-tagline">Ask us anything about our AI agents and services</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# CHAT HISTORY
# ---------------------------------------------------------------------------
for msg in st.session_state.messages:
    avatar = "🧑" if msg["role"] == "user" else "velnex_logo.png"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["display_content"])

# Auto-scroll anchor — keeps the latest message in view
st.markdown('<div id="bottom-anchor"></div>', unsafe_allow_html=True)
st.markdown(
    """
    <script>
    var anchor = window.parent.document.getElementById("bottom-anchor");
    if (anchor) { anchor.scrollIntoView({behavior: "smooth", block: "end"}); }
    </script>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# QUICK-REPLY SUGGESTIONS (shown only before the first message)
# ---------------------------------------------------------------------------
if "pending_input" not in st.session_state:
    st.session_state.pending_input = None

if len(st.session_state.messages) == 0:
    st.markdown("<p style='color:#888; font-size:0.9rem;'>Quick start:</p>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("What do you offer?", use_container_width=True):
            st.session_state.pending_input = "What do you offer?"
    with col2:
        if st.button("Pricing", use_container_width=True):
            st.session_state.pending_input = "How does pricing work?"
    with col3:
        if st.button("Get started", use_container_width=True):
            st.session_state.pending_input = "I want to get started, how do I begin?"

# ---------------------------------------------------------------------------
# CHAT INPUT
# ---------------------------------------------------------------------------
user_input = st.chat_input("Type your message here...")

if not user_input and st.session_state.pending_input:
    user_input = st.session_state.pending_input
    st.session_state.pending_input = None

if user_input:
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "display_content": user_input,
    })
    with st.chat_message("user", avatar="🧑"):
        st.markdown(user_input)

    with st.chat_message("assistant", avatar="velnex_logo.png"):
        api_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages
        ]

        placeholder = st.empty()
        full_text = ""
        visible_so_far = ""
        stream_failed = False

        for attempt in range(2):  # try once, retry once on failure
            try:
                full_text = ""
                for chunk in stream_ai_reply(api_messages):
                    full_text += chunk
                    visible_so_far = full_text.split("[LEAD]")[0].strip()
                    placeholder.markdown(visible_so_far + "▌")
                placeholder.markdown(visible_so_far)
                stream_failed = False
                break
            except Exception as e:
                stream_failed = True
                st.session_state.setdefault("errors", []).append(f"AI error (attempt {attempt + 1}): {e}")

        if stream_failed:
            visible_so_far = (
                "Sorry, I'm having trouble connecting right now. "
                "Please try again in a moment, or email us directly and "
                "we'll get back to you."
            )
            placeholder.markdown(visible_so_far)
            full_text = visible_so_far

        reply = full_text
        lead = parse_lead(reply) if not stream_failed else None
        display_reply = visible_so_far

        if not stream_failed:
            st.toast("New message from Velnex AI", icon="💬")

        if lead and is_lead_valid(lead):
            email_ok = send_email_notification(lead)
            if email_ok:
                st.success("Thanks! The owner has been notified and will reply soon.")
            else:
                st.info("Thanks for the details — please also feel free to reach out directly if you don't hear back soon.")
        elif lead and not is_lead_valid(lead):
            # AI tried to tag a lead before real data was collected — ignore it,
            # no email sent, chat continues normally so the AI can keep asking.
            st.session_state.setdefault("errors", []).append(
                f"Blocked incomplete/placeholder lead: {lead}"
            )

    st.session_state.messages.append({
        "role": "assistant",
        "content": reply,
        "display_content": display_reply,
    })
