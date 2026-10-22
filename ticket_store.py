"""Shared SQLite Ticket Store for NEXAI Support Triage.

Provides persistent, thread-safe, transactional SQLite storage for tickets,
agents, system configuration, and analytics across:
- Customer Portal (port 8501)
- Human Support Portal (port 8502)
- Admin Portal (port 8503)
- Portal Home / Landing (port 8500)
"""
import os
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
import pandas as pd

DB_NAME = "support_tickets.db"
DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_NAME)

VALID_STATUSES = ["Open", "In Review", "Waiting for Customer", "Resolved"]


def get_db_path(db_path: Optional[str] = None) -> str:
    """Return the absolute path to the SQLite database file."""
    if db_path:
        return os.path.abspath(db_path)
    env_path = os.getenv("TICKET_DB_PATH")
    if env_path:
        return os.path.abspath(env_path)
    return DEFAULT_DB_PATH


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Create and return a configured sqlite3 connection."""
    path = get_db_path(db_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, timeout=15.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Initialize the SQLite schema if it does not exist and apply migrations."""
    path = get_db_path(db_path)
    with get_connection(path) as conn:
        cursor = conn.cursor()

        # 1. Tickets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id TEXT PRIMARY KEY,
                message TEXT NOT NULL,
                intent TEXT,
                category TEXT,
                urgency TEXT,
                confidence REAL,
                threshold REAL,
                escalation_reason TEXT,
                llm_acknowledgement TEXT,
                agent_response TEXT DEFAULT '',
                internal_notes TEXT DEFAULT '',
                status TEXT DEFAULT 'Open',
                assigned_agent TEXT DEFAULT 'Unassigned',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)

        # Migration: ensure assigned_agent exists on older databases
        cursor.execute("PRAGMA table_info(tickets)")
        cols = [col[1] for col in cursor.fetchall()]
        if "assigned_agent" not in cols:
            cursor.execute("ALTER TABLE tickets ADD COLUMN assigned_agent TEXT DEFAULT 'Unassigned';")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tickets_urgency ON tickets(urgency);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tickets_created_at ON tickets(created_at);")

        # 2. Agents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT,
                role TEXT,
                active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL
            );
        """)

        # Seed initial agents if table is empty
        cursor.execute("SELECT COUNT(*) FROM agents")
        if cursor.fetchone()[0] == 0:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            initial_agents = [
                ("AGT-01", "Priya Sharma", "priya.s@support.nexai.local", "Senior Triage Specialist", 1, now),
                ("AGT-02", "Karthik Raja", "karthik.r@support.nexai.local", "Billing & Refunds Specialist", 1, now),
                ("AGT-03", "Rahul Verma", "rahul.v@support.nexai.local", "Technical Escalations Agent", 1, now),
            ]
            cursor.executemany(
                "INSERT INTO agents (agent_id, name, email, role, active, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                initial_agents,
            )

        # 3. System settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)

        # 4. Customer Feedback table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customer_feedback (
                feedback_id TEXT PRIMARY KEY,
                ticket_id TEXT DEFAULT '',
                rating INTEGER NOT NULL,
                category TEXT NOT NULL,
                message TEXT DEFAULT '',
                status TEXT DEFAULT 'New',
                agent_response TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_status ON customer_feedback(status);")

        # Seed initial settings if missing
        cursor.execute("SELECT COUNT(*) FROM system_settings WHERE key = 'confidence_threshold'")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO system_settings (key, value, updated_at) VALUES (?, ?, ?)",
                ("confidence_threshold", "0.45", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )

        conn.commit()


# ---------------- System Settings Operations ----------------

def get_setting(key: str, default: Any = None, db_path: Optional[str] = None) -> Any:
    """Retrieve a system setting from SQLite."""
    init_db(db_path)
    path = get_db_path(db_path)
    with get_connection(path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row:
            val = row[0]
            # Try float/int conversion if appropriate
            try:
                if "." in val:
                    return float(val)
                return int(val)
            except ValueError:
                return val
    return default


def set_setting(key: str, value: Any, db_path: Optional[str] = None) -> None:
    """Save or update a system setting in SQLite."""
    init_db(db_path)
    path = get_db_path(db_path)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection(path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO system_settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
            """,
            (key, str(value), now),
        )
        conn.commit()


