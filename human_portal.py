"""NEXAI - Human Support Portal.

Standalone agent dashboard for support representatives to inspect, manage,
and resolve customer complaints escalated by the NEXAI triage engine.

Run:
    python -m streamlit run human_portal.py --server.port 8502
"""
import os
import importlib
import pandas as pd
import streamlit as st

import ticket_store
importlib.reload(ticket_store)

LANDING_PAGE_URL = os.getenv("LANDING_PAGE_URL", "http://localhost:8500")

st.set_page_config(
    page_title="NEXAI — Human Support Portal",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for Agent Portal
st.markdown("""
<style>
/* Modern agent portal metrics and cards */
div[data-testid="stMetric"] {
    background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 10px 14px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}
div[data-testid="stMetricLabel"] {
    font-size: 0.80rem !important;
    font-weight: 600 !important;
    color: #475569 !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
div[data-testid="stMetricValue"] {
    font-size: 1.35rem !important;
    font-weight: 700 !important;
    color: #0f172a !important;
}

/* Ticket detail containers */
.agent-complaint-box {
    background-color: #f1f5f9;
    border-left: 4px solid #64748b;
    border-radius: 6px;
    padding: 12px 16px;
    font-size: 1.05rem;
    font-weight: 500;
    color: #1e293b;
    margin-bottom: 15px;
}

.agent-notes-box {
    background-color: #fffbeb;
    border: 1px solid #fde68a;
    border-radius: 6px;
    padding: 10px 14px;
    font-size: 0.92rem;
    color: #92400e;
    margin-top: 10px;
}

.badge-open {
    background-color: #fee2e2;
    color: #991b1b;
    padding: 4px 10px;
    border-radius: 9999px;
    font-size: 0.85rem;
    font-weight: 600;
}
.badge-in-review {
    background-color: #fef3c7;
    color: #92400e;
    padding: 4px 10px;
    border-radius: 9999px;
    font-size: 0.85rem;
    font-weight: 600;
}
.badge-resolved {
    background-color: #dcfce7;
    color: #166534;
    padding: 4px 10px;
    border-radius: 9999px;
    font-size: 0.85rem;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# Header
top_c1, top_c2 = st.columns([5, 1])
with top_c1:
    st.title("🛡️ NEXAI Human Support Portal")
    st.caption(
        "Dedicated Agent Interface for escalated Code-Mixed (Tanglish / Hinglish / English) support tickets."
    )
with top_c2:
    st.markdown(f"[🏠 **Home**]({LANDING_PAGE_URL})", help="Return to NEXAI Landing Page")

# Sidebar navigation & status
st.sidebar.markdown(f"[🏠 **Back to Portal Selection**]({LANDING_PAGE_URL})")
st.sidebar.header("Agent Controls")
st.sidebar.info(
    "🔒 **Role Separation Notice:** This portal is strictly for human support agents. "
    "Internal notes and ticket management actions are isolated from the customer-facing interface."
)

# Check URL Query Parameter for Direct Ticket Link
query_ticket_id = st.query_params.get("ticket_id", None)
if isinstance(query_ticket_id, list):
    query_ticket_id = query_ticket_id[0] if query_ticket_id else None

# Refresh button in sidebar
if st.sidebar.button("🔄 Refresh Queue"):
    st.rerun()

# ----------------- TICKET DETAIL VIEW -----------------
def render_ticket_detail(ticket: dict):
    tid = ticket["ticket_id"]
    status = ticket["status"]
    urgency = ticket["urgency"]

    col_back, col_title = st.columns([1, 6])
    with col_back:
        if st.button("⬅️ All Tickets"):
            st.query_params.clear()
            st.rerun()
    with col_title:
        status_badges = {
            "Open": "🔴 OPEN",
            "In Review": "🟠 IN REVIEW",
            "Waiting for Customer": "🟡 WAITING FOR CUSTOMER",
            "Resolved": "🟢 RESOLVED",
        }
        st.subheader(f"Ticket {tid}  [{status_badges.get(status, status)}]")

    # Meta Overview Cards
    c1, c2, c3, c4 = st.columns([1.2, 1, 1, 1.2])
    c1.metric("Predicted Intent", ticket["intent"])
    urg_icons = {"High": "🔴 High", "Medium": "🟠 Medium", "Low": "🟢 Low"}
    c2.metric("Urgency Level", urg_icons.get(urgency, urgency))
    c3.metric("Classifier Conf.", f"{ticket['confidence']:.0%}")
    c4.metric("Created", ticket["created_at"].split()[1] if " " in ticket["created_at"] else ticket["created_at"])

    st.markdown("---")

    left_col, right_col = st.columns([1.2, 1])

    with left_col:
        st.markdown("### 📝 Customer Complaint")
        st.markdown(f'<div class="agent-complaint-box">"{ticket["message"]}"</div>', unsafe_allow_html=True)

        st.markdown("### ⚠️ Escalation Diagnosis")
        st.error(f"**Reasons for Escalation:**\n\n{ticket['escalation_reason']}")
        st.caption(f"Safety Threshold: **{ticket['threshold']:.0%}** | Category: **{ticket['category']}**")

        if ticket.get("llm_acknowledgement"):
            st.markdown("### 🤖 Customer LLM Holding Acknowledgement")
            st.info(f"Draft generated for customer:\n\n_{ticket['llm_acknowledgement']}_")

    with right_col:
        st.markdown("### 🛠️ Agent Response & Action")
        with st.form(key=f"form_{tid}"):
            f_c1, f_c2 = st.columns(2)
            with f_c1:
                new_status = st.selectbox(
                    "Ticket Status",
                    ticket_store.VALID_STATUSES,
                    index=ticket_store.VALID_STATUSES.index(status) if status in ticket_store.VALID_STATUSES else 0
                )
            with f_c2:
                active_agents = ticket_store.get_agents(only_active=True)
                agent_names = ["Unassigned"] + [a["name"] for a in active_agents]
                cur_agent = ticket.get("assigned_agent") or "Unassigned"
                cur_idx = agent_names.index(cur_agent) if cur_agent in agent_names else 0
                new_agent = st.selectbox("Assigned Specialist", agent_names, index=cur_idx)

            agent_reply = st.text_area(
                "Official Response to Customer",
                value=ticket.get("agent_response", "") or "",
                height=120,
                placeholder="Type the verified resolution or follow-up question here..."
            )

            internal_notes = st.text_area(
                "Internal Agent Notes (Private — not visible to customer)",
                value=ticket.get("internal_notes", "") or "",
                height=80,
                placeholder="Log internal diagnostics, supervisor checks, or transaction IDs here..."
            )

            b_col1, b_col2 = st.columns(2)
            with b_col1:
                save_clicked = st.form_submit_button("💾 Save Update", type="primary")
            with b_col2:
                resolve_clicked = st.form_submit_button("✅ Mark as Resolved")

            if save_clicked:
                ticket_store.update_ticket(
                    ticket_id=tid,
                    status=new_status,
                    agent_response=agent_reply,
                    internal_notes=internal_notes,
                    assigned_agent=new_agent
                )
                st.success("✅ Ticket successfully updated!")
                st.rerun()

            if resolve_clicked:
                ticket_store.update_ticket(
                    ticket_id=tid,
                    status="Resolved",
                    agent_response=agent_reply,
                    internal_notes=internal_notes,
                    assigned_agent=new_agent
                )
                st.success("✅ Ticket marked as RESOLVED!")
                st.rerun()

    # Activity Timeline & Audit
    with st.expander("🕒 Ticket Metadata & Audit Details"):
        st.write(f"- **Ticket ID:** `{tid}`")
        st.write(f"- **Original Creation Timestamp:** `{ticket['created_at']}`")
        st.write(f"- **Last Updated:** `{ticket['updated_at']}`")
        st.write(f"- **Current Internal Notes:** {ticket.get('internal_notes') or 'None logged.'}")


# ----------------- QUEUE / DASHBOARD VIEW -----------------
stats = ticket_store.get_stats()

# Metric summary row
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Total Tickets", stats["total"])
m2.metric("🔴 Open", stats["open"])
m3.metric("🟠 In Review", stats["in_review"])
m4.metric("🚨 High Urgency", stats["high_urgency"])
m5.metric("🟢 Resolved", stats["resolved"])

st.markdown("---")

# If user is inspecting a specific ticket
if query_ticket_id:
    selected_ticket = ticket_store.get_ticket(query_ticket_id)
    if selected_ticket:
        render_ticket_detail(selected_ticket)
    else:
        st.error(f"❌ Ticket `{query_ticket_id}` not found in the shared database.")
        if st.button("Return to All Tickets"):
            st.query_params.clear()
            st.rerun()
else:
    # Filter Toolbar
    f_col1, f_col2, f_col3 = st.columns([1, 1, 2])
    with f_col1:
        status_filter = st.selectbox(
            "Filter Status",
            ["All", "Open", "In Review", "Waiting for Customer", "Resolved"],
            index=0
        )
    with f_col2:
        urgency_filter = st.selectbox(
            "Filter Urgency",
            ["All", "High", "Medium", "Low"],
            index=0
        )
    with f_col3:
        search_query = st.text_input("🔍 Search Complaint Text or Ticket ID", placeholder="Type keyword...")

    tickets = ticket_store.get_all_tickets(
        status_filter=status_filter,
        urgency_filter=urgency_filter
    )

    if search_query.strip():
        q = search_query.strip().lower()
        tickets = [
            t for t in tickets
            if q in t["message"].lower() or q in t["ticket_id"].lower() or q in t["intent"].lower()
        ]

    st.subheader(f"📋 Escalated Ticket Queue ({len(tickets)} tickets)")

    if not tickets:
        st.info("No tickets match the selected filters. Great job! The queue is clean.")
    else:
        # Table Overview
        df_display = pd.DataFrame([{
            "ID": t["ticket_id"],
            "Created": t["created_at"],
            "Urgency": {"High": "🔴 High", "Medium": "🟠 Medium", "Low": "🟢 Low"}.get(t["urgency"], t["urgency"]),
            "Status": t["status"],
            "Intent": t["intent"],
            "Confidence": f"{t['confidence']:.0%}",
            "Assigned": t.get("assigned_agent") or "Unassigned",
            "Complaint Snippet": (t["message"][:60] + "...") if len(t["message"]) > 60 else t["message"],
        } for t in tickets])

        st.dataframe(df_display, use_container_width=True)

        st.markdown("### 🔎 Inspect Ticket")
        ticket_options = [f"{t['ticket_id']} — [{t['urgency']}] {t['message'][:50]}..." for t in tickets]
        selected_option = st.selectbox("Choose a ticket to review and respond:", ticket_options)

        if st.button("Inspect Selected Ticket", type="primary"):
            chosen_id = selected_option.split(" — ")[0].strip()
            st.query_params["ticket_id"] = chosen_id
            st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption(
    "NEXAI PS 1.1 — Code-Mixed Support Triage Assistant\n"
    "Human Support Agent Portal v2.0"
)

