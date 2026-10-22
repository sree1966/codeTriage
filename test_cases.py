"""Team-written Tanglish/Hinglish test set (expected intent + expected urgency)
and automated unit tests for NEXAI Triage and Gemini LLM integration.

Run:  python test_cases.py
"""
import os
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd

# (message, expected_intent, expected_urgency)
TEST_CASES = [
    # ---------------- Hinglish ----------------
    ("Mera order kahan hai? Tracking number bhejo", "track_order", "Low"),
    ("Delivery mein kitne din lagenge?", "delivery_period", "Low"),
    ("Order cancel karna hai please, galti se ho gaya", "cancel_order", "Medium"),
    ("Mujhe apna paisa wapas chahiye, product kharab nikla", "get_refund", "Medium"),
    ("Refund kab milega? 5 din ho gaye", "track_refund", "Medium"),
    ("Mera password bhool gaya hu, reset kaise karu", "recover_password", "Low"),
    ("Mujhe naya account banana hai", "create_account", "Low"),
    ("Mera account delete kar do permanently", "delete_account", "Low"),
    ("Invoice ki copy email pe bhej do", "get_invoice", "Low"),
    ("Payment ho gaya lekin order confirm nahi hua, paisa kat gaya", "payment_issue", "High"),
    ("Mujhe kisi insaan se baat karni hai, bot se kaam nahi chal raha", "contact_human_agent", "Low"),
    ("Delivery address change karna hai, naya pata ye hai", "change_shipping_address", "Low"),
    ("Aapki service bahut ghatiya hai, main bahut pareshan hoon, shikayat darj karo", "complaint", "Medium"),
    ("Kya main COD se payment kar sakta hu?", "check_payment_methods", "Low"),
    ("Cancellation fee kitni lagegi?", "check_cancellation_fee", "Low"),
    ("Mujhe apni product review likhna hai", "review", "Low"),
    ("URGENT: mere card se do baar paise kat gaye, ye fraud lagta hai!", "payment_issue", "High"),
    ("Newsletter se unsubscribe karna hai", "newsletter_subscription", "Low"),
    ("Order mein size M ki jagah L chahiye, order change karo", "change_order", "Low"),
    ("Return policy kya hai?", "check_refund_policy", "Low"),
    # ---------------- Tanglish ----------------
    ("Enakku en order cancel pannanum, thappa order pannitten", "cancel_order", "Medium"),
    ("Order eppo vandhu sernthuchu? tracking details venum", "track_order", "Low"),
    ("Delivery varuvadharku evlo naal aagum?", "delivery_period", "Low"),
    ("Kasu thirumba venum, product romba mosam", "get_refund", "Medium"),
    ("Refund innum varala, eppo varum?", "track_refund", "Medium"),
    ("Password maranthuten, reset pannunga", "recover_password", "Low"),
    ("Pudhu account create panna mudiyala, error varudhu", "registration_problems", "Medium"),
    ("En account-a delete pannunga", "delete_account", "Low"),
    ("Invoice copy anuppunga please", "get_invoice", "Low"),
    ("Kasu pochu but order confirm aagala, seekiram help pannunga!", "payment_issue", "High"),
    ("Oru manushan kooda pesanum, bot help pannala", "contact_human_agent", "Low"),
    ("Delivery address mathanum, puthu mugavari anuppuren", "change_shipping_address", "Low"),
    ("Ungal service romba mosam, complaint pannanum", "complaint", "Medium"),
    ("Epdi pay panna mudiyum? UPI accept pannuvingala?", "check_payment_methods", "Low"),
    ("Cancel panna charge evlo?", "check_cancellation_fee", "Medium"),
    ("En order-la item mathanum, size L venum", "change_order", "Low"),
    ("Product review eluthanum", "review", "Low"),
    ("Emathitanga! Unauthorized transaction nadandhuruku, udane help pannunga", "payment_issue", "High"),
    ("Newsletter subscribe pannanum", "newsletter_subscription", "Low"),
    ("Refund policy enna?", "check_refund_policy", "Medium"),
    # ---------------- examples named in the problem brief ----------------
    ("Order vandhuchu but box damaged, refund venum.", "get_refund", "Medium"),
    ("Mera payment deduct ho gaya, order confirm nahi hua.", "payment_issue", "High"),
    ("En account login aagala, help pannunga.", "recover_password", "Low"),
    ("Refund innum varala, please check pannunga.", "track_refund", "Medium"),
    ("Wrong product deliver pannitanga.", "complaint", "Medium"),
]

# Bitext has no 'login problem' or 'wrong item delivered' intent. These two cases use the
# closest existing label as a DOCUMENTED FALLBACK (they are not real Bitext labels).
LABEL_NOTES = {
    "En account login aagala, help pannunga.":
        "Fallback: no login-problem intent in Bitext; closest is recover_password",
    "Wrong product deliver pannitanga.":
        "Fallback: no wrong-item intent in Bitext; closest is complaint",
}