# ---------------- Ticket Operations ----------------

def create_ticket(
    message: str,
    intent: str = "Unknown",
    category: str = "Unknown",
    urgency: str = "Unknown",
    confidence: float = 0.0,
    threshold: float = 0.45,
    escalation_reason: Union[str, List[str]] = "",
    llm_acknowledgement: str = "",
    assigned_agent: str = "Unassigned",
    db_path: Optional[str] = None,
) -> str:
    """Create a new support ticket in the shared database."""
    init_db(db_path)

    if isinstance(escalation_reason, (list, tuple)):
        reasons_text = "; ".join(str(r) for r in escalation_reason)
    else:
        reasons_text = str(escalation_reason).strip()

    ticket_id = f"TICK-{uuid.uuid4().hex[:6].upper()}"
    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    path = get_db_path(db_path)
    with get_connection(path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO tickets (
                ticket_id, message, intent, category, urgency, confidence,
                threshold, escalation_reason, llm_acknowledgement,
                agent_response, internal_notes, status, assigned_agent,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticket_id,
                message.strip(),
                intent,
                category,
                urgency,
                round(float(confidence), 4),
                round(float(threshold), 4),
                reasons_text,
                llm_acknowledgement.strip(),
                "",
                "",
                "Open",
                assigned_agent,
                now_iso,
                now_iso,
            ),
        )
        conn.commit()

    return ticket_id


def get_ticket(ticket_id: str, db_path: Optional[str] = None) -> Optional[Dict]:
    """Retrieve a single ticket by its ticket_id."""
    init_db(db_path)
    path = get_db_path(db_path)
    with get_connection(path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id.strip(),))
        row = cursor.fetchone()
        if row:
            return dict(row)
    return None


def update_ticket(
    ticket_id: str,
    status: Optional[str] = None,
    agent_response: Optional[str] = None,
    internal_notes: Optional[str] = None,
    assigned_agent: Optional[str] = None,
    db_path: Optional[str] = None,
) -> bool:
    """Update status, agent response, internal notes, or assigned agent."""
    init_db(db_path)

    if status and status not in VALID_STATUSES:
        raise ValueError(f"Invalid status '{status}'. Must be one of: {VALID_STATUSES}")

    fields = []
    values = []

    if status is not None:
        fields.append("status = ?")
        values.append(status)

    if agent_response is not None:
        fields.append("agent_response = ?")
        values.append(agent_response.strip())

    if internal_notes is not None:
        fields.append("internal_notes = ?")
        values.append(internal_notes.strip())

    if assigned_agent is not None:
        fields.append("assigned_agent = ?")
        values.append(assigned_agent.strip())

    if not fields:
        return False

    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fields.append("updated_at = ?")
    values.append(now_iso)

    values.append(ticket_id.strip())
    set_clause = ", ".join(fields)

    path = get_db_path(db_path)
    with get_connection(path) as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE tickets SET {set_clause} WHERE ticket_id = ?", values)
        conn.commit()
        return cursor.rowcount > 0


def assign_ticket(ticket_id: str, agent_name: str, db_path: Optional[str] = None) -> bool:
    """Assign a ticket to a specific agent."""
    return update_ticket(ticket_id, assigned_agent=agent_name, db_path=db_path)


