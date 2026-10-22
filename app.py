"""NEXAI - Code-Mixed Support Triage Assistant (Streamlit).
Run:  streamlit run app.py --server.port 8501
"""
import json
import os
import importlib
from datetime import datetime
import pandas as pd
import streamlit as st

import ticket_store
importlib.reload(ticket_store)
from llm_response import check_api_status, generate_support_reply
from triage_engine import CONF_THRESHOLD, triage

TICKETS_CSV = os.path.join("results", "tickets.csv")
STATS_JSON = os.path.join("results", "dataset_stats.json")
HUMAN_PORTAL_URL = os.getenv("HUMAN_PORTAL_URL", "http://localhost:8502")
LANDING_PAGE_URL = os.getenv("LANDING_PAGE_URL", "http://localhost:8500")

st.set_page_config(page_title="NEXAI Triage", page_icon="📥", layout="wide")

# Custom CSS for attractive, perfectly fitted metrics and response cards
st.markdown("""
<style>
/* Modern, attractive card styling for Streamlit metrics */
div[data-testid="stMetric"] {
    background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 10px 14px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.02);
    min-height: 82px;
}

div[data-testid="stMetric"]:hover {
    border-color: #cbd5e1;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.06);
}

div[data-testid="stMetricLabel"] {
    font-size: 0.80rem !important;
    font-weight: 600 !important;
    color: #64748b !important;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    white-space: nowrap !important;
}

div[data-testid="stMetricValue"] {
    font-size: 1.15rem !important;
    font-weight: 700 !important;
    color: #0f172a !important;
    white-space: normal !important;
    word-break: break-word !important;
    overflow: visible !important;
    line-height: 1.25 !important;
}

.ticket-banner {
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-radius: 8px;
    padding: 12px 16px;
    margin: 10px 0;
}
.ticket-escalated-banner {
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 8px;
    padding: 12px 16px;
    margin: 10px 0;
}
</style>
""", unsafe_allow_html=True)

top_c1, top_c2 = st.columns([5, 1])
with top_c1:
    st.title("NEXAI — Customer Support Portal")
    st.caption(
        "Tanglish / Hinglish / English support messages → Intent classification, urgency detection, "
        "confidence estimation, human escalation, and natural Gemini LLM responses."
    )
with top_c2:
    st.markdown(f"[🏠 **Home**]({LANDING_PAGE_URL})", help="Return to NEXAI Landing Page")

# ---------------- Sidebar Configuration & Status ----------------
st.sidebar.markdown(f"[🏠 **Back to Portal Selection**]({LANDING_PAGE_URL})")
st.sidebar.header("Triage Settings")
default_thr = float(ticket_store.get_setting("confidence_threshold", CONF_THRESHOLD))
threshold = st.sidebar.slider(
    "Confidence threshold (below = Needs human review)",
    0.10, 0.90, default_thr, 0.05
)
st.sidebar.info(
    "ℹ️ **Confidence Score Note:** The confidence score represents the ML model's class probability. "
    "It is a statistical confidence score, not a guarantee of correctness. "
    "Predictions below the threshold trigger human escalation."
)

# LLM Status Indicator
st.sidebar.subheader("Gemini LLM Status")
api_info = check_api_status()
if api_info["configured"]:
    st.sidebar.success(f"🟢 Gemini Connected (`{api_info.get('model')}`)")
else:
    st.sidebar.warning("🟡 Gemini API Key Missing\nConfigure `GEMINI_API_KEY` in `.env` for AI responses.")

st.sidebar.subheader("Human Support Portal")
st.sidebar.markdown(f"Portal Address: [`{HUMAN_PORTAL_URL}`]({HUMAN_PORTAL_URL})")

st.sidebar.warning(
    "⚠️ Trained on synthetic **English** Bitext data plus a small code-mixed word-normalization layer. "
    "Results on our team-written test messages evaluate the system on realistic code-mixed expressions."
)

# Verify model loads
try:
    triage("test message")
except FileNotFoundError as e:
    st.error(str(e))
    st.stop()
except Exception as e:  # noqa: BLE001
    st.error(f"Could not load the model: {e}")
    st.stop()


