# Code-Mixed Support Triage Assistant (NEXAI 2026, PS 1.1)

Classifies Tanglish/Hinglish/English customer complaints, predicts intent and urgency,
estimates prediction confidence, provides natural Gemini LLM responses, and automatically
escalates uncertain complaints into a dedicated **Human Support Portal** via a shared SQLite database.

---

## 🌐 Architecture: Two Separate Websites

| Website | File | Default Port | Purpose |
| :--- | :--- | :--- | :--- |
| **Customer Assistant** | [`app.py`](file:///c:/Users/91960/Downloads/nexai-triage/nexai-triage/app.py) | `http://localhost:8501` | For customers to enter complaints, receive AI triage & Gemini responses, and get escalated tickets. |
| **Human Support Portal** | [`human_portal.py`](file:///c:/Users/91960/Downloads/nexai-triage/nexai-triage/human_portal.py) | `http://localhost:8502` | For support agents to review, inspect, respond to, and resolve escalated tickets. |

Both applications share backend logic and the SQLite database ([`ticket_store.py`](file:///c:/Users/91960/Downloads/nexai-triage/nexai-triage/ticket_store.py) -> `support_tickets.db`).

---

## 🚀 Quickstart: Running Both Websites

Open two terminals in `C:\Users\91960\Downloads\nexai-triage\nexai-triage`:

### Terminal 1: Customer Application
```powershell
python -m streamlit run app.py --server.port 8501
```

### Terminal 2: Human Support Portal
```powershell
python -m streamlit run human_portal.py --server.port 8502
```

---

## 🔄 Automatic Escalation Workflow

1. **Submission**: Customer enters a message in English, Tanglish, or Hinglish on the Customer Website (`:8501`).
2. **Triage & Safety Evaluation**:
   - The ML model (`triage_engine.py`) predicts intent and confidence probability.
   - Urgency and safety rules (e.g., high-urgency payment issue, low confidence, unfamiliar code-mixed wording) determine if human escalation is required.
3. **Automatic Ticket Creation**:
   - When escalation is triggered, a ticket (`TICK-XXXXXX`) is stored in `support_tickets.db` (with deduplication on UI reruns).
4. **Customer Actions**:
   - Customer sees the warning banner and their assigned Ticket ID.
   - Customer clicks **"Get Human Support (Open Portal)"**, which opens `http://localhost:8502/?ticket_id=TICK-XXXXXX`.
   - Customer can click **"Check Ticket Status"** to retrieve agent updates. Internal agent notes are strictly hidden from customers.
5. **Agent Workflow (Human Support Portal)**:
   - Direct URL parameter immediately opens the exact ticket in the agent interface.
   - Agents review the original complaint, model diagnosis, confidence, and Gemini draft.
   - Agents draft an official response, add internal private notes, and update status (`Open` → `In Review` → `Resolved`).
   - Updates persist to SQLite and are immediately visible to the customer when checking status.

---

## 🧪 Testing

Run the full automated test suite (including code-mixed benchmarks and SQLite lifecycle tests):

```powershell
python test_cases.py
```