def get_all_tickets(
    status_filter: Optional[str] = None,
    urgency_filter: Optional[str] = None,
    intent_filter: Optional[str] = None,
    db_path: Optional[str] = None,
) -> List[Dict]:
    """Retrieve all tickets, optionally filtered by status, urgency, and/or intent."""
    init_db(db_path)
    query = "SELECT * FROM tickets WHERE 1=1"
    params = []

    if status_filter and status_filter != "All":
        query += " AND status = ?"
        params.append(status_filter)

    if urgency_filter and urgency_filter != "All":
        query += " AND urgency = ?"
        params.append(urgency_filter)

    if intent_filter and intent_filter != "All":
        query += " AND intent = ?"
        params.append(intent_filter)

    query += """
        ORDER BY
            CASE urgency WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 WHEN 'Low' THEN 3 ELSE 4 END,
            CASE status WHEN 'Open' THEN 1 WHEN 'In Review' THEN 2 WHEN 'Waiting for Customer' THEN 3 ELSE 4 END,
            created_at DESC
    """

    path = get_db_path(db_path)
    with get_connection(path) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def get_stats(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Return dashboard summary metrics."""
    init_db(db_path)
    path = get_db_path(db_path)
    with get_connection(path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tickets")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tickets WHERE status = 'Open'")
        open_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tickets WHERE status = 'In Review'")
        in_review = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tickets WHERE status = 'Waiting for Customer'")
        waiting = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tickets WHERE status = 'Resolved'")
        resolved = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tickets WHERE urgency = 'High'")
        high_urgency = cursor.fetchone()[0]

    return {
        "total": total,
        "open": open_count,
        "in_review": in_review,
        "waiting": waiting,
        "resolved": resolved,
        "high_urgency": high_urgency,
    }


# ---------------- Agent Management ----------------

def get_agents(only_active: bool = False, db_path: Optional[str] = None) -> List[Dict]:
    """Return list of support agents."""
    init_db(db_path)
    path = get_db_path(db_path)
    with get_connection(path) as conn:
        cursor = conn.cursor()
        if only_active:
            cursor.execute("SELECT * FROM agents WHERE active = 1 ORDER BY name ASC")
        else:
            cursor.execute("SELECT * FROM agents ORDER BY active DESC, name ASC")
        return [dict(r) for r in cursor.fetchall()]


def add_agent(name: str, email: str, role: str, db_path: Optional[str] = None) -> str:
    """Add a new support agent."""
    init_db(db_path)
    path = get_db_path(db_path)
    agent_id = f"AGT-{uuid.uuid4().hex[:4].upper()}"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection(path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO agents (agent_id, name, email, role, active, created_at) VALUES (?, ?, ?, ?, 1, ?)",
            (agent_id, name.strip(), email.strip(), role.strip(), now),
        )
        conn.commit()
    return agent_id


def toggle_agent(agent_id: str, active: bool, db_path: Optional[str] = None) -> bool:
    """Activate or deactivate a support agent."""
    init_db(db_path)
    path = get_db_path(db_path)
    with get_connection(path) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE agents SET active = ? WHERE agent_id = ?", (1 if active else 0, agent_id))
        conn.commit()
        return cursor.rowcount > 0


# ---------------- Admin Analytics & Export ----------------

def get_admin_analytics(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Compute real metrics from the stored tickets table."""
    init_db(db_path)
    path = get_db_path(db_path)
    with get_connection(path) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM tickets")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT status, COUNT(*) FROM tickets GROUP BY status")
        status_counts = dict(cursor.fetchall())

        cursor.execute("SELECT urgency, COUNT(*) FROM tickets GROUP BY urgency")
        urgency_counts = dict(cursor.fetchall())

        cursor.execute("SELECT intent, COUNT(*) FROM tickets GROUP BY intent ORDER BY COUNT(*) DESC")
        intent_counts = dict(cursor.fetchall())

        cursor.execute("SELECT AVG(confidence) FROM tickets")
        avg_confidence = cursor.fetchone()[0] or 0.0

        # Calculate average resolution time for Resolved tickets
        cursor.execute("SELECT created_at, updated_at FROM tickets WHERE status = 'Resolved'")
        resolved_times = cursor.fetchall()

    resolution_durations_sec = []
    for c_at, u_at in resolved_times:
        try:
            t1 = datetime.strptime(c_at, "%Y-%m-%d %H:%M:%S")
            t2 = datetime.strptime(u_at, "%Y-%m-%d %H:%M:%S")
            dur = (t2 - t1).total_seconds()
            if dur >= 0:
                resolution_durations_sec.append(dur)
        except Exception:
            pass

    avg_resolution_min = (
        round(sum(resolution_durations_sec) / (len(resolution_durations_sec) * 60.0), 1)
        if resolution_durations_sec
        else 0.0
    )

    return {
        "total_tickets": total,
        "open_tickets": status_counts.get("Open", 0),
        "in_review": status_counts.get("In Review", 0),
        "waiting": status_counts.get("Waiting for Customer", 0),
        "resolved": status_counts.get("Resolved", 0),
        "high_urgency": urgency_counts.get("High", 0),
        "avg_confidence": avg_confidence,
        "status_distribution": status_counts,
        "urgency_distribution": urgency_counts,
        "intent_distribution": intent_counts,
        "avg_resolution_min": avg_resolution_min,
    }