def load_tickets():
    if os.path.exists(TICKETS_CSV):
        return pd.read_csv(TICKETS_CSV)
    return pd.DataFrame(columns=["time", "message", "language", "intent", "category",
                                 "urgency", "confidence", "escalated"])


def save_ticket(r):
    os.makedirs("results", exist_ok=True)
    row = pd.DataFrame([{
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "message": r["text"],
        "language": r["language"],
        "intent": r["intent"],
        "category": r["category"],
        "urgency": r["urgency"],
        "confidence": round(r["confidence"], 3),
        "escalated": r["escalate"]
    }])
    row.to_csv(TICKETS_CSV, mode="a", header=not os.path.exists(TICKETS_CSV), index=False)


EXAMPLES = [
    "Order vandhuchu but box damaged, refund venum.",
    "Mera payment deduct ho gaya, order confirm nahi hua.",
    "En account login aagala, help pannunga.",
    "Refund innum varala, please check pannunga.",
    "Wrong product deliver pannitanga.",
    "URGENT: mere card se do baar paise kat gaye, ye fraud lagta hai!",
    "Mujhe kisi insaan se baat karni hai",
    "Bro, app romba slow, enna pannalam?",
    "Where is my package? The tracking link is not updating.",
]

tab_inbox, tab_data, tab_tests, tab_dash, tab_feedback = st.tabs(
    ["Triage inbox", "Dataset statistics", "Test suite", "Ticket dashboard", "⭐ Give Feedback"]
)

