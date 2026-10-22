"""NEXAI - Gemini LLM Response Generation Module.

Generates natural, context-aware, code-mixed customer support responses using
Google GenAI SDK (google-genai) and Gemini models, honoring triage classification
and human-escalation decisions.
"""
import os
import re
from typing import List, Optional, Union
from dotenv import find_dotenv, load_dotenv

# Load .env searching from current working directory upward
load_dotenv(find_dotenv(usecwd=True))

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
FALLBACK_MODELS = [DEFAULT_MODEL, "gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-flash-latest"]


def get_api_key() -> Optional[str]:
    """Retrieve the Gemini API key from environment, ensuring it's not a placeholder."""
    # Reload in case .env was edited at runtime
    load_dotenv(find_dotenv(usecwd=True), override=False)
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key or key == "YOUR_NEW_GEMINI_API_KEY":
        return None
    return key


def check_api_status() -> dict:
    """Check whether Gemini API is configured and operational without exposing secrets."""
    key = get_api_key()
    if not key:
        return {
            "configured": False,
            "status": "missing_key",
            "message": "Gemini API key is not configured. Add GEMINI_API_KEY to .env.",
        }
    return {
        "configured": True,
        "status": "ready",
        "message": "Gemini API key detected.",
        "model": DEFAULT_MODEL,
    }


def generate_support_reply(
    message: str,
    intent: str = "Unknown",
    category: str = "Unknown",
    urgency: str = "Unknown",
    confidence: float = 0.0,
    escalate: bool = False,
    escalation_reason: Union[str, List[str]] = "",
    client=None,
    model_name: Optional[str] = None,
) -> str:
    """Generate a customer-support reply using Gemini LLM.

    Args:
        message: The raw customer complaint in English, Tanglish, or Hinglish.
        intent: The predicted intent from the triage classifier.
        category: The predicted category, if available.
        urgency: Urgency level (Low, Medium, High).
        confidence: Prediction confidence score (0.0 to 1.0).
        escalate: Boolean indicating if human escalation is required.
        escalation_reason: Reason(s) for human escalation if triggered.
        client: Optional pre-configured genai.Client instance (useful for testing/mocking).
        model_name: Optional model override.

    Returns:
        A concise, natural, safe customer-support draft reply.
    """
    if not message or not str(message).strip():
        return "Please provide a description of the issue so we can assist you."

    # Format escalation reasons cleanly
    if isinstance(escalation_reason, (list, tuple)):
        reasons_text = "; ".join(str(r) for r in escalation_reason)
    else:
        reasons_text = str(escalation_reason).strip()

    api_key = get_api_key()
    if not api_key and client is None:
        return (
            "⚠️ Gemini API key is not configured. "
            "Please add a valid GEMINI_API_KEY to your .env file to enable AI responses."
        )

    try:
        from google import genai
    except ImportError:
        return "google-genai SDK is not installed. Please run `pip install google-genai`."

    try:
        if client is None:
            client = genai.Client(api_key=api_key)

        if escalate:
            escalation_instructions = f"""
            CRITICAL SAFETY INSTRUCTIONS:
            - The classifier has flagged this complaint for HUMAN ESCALATION.
              Escalation reason: {reasons_text or 'Prediction confidence below safety threshold'}.
            - DO NOT resolve the case yourself or invent facts.
            - DO NOT claim that a refund, cancellation, transaction, or account change has been completed.
            - DO NOT fabricate order IDs, tracking links, or balances.
            - Clearly acknowledge the customer's issue with empathy and confirm that a human support specialist
              is reviewing their request and will follow up shortly.
            - If details like order number or transaction ID are missing, politely ask the customer to share them
              now so the support agent can resolve the ticket faster.
            """
        else:
            escalation_instructions = f"""
            INSTRUCTIONS:
            - Provide a helpful, concise next step or resolution for intent '{intent}' in category '{category}'.
            - Never invent or fabricate order details, transaction status, refund completion, or account changes.
            - Do not claim an action has been completed unless verified.
            - If key information is missing, ask a clear clarification question.
            """

        prompt = f"""
        You are an intelligent customer support triage assistant for NEXAI.
        You understand customer complaints written in English, Tanglish (Tamil + English), and Hinglish (Hindi + English).

        Customer Complaint:
        "{message.strip()}"

        Triage Metadata:
        - Predicted Intent: {intent}
        - Category: {category or 'General Support'}
        - Urgency: {urgency}
        - Classifier Confidence: {confidence:.1%}
        - Needs Human Escalation: {'YES' if escalate else 'NO'}

        Guidelines:
        1. Tone: Professional, courteous, and empathetic.
        2. Language: Match the customer's language style (English, Tanglish, or Hinglish) naturally and appropriately.
        3. Length: Keep it concise (2 to 4 sentences).
        {escalation_instructions}

        Respond directly to the customer now:
        """

        primary_model = model_name or os.getenv("GEMINI_MODEL") or DEFAULT_MODEL
        models_to_try = [primary_model] + [m for m in FALLBACK_MODELS if m != primary_model]

        last_error = None
        for candidate in models_to_try:
            try:
                response = client.models.generate_content(
                    model=candidate,
                    contents=prompt.strip(),
                )
                if response and response.text and response.text.strip():
                    return response.text.strip()
            except Exception as e:
                last_error = e
                # Try next model if 404 / 503 model availability issue
                continue

        # If all candidates failed
        if last_error:
            # Safe user-facing message, log without exposing credentials
            return (
                "The AI response service is temporarily experiencing high traffic. "
                "A support agent will assist you shortly."
            )

        return "No response could be generated. Please try again or reach out to support."

    except Exception:
        # Catch any unexpected failure and return safe message
        return (
            "The AI response service is currently unavailable. "
            "Please verify your connection and try again."
        )