def export_sanitized_tickets_df(db_path: Optional[str] = None) -> pd.DataFrame:
    """Return a DataFrame of tickets sanitized for administrative reporting.

    EXCLUDES private internal notes to ensure data safety and privacy.
    """
    init_db(db_path)
    path = get_db_path(db_path)
    with get_connection(path) as conn:
        df = pd.read_sql_query(
            """
            SELECT
                ticket_id,
                message,
                intent,
                category,
                urgency,
                confidence,
                threshold,
                escalation_reason,
                status,
                assigned_agent,
                agent_response,
                created_at,
                updated_at
            FROM tickets
            ORDER BY created_at DESC
            """,
            conn,
        )
    return df


# ---------------- Customer Feedback Operations ----------------

FEEDBACK_STATUSES = ["New", "Reviewed", "Responded", "Closed"]


def create_feedback(
    rating: int,
    category: str,
    message: str = "",
    ticket_id: str = "",
    db_path: Optional[str] = None,
) -> str:
    """Save customer feedback in SQLite and return feedback_id."""
    init_db(db_path)
    fb_id = f"FB-{uuid.uuid4().hex[:6].upper()}"
    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    path = get_db_path(db_path)
    with get_connection(path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO customer_feedback (
                feedback_id, ticket_id, rating, category, message,
                status, agent_response, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'New', '', ?, ?)
            """,
            (
                fb_id,
                ticket_id.strip() if ticket_id else "",
                int(rating),
                category.strip(),
                message.strip(),
                now_iso,
                now_iso,
            ),
        )
        conn.commit()
    return fb_id


def get_all_feedback(status_filter: Optional[str] = None, db_path: Optional[str] = None) -> List[Dict]:
    """Retrieve all submitted feedback entries."""
    init_db(db_path)
    query = "SELECT * FROM customer_feedback WHERE 1=1"
    params = []
    if status_filter and status_filter != "All":
        query += " AND status = ?"
        params.append(status_filter)
    query += " ORDER BY created_at DESC"

    path = get_db_path(db_path)
    with get_connection(path) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]


def get_feedback(feedback_id: str, db_path: Optional[str] = None) -> Optional[Dict]:
    """Retrieve a single feedback record."""
    init_db(db_path)
    path = get_db_path(db_path)
    with get_connection(path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM customer_feedback WHERE feedback_id = ?", (feedback_id.strip(),))
        row = cursor.fetchone()
        if row:
            return dict(row)
    return None


def update_feedback(
    feedback_id: str,
    status: Optional[str] = None,
    agent_response: Optional[str] = None,
    db_path: Optional[str] = None,
) -> bool:
    """Update feedback status and/or agent response."""
    init_db(db_path)
    if status and status not in FEEDBACK_STATUSES:
        raise ValueError(f"Invalid status '{status}'. Must be one of: {FEEDBACK_STATUSES}")

    fields = []
    values = []
    if status is not None:
        fields.append("status = ?")
        values.append(status)
    if agent_response is not None:
        fields.append("agent_response = ?")
        values.append(agent_response.strip())

    if not fields:
        return False

    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fields.append("updated_at = ?")
    values.append(now_iso)
    values.append(feedback_id.strip())

    set_clause = ", ".join(fields)
    path = get_db_path(db_path)
    with get_connection(path) as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE customer_feedback SET {set_clause} WHERE feedback_id = ?", values)
        conn.commit()
        return cursor.rowcount > 0