def run_tests(threshold=None, verbose=False, save=True):
    """Run code-mixed evaluation on the team-written test set."""
    from triage_engine import CONF_THRESHOLD, load_bundle, triage
    thr = CONF_THRESHOLD if threshold is None else threshold
    classes = set(load_bundle()["model"].classes_)
    rows = []
    for text, exp_intent, exp_urg in TEST_CASES:
        r = triage(text, thr)
        rows.append({
            "message": text,
            "expected_intent": exp_intent,
            "label_in_dataset": exp_intent in classes,
            "predicted_intent": r["intent"],
            "intent_ok": r["intent"] == exp_intent,
            "confidence": round(r["confidence"], 3),
            "expected_urgency": exp_urg,
            "predicted_urgency": r["urgency"],
            "urgency_ok": r["urgency"] == exp_urg,
            "language": r["language"],
            "status": "Needs human review" if r["escalate"] else "Auto-handled",
            "escalated": r["escalate"],
            "label_note": LABEL_NOTES.get(text, ""),
        })
    df = pd.DataFrame(rows)
    missing = df[~df.label_in_dataset]
    if len(missing):
        print("WARNING: expected labels not found in the dataset:", sorted(set(missing.expected_intent)))
    if save:
        os.makedirs("results", exist_ok=True)
        df.to_csv(os.path.join("results", "test_results.csv"), index=False)
    if verbose:
        n = len(df)
        print(f"\n=== Code-mixed team test set: {n} messages ===")
        print(f"Intent accuracy : {df.intent_ok.mean():.1%} ({df.intent_ok.sum()}/{n})")
        print(f"Urgency accuracy: {df.urgency_ok.mean():.1%} ({df.urgency_ok.sum()}/{n})")
        print(f"Escalated to human: {df.escalated.sum()}/{n}")
        wrong = df[~df.intent_ok]
        if len(wrong):
            print("\nMisclassified:")
            print(wrong[["message", "expected_intent", "predicted_intent", "confidence"]].to_string(index=False))
    return df