# ---------------- Triage inbox ----------------
with tab_inbox:
    left, right = st.columns([1, 1.8])
    with left:
        example = st.selectbox("Example complaints", [""] + EXAMPLES)
        msg = st.text_area(
            "Customer complaint",
            value=example,
            height=140,
            placeholder="Type a Tanglish / Hinglish / English complaint here..."
        )
        go = st.button("Triage ticket", type="primary")

    with right:
        if not go and "last_triage" not in st.session_state:
            st.info("Pick an example or type a message, then press **Triage ticket**.")
        elif go and not msg.strip():
            st.warning("Please enter a message first.")
        else:
            # If user pressed go or has current active ticket
            current_msg = msg.strip() if go else st.session_state.get("last_msg", "")

            if go:
                failed = False
                try:
                    r = triage(current_msg, threshold)
                except Exception as e:  # noqa: BLE001
                    r, failed = None, True
                    st.error(f"Something went wrong while triaging this message ({e}). Please route to a human.")

                if r is None and not failed:
                    st.warning("Could not read any valid text in that message. Needs human review.")
                    st.session_state.pop("last_triage", None)
                    st.session_state.pop("current_ticket_id", None)
                elif r is not None:
                    save_ticket(r)
                    st.session_state["last_msg"] = current_msg
                    st.session_state["last_threshold"] = threshold
                    st.session_state["last_triage"] = r

                    # Generate and cache Gemini reply to prevent redundant API calls on reruns
                    with st.spinner("Generating natural AI response via Gemini..."):
                        llm_reply = generate_support_reply(
                            message=current_msg,
                            intent=r["intent"],
                            category=r["category"],
                            urgency=r["urgency"],
                            confidence=r["confidence"],
                            escalate=r["escalate"],
                            escalation_reason=r["escalation_reasons"],
                        )
                    st.session_state["last_llm_reply"] = llm_reply

                    # Automatic Escalation to SQLite Ticket Store
                    run_key = f"{current_msg}_{threshold}"
                    if r["escalate"]:
                        # Avoid duplicate ticket creation on Streamlit reruns
                        if st.session_state.get("escalated_run_key") != run_key:
                            tid = ticket_store.create_ticket(
                                message=current_msg,
                                intent=r["intent"],
                                category=r["category"],
                                urgency=r["urgency"],
                                confidence=r["confidence"],
                                threshold=threshold,
                                escalation_reason=r["escalation_reasons"],
                                llm_acknowledgement=llm_reply,
                            )
                            st.session_state["escalated_run_key"] = run_key
                            st.session_state["current_ticket_id"] = tid
                    else:
                        st.session_state.pop("current_ticket_id", None)
                        st.session_state.pop("escalated_run_key", None)

            # Display active ticket results from session state
            if "last_triage" in st.session_state:
                r = st.session_state["last_triage"]
                llm_reply = st.session_state.get("last_llm_reply", "")
                ticket_id = st.session_state.get("current_ticket_id")

                if r["escalate"]:
                    st.error("⚠️ **NEEDS HUMAN REVIEW**\n\n" + "\n".join(f"- {x}" for x in r["escalation_reasons"]))

                    # Prominent Human Escalation Section
                    if ticket_id:
                        portal_link = f"{HUMAN_PORTAL_URL}/?ticket_id={ticket_id}"
                        st.markdown(f"""
                        <div class="ticket-escalated-banner">
                            <span style="font-weight: 700; color: #1e40af; font-size: 1.05rem;">🎫 Support Ticket Created: <code>{ticket_id}</code></span><br/>
                            <span style="font-size: 0.90rem; color: #1e3a8a;">This ticket has been securely routed to the shared Human Support Portal.</span>
                        </div>
                        """, unsafe_allow_html=True)

                        btn_col1, btn_col2 = st.columns([1.5, 1])
                        with btn_col1:
                            st.link_button(
                                "🚀 Get Human Support (Open Portal)",
                                url=portal_link,
                                type="primary",
                                help="Opens the Human Support Portal with your ticket selected"
                            )
                        with btn_col2:
                            if st.button("🔄 Check Ticket Status", key="refresh_ticket_status"):
                                st.session_state["status_checked"] = True

                        # Live Status Check from Shared Database
                        db_ticket = ticket_store.get_ticket(ticket_id)
                        if db_ticket:
                            st.caption(f"Current Status: **{db_ticket['status']}** | Last updated: `{db_ticket['updated_at']}`")
                            if db_ticket.get("agent_response"):
                                st.success(f"💬 **Human Specialist Response:**\n\n{db_ticket['agent_response']}")
                            elif db_ticket["status"] == "Open":
                                st.info("ℹ️ Your ticket is currently queued for an available specialist.")
                else:
                    st.success("✅ **Confident prediction — auto-handled**")

                c1, c2, c3, c4 = st.columns([1.4, 1.1, 0.9, 1.1])
                c1.metric("Intent" + (" (uncertain)" if r["escalate"] else ""), r["intent"])
                urg_icons = {"High": "🔴 High", "Medium": "🟠 Medium", "Low": "🟢 Low"}
                c2.metric("Urgency", urg_icons.get(r["urgency"], r["urgency"]))
                c3.metric("Confidence", f"{r['confidence']:.0%}")
                c4.metric("Language mix", r["language"])

                st.caption(
                    f"Category: **{r['category']}** | Top 3 intents: " +
                    ", ".join(f"{i} ({p:.0%})" for i, p in r["top3"])
                )

                # Gemini AI Response Section
                st.subheader(
                    "🤖 Gemini AI Response" +
                    (" (Human review acknowledgement draft)" if r["escalate"] else " (Draft reply)")
                )
                st.info(llm_reply)

                # Explainability & Offline Details
                with st.expander("🔍 Why this result? (urgency rules, code-mixed normalization, offline template)"):
                    st.write("**Urgency rules that fired:**", "; ".join(r["urgency_reasons"]))
                    st.write("**Text the model actually saw after code-mixed normalization:**", r["normalized"])
                    st.write("**Offline fallback template:**")
                    st.text_area("Offline template draft", r["reply"], height=80, disabled=True)
                    st.write("**Most similar training examples:**")
                    st.dataframe(pd.DataFrame(r["similar"]))

# ---------------- Dataset stats ----------------
with tab_data:
    if not os.path.exists(STATS_JSON):
        st.info("Run `python train_model.py` to generate dataset statistics.")
    else:
        with open(STATS_JSON, encoding="utf-8") as f:
            s = json.load(f)
        a, b, c = st.columns(3)
        a.metric("Rows (after cleaning)", f"{s['rows_total']:,}")
        b.metric("Intents", s["n_intents"])
        c.metric("Categories", s["n_categories"])
        st.subheader("Intent distribution")
        st.bar_chart(pd.Series(s["intent_counts"]))
        st.subheader("Category distribution")
        st.bar_chart(pd.Series(s["category_counts"]))
        st.caption(
            "Bitext is a synthetic English customer-support dataset. It was not collected from real "
            "Tanglish/Hinglish customers."
        )

