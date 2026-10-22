"""NEXAI - Administrator & Analytics Portal.

Dedicated management console for system administrators to monitor real-time
triage performance, oversee agent workloads, adjust global ML thresholds,
and export compliance reports.

Run:
    python -m streamlit run admin_portal.py --server.port 8503
"""
import hashlib
import json
import os
import importlib
import pandas as pd
import streamlit as st

import ticket_store
importlib.reload(ticket_store)

LANDING_PAGE_URL = os.getenv("LANDING_PAGE_URL", "http://localhost:8500")
ADMIN_USER = os.getenv("ADMIN_USERNAME", "admin")
# Default password: "nexai2026" hashed with SHA-256
DEFAULT_HASH = hashlib.sha256("nexai2026".encode("utf-8")).hexdigest()
ADMIN_HASH = os.getenv("ADMIN_PASSWORD_HASH", DEFAULT_HASH)

st.set_page_config(
    page_title="NEXAI — Admin Portal",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
/* Modern Admin Portal Styling */
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
    color: #64748b !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
div[data-testid="stMetricValue"] {
    font-size: 1.30rem !important;
    font-weight: 700 !important;
    color: #0f172a !important;
}

.admin-header-bar {
    background: linear-gradient(135deg, #4c1d95 0%, #6d28d9 100%);
    border-radius: 10px;
    padding: 16px 24px;
    color: #ffffff;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 24px;
}

.login-card {
    max-width: 440px;
    margin: 40px auto;
    padding: 32px 28px;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.08);
}
</style>
""", unsafe_allow_html=True)

# ----------------- Authentication Barrier -----------------
if "admin_logged_in" not in st.session_state:
    st.session_state["admin_logged_in"] = False

if not st.session_state["admin_logged_in"]:
    st.markdown("""
    <div style="text-align: center; margin-top: 20px;">
        <h2>🛡️ NEXAI Administration Portal</h2>
        <p style="color: #64748b;">Authorized administrative access only</p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        with st.form("admin_login_form"):
            st.subheader("Admin Sign In")
            username = st.text_input("Username", value="", placeholder="Enter admin username")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            submit = st.form_submit_button("Sign In to Admin Console", type="primary", use_container_width=True)

            if submit:
                input_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
                if username.strip() == ADMIN_USER and input_hash == ADMIN_HASH:
                    st.session_state["admin_logged_in"] = True
                    st.session_state["admin_user"] = username.strip()
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

        st.caption("Demo Credentials: Username `admin` | Password `nexai2026`")
        st.markdown(f"[⬅️ Back to NEXAI Landing Page]({LANDING_PAGE_URL})")
    st.stop()

# ----------------- Authenticated Admin Header -----------------
h_col1, h_col2 = st.columns([4, 1])
with h_col1:
    st.title("🛡️ NEXAI Administration & System Governance")
    st.caption("Institutional management console for model oversight, agent workload, and compliance.")
with h_col2:
    st.markdown(f"[🏠 **Home**]({LANDING_PAGE_URL})", help="Return to Portal Landing Page")
    if st.button("🚪 Sign Out", key="admin_signout"):
        st.session_state["admin_logged_in"] = False
        st.rerun()

st.sidebar.header("Admin Controls")
st.sidebar.write(f"Logged in as: **{st.session_state.get('admin_user', 'admin')}**")
st.sidebar.markdown(f"[🏠 Back to Portal Selection]({LANDING_PAGE_URL})")
st.sidebar.info(
    "🔒 **Governance Note:** Actions in this console directly impact live routing, "
    "agent assignment, and global ML safety thresholds."
)

# ----------------- Admin Tabs -----------------
tab_overview, tab_tickets, tab_feedback, tab_agents, tab_ai, tab_config, tab_reports = st.tabs([
    "📊 System Overview",
    "📋 Ticket Management",
    "⭐ Customer Feedback",
    "👥 Agent Workloads",
    "🤖 AI & Triage Insights",
    "⚙️ Triage Configuration",
    "📥 Reports & Export",
])

analytics = ticket_store.get_admin_analytics()

# ================= TAB 1: System Overview =================
with tab_overview:
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Total Tickets", analytics["total_tickets"])
    m2.metric("🔴 Open", analytics["open_tickets"])
    m3.metric("🟠 In Review", analytics["in_review"])
    m4.metric("🟡 Waiting", analytics["waiting"])
    m5.metric("🟢 Resolved", analytics["resolved"])
    m6.metric("🚨 High Urgency", analytics["high_urgency"])

    st.markdown("---")

    c_left, c_right = st.columns([1, 1])

    with c_left:
        st.subheader("Ticket Distribution by Status")
        if analytics["status_distribution"]:
            st.bar_chart(pd.Series(analytics["status_distribution"]))
        else:
            st.info("No tickets recorded yet.")

    with c_right:
        st.subheader("Urgency Breakdown")
        if analytics["urgency_distribution"]:
            st.bar_chart(pd.Series(analytics["urgency_distribution"]))
        else:
            st.info("No urgency data recorded yet.")

    st.markdown("---")
    k1, k2 = st.columns(2)
    with k1:
        st.metric(
            "Average Resolution Time",
            f"{analytics['avg_resolution_min']} mins" if analytics["avg_resolution_min"] > 0 else "N/A (Pending resolutions)",
            help="Calculated from ticket creation to resolved timestamp"
        )
    with k2:
        st.metric(
            "Average Classifier Confidence",
            f"{analytics['avg_confidence']:.1%}" if analytics["total_tickets"] > 0 else "N/A",
            help="Average confidence probability of incoming escalated tickets"
        )

# ================= TAB 2: Ticket Management =================
with tab_tickets:
    st.subheader("Master Escalated Ticket Queue")
    all_tickets = ticket_store.get_all_tickets()

    if not all_tickets:
        st.info("No escalated tickets found in the database.")
    else:
        # Search & Filter controls
        f1, f2, f3 = st.columns([1, 1, 2])
        with f1:
            s_filter = st.selectbox("Status", ["All"] + ticket_store.VALID_STATUSES, key="tm_status")
        with f2:
            u_filter = st.selectbox("Urgency", ["All", "High", "Medium", "Low"], key="tm_urg")
        with f3:
            search_txt = st.text_input("Search ID / Keyword", placeholder="Search complaint...", key="tm_search")

        filtered = ticket_store.get_all_tickets(
            status_filter=s_filter if s_filter != "All" else None,
            urgency_filter=u_filter if u_filter != "All" else None,
        )

        if search_txt.strip():
            q = search_txt.strip().lower()
            filtered = [
                t for t in filtered
                if q in t["ticket_id"].lower() or q in t["message"].lower() or q in t["intent"].lower()
            ]

        # Display Queue
        df_show = pd.DataFrame([{
            "Ticket ID": t["ticket_id"],
            "Created": t["created_at"],
            "Status": t["status"],
            "Urgency": t["urgency"],
            "Intent": t["intent"],
            "Confidence": f"{t['confidence']:.0%}",
            "Assigned Agent": t.get("assigned_agent") or "Unassigned",
            "Message": (t["message"][:65] + "...") if len(t["message"]) > 65 else t["message"],
        } for t in filtered])

        st.dataframe(df_show, use_container_width=True)

        st.markdown("### 🔍 Inspect & Assign Ticket")
        sel_t = st.selectbox("Select ticket ID to inspect:", [t["ticket_id"] for t in filtered])
        t_data = ticket_store.get_ticket(sel_t)
        if t_data:
            with st.container():
                st.markdown(f"**Complaint:** `{t_data['message']}`")
                st.markdown(f"**Escalation Reason:** {t_data['escalation_reason']}")
                if t_data.get("agent_response"):
                    st.success(f"**Agent Response:** {t_data['agent_response']}")
                if t_data.get("internal_notes"):
                    st.warning(f"**Internal Agent Notes:** {t_data['internal_notes']}")

                # Agent assignment
                active_agents = ticket_store.get_agents(only_active=True)
                agent_names = ["Unassigned"] + [a["name"] for a in active_agents]
                cur_assigned = t_data.get("assigned_agent", "Unassigned")
                cur_idx = agent_names.index(cur_assigned) if cur_assigned in agent_names else 0

                assign_col1, assign_col2 = st.columns([2, 1])
                with assign_col1:
                    new_agent = st.selectbox("Assign Support Specialist", agent_names, index=cur_idx)
                with assign_col2:
                    st.write("")
                    st.write("")
                    if st.button("Update Assignment", key=f"assign_{sel_t}"):
                        ticket_store.assign_ticket(sel_t, new_agent)
                        st.success(f"Ticket {sel_t} assigned to {new_agent}!")
                        st.rerun()

# ================= CUSTOMER FEEDBACK =================
with tab_feedback:
    st.subheader("Customer Feedback")
    feedbacks = ticket_store.get_all_feedback()
    if not feedbacks:
        st.info("No customer feedback submitted yet.")
    else:
        st.dataframe(pd.DataFrame([{
            "Feedback ID": f["feedback_id"],
            "Rating": f"{f['rating']}/5",
            "Category": f["category"],
            "Comments": f["message"] or "No comments",
            "Ticket ID": f["ticket_id"] or "—",
            "Submitted": f["created_at"],
            "Status": f["status"],
        } for f in feedbacks]), use_container_width=True)

        st.markdown("### Open and manage feedback")
        selected_feedback_id = st.selectbox(
            "Select feedback ID", [f["feedback_id"] for f in feedbacks], key="admin_feedback_id"
        )
        feedback = ticket_store.get_feedback(selected_feedback_id)
        if feedback:
            st.write(f"**Rating:** {feedback['rating']}/5 · **Category:** {feedback['category']}")
            st.write(f"**Submitted:** {feedback['created_at']} · **Ticket ID:** {feedback['ticket_id'] or '—'}")
            st.write(f"**Comments:** {feedback['message'] or 'No comments'}")
            with st.form(f"admin_feedback_form_{selected_feedback_id}"):
                feedback_status = st.selectbox(
                    "Status", ticket_store.FEEDBACK_STATUSES,
                    index=ticket_store.FEEDBACK_STATUSES.index(feedback["status"])
                    if feedback["status"] in ticket_store.FEEDBACK_STATUSES else 0,
                )
                admin_response = st.text_area(
                    "Optional admin response", value=feedback.get("agent_response") or "", height=90
                )
                if st.form_submit_button("Save feedback updates", type="primary"):
                    ticket_store.update_feedback(
                        feedback_id=selected_feedback_id,
                        status=feedback_status,
                        agent_response=admin_response,
                    )
                    st.success("Feedback updated.")
                    st.rerun()
# ================= TAB 3: Agent Workloads =================
with tab_agents:
    st.subheader("Support Agent Directory & Workload Allocation")
    agents = ticket_store.get_agents()

    # Calculate workload per agent from tickets table
    with ticket_store.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT assigned_agent, COUNT(*) FROM tickets WHERE status != 'Resolved' GROUP BY assigned_agent")
        workload_map = dict(cursor.fetchall())

    agent_rows = []
    for a in agents:
        agent_rows.append({
            "Agent ID": a["agent_id"],
            "Name": a["name"],
            "Email": a["email"],
            "Role": a["role"],
            "Active": "🟢 Active" if a["active"] else "🔴 Inactive",
            "Active Workload (Open/Review)": workload_map.get(a["name"], 0),
            "Registered Date": a["created_at"],
        })
    st.dataframe(pd.DataFrame(agent_rows), use_container_width=True)

    st.markdown("---")
    st.subheader("Register New Support Agent")
    with st.form("new_agent_form"):
        ag_c1, ag_c2, ag_c3 = st.columns(3)
        with ag_c1:
            ag_name = st.text_input("Full Name", placeholder="e.g. Ananya Sen")
        with ag_c2:
            ag_email = st.text_input("Corporate Email", placeholder="ananya.s@support.nexai.local")
        with ag_c3:
            ag_role = st.selectbox(
                "Role / Specialization",
                ["Tier 1 Code-Mixed Triage", "Billing & Payment Specialist", "Escalations Lead", "General Support"]
            )
        ag_submit = st.form_submit_button("Register Agent", type="primary")

        if ag_submit:
            if ag_name.strip() and ag_email.strip():
                new_id = ticket_store.add_agent(ag_name, ag_email, ag_role)
                st.success(f"Successfully registered agent {ag_name} ({new_id})!")
                st.rerun()
            else:
                st.warning("Please provide both name and email.")

# ================= TAB 4: AI & Triage Monitoring =================
with tab_ai:
    st.subheader("Live Ticket Intake vs. Offline Model Benchmarks")

    st.markdown("#### 1. Live Incoming Ticket Intent Distribution")
    if analytics["intent_distribution"]:
        st.bar_chart(pd.Series(analytics["intent_distribution"]))
    else:
        st.info("No live tickets recorded yet to display intent distribution.")

    st.markdown("---")
    st.subheader("2. Offline Machine Learning Benchmarks (Trained Model Artifacts)")
    st.caption("Distinguished from live ticket data: These are rigorous held-out test evaluations from `results/`.")

    eval_report_path = os.path.join("results", "evaluation_metrics.txt")
    if os.path.exists(eval_report_path):
        with open(eval_report_path, "r", encoding="utf-8") as f:
            eval_text = f.read()
        st.text_area("Offline Model Evaluation Report", eval_text, height=260, disabled=True)
    else:
        st.info("Run `python train_model.py` to generate the offline evaluation benchmark.")

    test_res_csv = os.path.join("results", "test_results.csv")
    if os.path.exists(test_res_csv):
        df_bench = pd.read_csv(test_res_csv)
        b_c1, b_c2, b_c3 = st.columns(3)
        b_c1.metric("Code-Mixed Test Messages", len(df_bench))
        b_c2.metric("Intent Accuracy", f"{df_bench.intent_ok.mean():.1%}")
        b_c3.metric("Urgency Accuracy", f"{df_bench.urgency_ok.mean():.1%}")
        with st.expander("View 45-Message Team Test Evaluation Set"):
            st.dataframe(df_bench[["message", "expected_intent", "predicted_intent", "confidence", "status"]])

# ================= TAB 5: Triage Configuration =================
with tab_config:
    st.subheader("Global Triage Engine Safety Configuration")
    st.caption(
        "Persisted in the shared SQLite database. The Customer Portal and Human Support Portal "
        "synchronize with these parameters in real time."
    )

    current_threshold = float(ticket_store.get_setting("confidence_threshold", 0.45))

    with st.form("triage_config_form"):
        new_thr = st.slider(
            "Global Confidence Escalation Threshold",
            min_value=0.10,
            max_value=0.90,
            value=current_threshold,
            step=0.05,
            help="Predictions below this score will trigger automatic human review."
        )

        st.info(
            "🔒 **Security Guardrail:** Gemini API keys are loaded securely via local `.env` "
            "and are never exposed or edited via the Admin UI."
        )

        save_conf = st.form_submit_button("Save Global Settings", type="primary")
        if save_conf:
            ticket_store.set_setting("confidence_threshold", new_thr)
            st.success(f"Global confidence threshold updated to {new_thr:.0%}!")
            st.rerun()

# ================= TAB 6: Reports & Export =================
with tab_reports:
    st.subheader("Compliance & Operational Reports Export")
    st.caption("Generate sanitized CSV audit reports for analytics and auditing.")

    sanitized_df = ticket_store.export_sanitized_tickets_df()

    st.markdown(f"**Total Records:** `{len(sanitized_df)}` rows available.")
    st.warning("🛡️ **Privacy Shield Active:** Private internal agent notes are automatically excluded from exports.")

    if not sanitized_df.empty:
        st.dataframe(sanitized_df.head(15), use_container_width=True)

        csv_data = sanitized_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Sanitized Tickets CSV",
            data=csv_data,
            file_name="nexai_support_tickets_report.csv",
            mime="text/csv",
            type="primary"
        )
    else:
        st.info("No tickets available for export.")

st.markdown("---")
st.caption("NEXAI Platform v2.0 — Institutional Administration Console")

