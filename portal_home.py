"""NEXAI - Central Portal Selection & Landing Page.

VTOP-inspired institutional portal landing page providing unified access to:
- Customer Portal (Port 8501)
- Human Support Portal (Port 8502)
- Admin Portal (Port 8503)

Run:
    python -m streamlit run portal_home.py --server.port 8500
"""
import os
import streamlit as st

CUSTOMER_PORTAL_URL = os.getenv("CUSTOMER_PORTAL_URL", "http://localhost:8501")
HUMAN_PORTAL_URL = os.getenv("HUMAN_PORTAL_URL", "http://localhost:8502")
ADMIN_PORTAL_URL = os.getenv("ADMIN_PORTAL_URL", "http://localhost:8503")

st.set_page_config(
    page_title="NEXAI — Portal Selection",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom VTOP-Inspired Styling
st.markdown("""
<style>
/* Main Container & Font */
.block-container {
    padding-top: 1rem;
    padding-bottom: 2rem;
    max-width: 1200px;
}

/* Wide Blue Gradient Institutional Header */
.vtop-header {
    background: linear-gradient(135deg, #0f2b5c 0%, #1a4480 50%, #205493 100%);
    border-radius: 12px;
    padding: 24px 32px;
    color: #ffffff;
    box-shadow: 0 4px 14px rgba(15, 43, 92, 0.2);
    margin-bottom: 28px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.brand-wrapper {
    display: flex;
    align-items: center;
    gap: 18px;
}

.brand-logo-badge {
    background: rgba(255, 255, 255, 0.15);
    border: 2px solid rgba(255, 255, 255, 0.35);
    border-radius: 12px;
    width: 58px;
    height: 58px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 30px;
    backdrop-filter: blur(4px);
}

.brand-title {
    font-size: 2.2rem;
    font-weight: 800;
    letter-spacing: 1.5px;
    color: #ffffff;
    margin: 0;
    line-height: 1.1;
}

.brand-subtitle {
    font-size: 0.95rem;
    color: #cbd5e1;
    font-weight: 400;
    margin-top: 4px;
    letter-spacing: 0.5px;
}

.header-status-badge {
    background: rgba(16, 185, 129, 0.2);
    border: 1px solid rgba(52, 211, 153, 0.4);
    color: #a7f3d0;
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 6px;
}

/* Welcome Hero Section */
.welcome-hero {
    text-align: center;
    padding: 10px 20px 26px 20px;
}

.welcome-title {
    font-size: 2.1rem;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 8px;
}

.welcome-subtitle {
    font-size: 1.12rem;
    font-weight: 500;
    color: #2563eb;
    margin-bottom: 6px;
}

.welcome-desc {
    font-size: 0.98rem;
    color: #64748b;
    max-width: 720px;
    margin: 0 auto;
    line-height: 1.5;
}

/* Portal Card Tiles */
.portal-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 24px 20px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
    text-align: center;
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 290px;
    position: relative;
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.portal-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 20px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -2px rgba(0, 0, 0, 0.04);
}

.card-customer {
    border-top: 5px solid #2563eb;
}
.card-customer:hover {
    border-color: #2563eb;
}

.card-human {
    border-top: 5px solid #059669;
}
.card-human:hover {
    border-color: #059669;
}

.card-admin {
    border-top: 5px solid #7c3aed;
}
.card-admin:hover {
    border-color: #7c3aed;
}

.card-icon-container {
    width: 64px;
    height: 64px;
    border-radius: 16px;
    margin: 0 auto 16px auto;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 32px;
}

.icon-customer {
    background: #eff6ff;
    color: #2563eb;
}
.icon-human {
    background: #ecfdf5;
    color: #059669;
}
.icon-admin {
    background: #f5f3ff;
    color: #7c3aed;
}

.card-heading {
    font-size: 1.35rem;
    font-weight: 700;
    color: #1e293b;
    margin-bottom: 8px;
}

.card-description {
    font-size: 0.93rem;
    color: #64748b;
    line-height: 1.45;
    margin-bottom: 20px;
    flex-grow: 1;
}

.card-port-pill {
    display: inline-block;
    padding: 3px 10px;
    background: #f1f5f9;
    border-radius: 12px;
    font-size: 0.78rem;
    font-weight: 600;
    color: #475569;
    margin-bottom: 14px;
}

/* Institutional Footer */
.vtop-footer {
    text-align: center;
    margin-top: 48px;
    padding-top: 24px;
    border-top: 1px solid #e2e8f0;
    color: #94a3b8;
    font-size: 0.88rem;
}
</style>
""", unsafe_allow_html=True)

# ----------------- VTOP-Style Header -----------------
st.markdown(f"""
<div class="vtop-header">
    <div class="brand-wrapper">
        <div class="brand-logo-badge">🏛️</div>
        <div>
            <div class="brand-title">NEXAI</div>
            <div class="brand-subtitle">Intelligent Customer Support Platform</div>
        </div>
    </div>
    <div class="header-status-badge">
        <span>●</span> All Systems Operational
    </div>
</div>
""", unsafe_allow_html=True)

# ----------------- Welcome Section -----------------
st.markdown("""
<div class="welcome-hero">
    <div class="welcome-title">Welcome to NEXAI</div>
    <div class="welcome-subtitle">One intelligent platform for customer support, AI-powered triage, and human assistance.</div>
    <div class="welcome-desc">
        Submit customer complaints in English, Tanglish, or Hinglish, receive AI-assisted responses,
        and seamlessly escalate complex cases to dedicated support teams.
    </div>
</div>
""", unsafe_allow_html=True)

# ----------------- Horizontal 3-Card Portal Selector -----------------
col1, col2, col3 = st.columns(3)

# Card 1: Customer Portal
with col1:
    st.markdown(f"""
    <div class="portal-card card-customer">
        <div class="card-icon-container icon-customer">💬</div>
        <div class="card-heading">Customer Portal</div>
        <div class="card-port-pill">PORT :8501</div>
        <div class="card-description">
            Submit complaints in Tanglish, Hinglish, or English. Receive instant AI-assisted triage,
            and track your ticket resolution in real time.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.link_button("Enter Customer Portal", url=CUSTOMER_PORTAL_URL, type="primary", use_container_width=True)

# Card 2: Human Support Portal
with col2:
    st.markdown(f"""
    <div class="portal-card card-human">
        <div class="card-icon-container icon-human">🎧</div>
        <div class="card-heading">Human Support Portal</div>
        <div class="card-port-pill">PORT :8502</div>
        <div class="card-description">
            Dedicated interface for support representatives. Review escalated tickets, inspect model diagnoses,
            record official responses, and manage ticket status.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.link_button("Enter Support Portal", url=HUMAN_PORTAL_URL, type="primary", use_container_width=True)

# Card 3: Admin Portal
with col3:
    st.markdown(f"""
    <div class="portal-card card-admin">
        <div class="card-icon-container icon-admin">🛡️</div>
        <div class="card-heading">Admin Portal</div>
        <div class="card-port-pill">PORT :8503</div>
        <div class="card-description">
            Monitor institutional metrics, manage agent allocations, tune global triage confidence thresholds,
            and export sanitized compliance reports.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.link_button("Enter Admin Portal", url=ADMIN_PORTAL_URL, type="primary", use_container_width=True)

# ----------------- Portal Information & Architecture Note -----------------
st.markdown("---")
with st.expander("ℹ️ About the NEXAI Multi-Portal Architecture & Security Guidelines"):
    st.markdown("""
    - **Customer Portal (`:8501`)**: Interacts directly with customers, applying TF-IDF code-mixed classification, urgency detection, and Gemini LLM drafting.
    - **Human Support Portal (`:8502`)**: Isolates human agent tools and private notes from customer visibility. Automatically synchronized through the shared SQLite ticket store.
    - **Admin Portal (`:8503`)**: Restricts administrative controls (agent creation, system threshold configuration, data export) behind role-based authentication.
    - **Local MVP Notice**: This multi-port local architecture is tailored for hackathon demonstration. In production, each portal runs behind an enterprise reverse proxy / API gateway with centralized SSO (OAuth2/SAML) and SSL encryption.
    """)

# ----------------- Institutional Footer -----------------
st.markdown("""
<div class="vtop-footer">
    <strong>NEXAI — Code-Mixed Support Triage Assistant</strong> | PS 1.1, NEXAI 2026<br/>
    Powered by TF-IDF + Logistic Regression Classifier & Google Gemini LLM Integration
</div>
""", unsafe_allow_html=True)