# ---------------------------------------------------------------------------
# Unit and Edge Case Tests (English, Tanglish, Hinglish, Empty, Low-conf, LLM)
# ---------------------------------------------------------------------------
class TestTriageSystem(unittest.TestCase):
    """Automated unit tests covering triage engine, edge cases, and LLM behavior."""

    @classmethod
    def setUpClass(cls):
        from triage_engine import load_bundle
        load_bundle()

    def test_english_complaint(self):
        from triage_engine import triage
        r = triage("Where is my order? Please provide the tracking status.")
        self.assertIsNotNone(r)
        self.assertEqual(r["intent"], "track_order")
        self.assertEqual(r["language"], "English")

    def test_tanglish_complaint(self):
        from triage_engine import triage
        r = triage("Enakku en order cancel pannanum, thappa order pannitten")
        self.assertIsNotNone(r)
        self.assertEqual(r["intent"], "cancel_order")
        self.assertEqual(r["language"], "Tanglish")

    def test_hinglish_complaint(self):
        from triage_engine import triage
        r = triage("Mera order kahan hai? Tracking number bhejo")
        self.assertIsNotNone(r)
        self.assertEqual(r["intent"], "track_order")
        self.assertEqual(r["language"], "Hinglish")

    def test_empty_and_whitespace_input(self):
        from triage_engine import triage
        from llm_response import generate_support_reply
        self.assertIsNone(triage(""))
        self.assertIsNone(triage("   \n\t  "))
        reply = generate_support_reply("   ")
        self.assertIn("provide a description", reply.lower())

    def test_low_confidence_triggers_escalation(self):
        from triage_engine import triage
        # With threshold = 0.99, any normal message should escalate
        r = triage("I need help with something vague", threshold=0.99)
        self.assertTrue(r["escalate"])
        self.assertTrue(any("confidence" in reason.lower() for reason in r["escalation_reasons"]))

    def test_gemini_missing_api_key(self):
        from llm_response import generate_support_reply
        with patch("llm_response.get_api_key", return_value=None):
            reply = generate_support_reply(
                message="My package has not arrived yet.",
                intent="track_order",
                client=None
            )
            self.assertIn("Gemini API key is not configured", reply)

    def test_gemini_api_failure_handled_gracefully(self):
        from llm_response import generate_support_reply
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = RuntimeError("API Network Connection Timeout")

        with patch("llm_response.get_api_key", return_value="fake_test_key"):
            reply = generate_support_reply(
                message="My package has not arrived yet.",
                intent="track_order",
                category="order",
                urgency="Medium",
                confidence=0.85,
                escalate=False,
                client=mock_client
            )
            # Must return a safe user message and NOT crash or leak the exception trace
            self.assertIn("temporarily experiencing high traffic", reply)
            self.assertNotIn("fake_test_key", reply)
            self.assertNotIn("Traceback", reply)

    def test_gemini_escalation_reply_does_not_claim_completion(self):
        from llm_response import generate_support_reply
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = (
            "We have noted your issue regarding payment deduction. A human agent is reviewing "
            "your case and will follow up shortly. Please provide your transaction reference number."
        )
        mock_client.models.generate_content.return_value = mock_response

        with patch("llm_response.get_api_key", return_value="fake_test_key"):
            reply = generate_support_reply(
                message="Paisa kat gaya order confirm nahi hua",
                intent="payment_issue",
                urgency="High",
                confidence=0.30,
                escalate=True,
                escalation_reason="Low confidence (30%)",
                client=mock_client
            )
            self.assertIn("human agent", reply.lower())

    def test_sqlite_ticket_lifecycle(self):
        import tempfile
        import ticket_store

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            test_db = tf.name

        try:
            # 1. Create ticket
            tid = ticket_store.create_ticket(
                message="Card se double deduction ho gaya",
                intent="payment_issue",
                category="payment",
                urgency="High",
                confidence=0.25,
                threshold=0.45,
                escalation_reason="Low confidence (25%)",
                llm_acknowledgement="Holding reply",
                db_path=test_db
            )
            self.assertTrue(tid.startswith("TICK-"))

            # 2. Retrieve ticket
            t = ticket_store.get_ticket(tid, db_path=test_db)
            self.assertIsNotNone(t)
            self.assertEqual(t["status"], "Open")
            self.assertEqual(t["urgency"], "High")
            self.assertEqual(t["message"], "Card se double deduction ho gaya")

            # 3. Update ticket (In Review + notes)
            ticket_store.update_ticket(
                tid,
                status="In Review",
                agent_response="We are contacting your bank.",
                internal_notes="Investigating auth ID #49281",
                db_path=test_db
            )
            t_updated = ticket_store.get_ticket(tid, db_path=test_db)
            self.assertEqual(t_updated["status"], "In Review")
            self.assertEqual(t_updated["agent_response"], "We are contacting your bank.")
            self.assertEqual(t_updated["internal_notes"], "Investigating auth ID #49281")

            # 4. Resolve ticket
            ticket_store.update_ticket(tid, status="Resolved", db_path=test_db)
            t_resolved = ticket_store.get_ticket(tid, db_path=test_db)
            self.assertEqual(t_resolved["status"], "Resolved")

            # 5. Invalid status raises ValueError
            with self.assertRaises(ValueError):
                ticket_store.update_ticket(tid, status="InvalidStatus", db_path=test_db)

            # 6. Non-existent ticket returns None
            self.assertIsNone(ticket_store.get_ticket("TICK-NONEXIST", db_path=test_db))

            # 7. Stats
            stats = ticket_store.get_stats(db_path=test_db)
            self.assertEqual(stats["total"], 1)
            self.assertEqual(stats["resolved"], 1)
            self.assertEqual(stats["open"], 0)

            # 8. Settings persistence
            ticket_store.set_setting("confidence_threshold", 0.55, db_path=test_db)
            self.assertEqual(ticket_store.get_setting("confidence_threshold", db_path=test_db), 0.55)

            # 9. Agent management and ticket assignment
            agents = ticket_store.get_agents(db_path=test_db)
            self.assertTrue(len(agents) >= 3)
            new_aid = ticket_store.add_agent("Test Agent", "test@support.local", "Triage Lead", db_path=test_db)
            self.assertTrue(new_aid.startswith("AGT-"))
            ticket_store.assign_ticket(tid, "Test Agent", db_path=test_db)
            t_assigned = ticket_store.get_ticket(tid, db_path=test_db)
            self.assertEqual(t_assigned["assigned_agent"], "Test Agent")

            # 10. Sanitized export privacy (internal_notes excluded)
            df_export = ticket_store.export_sanitized_tickets_df(db_path=test_db)
            self.assertIn("ticket_id", df_export.columns)
            self.assertIn("assigned_agent", df_export.columns)
            self.assertNotIn("internal_notes", df_export.columns)
        finally:
            if os.path.exists(test_db):
                try:
                    os.remove(test_db)
                except OSError:
                    pass


if __name__ == "__main__":
    print("=" * 60)
    print("1. RUNNING CODE-MIXED EVALUATION BENCHMARK")
    print("=" * 60)
    run_tests(verbose=True)

    print("\n" + "=" * 60)
    print("2. RUNNING AUTOMATED UNIT TESTS (MOCKING API CALLS)")
    print("=" * 60)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestTriageSystem)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        exit(1)