# ---------------- Test suite ----------------
with tab_tests:
    from test_cases import run_tests
    df = run_tests(threshold, save=False)
    n = len(df)
    a, b, c, d = st.columns(4)
    a.metric("Test messages", n)
    b.metric("Intent pass rate", f"{df.intent_ok.mean():.0%} ({int(df.intent_ok.sum())}/{n})")
    c.metric("Urgency pass rate", f"{df.urgency_ok.mean():.0%}")
    d.metric("Needs human review", int(df.escalated.sum()))
    show = df[["message", "expected_intent", "predicted_intent", "intent_ok", "confidence",
               "status", "predicted_urgency", "language", "label_note"]]
    st.dataframe(show)
    st.caption(
        "These are team-written Tanglish/Hinglish examples, **not** a representative benchmark of "
        "Indian languages. Cases with a 'Fallback' note use the closest existing Bitext label because "
        "no exact intent exists."
    )

# ---------------- Ticket dashboard ----------------
with tab_dash:
    t = load_tickets()
    if t.empty:
        st.info("No tickets yet. Submit some messages in the Triage inbox tab.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Tickets", len(t))
        c2.metric("Needs human review", int(t.escalated.astype(str).str.lower().eq("true").sum()))
        c3.metric("Avg confidence", f"{t.confidence.mean():.0%}")
        st.subheader("Ticket volume by intent")
        st.bar_chart(t.intent.value_counts())
        st.subheader("Ticket volume by urgency")
        st.bar_chart(t.urgency.value_counts().reindex(["High", "Medium", "Low"]).fillna(0))
        st.subheader("Intent × urgency")
        st.dataframe(pd.crosstab(t.intent, t.urgency))
        st.subheader("Recent tickets")
        st.dataframe(t.tail(20).iloc[::-1])

# ---------------- Give Feedback ----------------
def _submit_customer_feedback(rating: int, category: str, message: str = "", ticket_id: str = "") -> str:
    """Submit customer feedback through the shared SQLite store."""
    return ticket_store.create_feedback(
        rating=rating,
        category=category,
        message=message,
        ticket_id=ticket_id,
    )

with tab_feedback:
    st.subheader("⭐ Customer Feedback")
    st.caption("Help us improve the NEXAI Code-Mixed Triage Assistant. Share your experience with our AI triage and support.")

    # Feedback Form
    with st.form("customer_feedback_form"):
        fb_c1, fb_c2 = st.columns(2)
        with fb_c1:
            rating = st.select_slider(
                "Overall Experience Rating",
                options=[1, 2, 3, 4, 5],
                value=5,
                format_func=lambda x: f"{x} Star{'s' if x > 1 else ''} {'⭐' * x}"
            )
        with fb_c2:
            category = st.selectbox(
                "Feedback Category",
                [
                    "AI Response Quality",
                    "Triage Speed & Accuracy",
                    "Language Understanding (Tanglish/Hinglish)",
                    "Human Support Experience",
                    "General Feedback"
                ]
            )

        fb_ticket_id = st.text_input(
            "Associated Ticket ID (Optional)",
            value=st.session_state.get("current_ticket_id", "") or "",
            placeholder="e.g. TICK-A1B2C3"
        )

        fb_comments = st.text_area(
            "Your Comments / Suggestions",
            height=110,
            placeholder="Let us know what worked well or what we can improve..."
        )

        submit_fb = st.form_submit_button("Submit Feedback", type="primary")

    if submit_fb:
        # Prevent duplicate submissions on reruns
        fb_key = f"{rating}_{category}_{fb_ticket_id.strip()}_{fb_comments.strip()}"
        if st.session_state.get("last_fb_submission_key") == fb_key:
            st.info(f"✅ Your feedback has already been submitted (ID: `{st.session_state.get('last_fb_id')}`).")
        else:
            fb_id = _submit_customer_feedback(
                rating=rating,
                category=category,
                message=fb_comments,
                ticket_id=fb_ticket_id
            )
            st.session_state["last_fb_submission_key"] = fb_key
            st.session_state["last_fb_id"] = fb_id
            st.success(f"✅ Thank you! Your feedback has been recorded successfully. Reference ID: `{fb_id}`")

