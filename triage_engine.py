"""Core triage logic: code-mixed normalization, urgency rules, prediction,
escalation and reply drafting. Fully offline (no API calls)."""
import os
import re

import joblib
import numpy as np
from sklearn.metrics.pairwise import linear_kernel

MODEL_PATH = os.path.join("model", "triage_model.joblib")
CONF_THRESHOLD = 0.45  # below this -> escalate to a human

# ---------------------------------------------------------------------------
# 1. Code-mixed lexicon: romanized Hinglish / Tanglish word -> English
#    ("" = filler word that is dropped). Words that are also common English
#    words (do, me, to, hi, a ...) are intentionally left out.
# ---------------------------------------------------------------------------
HINGLISH = {
    "mera": "my", "meri": "my", "mere": "my", "apna": "my", "apne": "my", "apni": "my",
    "mujhe": "i", "main": "i", "hum": "we", "aap": "you", "aapka": "your", "aapki": "your",
    "chahiye": "want", "chahta": "want", "chahti": "want", "chahte": "want",
    "karna": "", "karni": "", "karo": "", "kardo": "", "kar": "", "karu": "", "karun": "",
    "kijiye": "", "kijiyega": "", "dijiye": "", "diya": "", "diye": "",
    "kab": "when", "kahan": "where", "kaha": "where", "kahaan": "where",
    "kyun": "why", "kyu": "why", "kaise": "how", "kya": "what", "kitne": "how many",
    "kitna": "how much", "kitni": "how much", "din": "days", "lagega": "take", "lagenge": "take",
    "lagegi": "take", "nahi": "not", "nahin": "not", "nhi": "not",
    "mila": "received", "mili": "received", "milega": "receive", "milegi": "receive",
    "aaya": "arrived", "aayi": "arrived", "aaye": "arrived", "pahunchega": "arrive",
    "pahuchega": "arrive", "pahuncha": "arrived", "paisa": "money", "paise": "money",
    "rupaye": "money", "wapas": "back refund", "vapas": "back refund",
    "raddh": "cancel", "radd": "cancel", "band": "close", "badalna": "change",
    "badal": "change", "badlo": "change", "pata": "address", "khata": "account",
    "khaata": "account", "bill": "invoice", "shikayat": "complaint",
    "shikayaat": "complaint", "dhokha": "fraud", "dhoka": "fraud", "bakwas": "terrible",
    "ghatiya": "terrible", "kharab": "bad", "galat": "wrong", "toota": "damaged",
    "tuta": "damaged", "jaldi": "urgent", "turant": "immediately urgent", "abhi": "now",
    "bhool": "forgot", "bhul": "forgot", "gaya": "", "gayi": "", "gaye": "",
    "hai": "", "hain": "", "hu": "", "hoon": "", "tha": "", "thi": "", "ho": "",
    "hua": "", "hui": "", "raha": "", "rahi": "", "rahe": "", "ka": "", "ki": "",
    "ke": "", "ko": "", "se": "", "ne": "", "par": "", "pe": "", "mein": "",
    "lekin": "but", "aur": "and", "ya": "or", "bhejo": "send", "bhej": "send",
    "bhejna": "send", "baat": "talk", "baatcheet": "talk", "insaan": "human",
    "insan": "human", "banda": "human", "sampark": "contact", "naya": "new",
    "naye": "new", "banana": "create", "banao": "create", "banwana": "create",
    "hatao": "delete", "hatana": "delete", "mitao": "delete", "kata": "deducted",
    "kat": "deducted", "kaat": "deducted", "baar": "times", "dobara": "again",
    "sahi": "correct", "dikhao": "show", "batao": "tell", "bataiye": "tell",
    "madad": "help", "sahayata": "help", "pareshan": "upset", "darj": "file",
    "deduct": "deducted", "likhna": "write", "likhni": "write", "sakta": "can", "sakti": "can",
    "jagah": "instead of", "chalu": "start", "kaam": "work", "bahut": "very",
    "bohot": "very", "zyada": "too much", "galti": "mistake", "se.": "",
}

TANGLISH = {
    "enakku": "i", "ennaku": "i", "enaku": "i", "ennakku": "i", "naan": "i", "nan": "i",
    "ennoda": "my", "en": "my", "ungal": "your", "unga": "your", "ungala": "you",
    "venum": "want", "vendum": "want", "venumnu": "want", "illa": "not", "illai": "not",
    "ila": "not", "eppo": "when", "eppadi": "how", "epdi": "how", "enga": "where",
    "engae": "where", "enna": "what", "ena": "what", "yen": "why", "evlo": "how many",
    "evvalavu": "how much", "naal": "days", "naalu": "days", "aagum": "take",
    "pannunga": "", "pannungo": "", "pannu": "", "panna": "", "pannanum": "",
    "pannanu": "", "panren": "", "pannen": "", "pannita": "", "pannitten": "",
    "pannuvingala": "", "pannitanga": "", "pannittanga": "", "seiyunga": "", "seyyunga": "", "kudunga": "give",
    "tharuveenga": "", "thaanga": "", "thanga": "", "kasu": "money", "kaasu": "money",
    "panam": "money", "thirumba": "back refund", "thirumbi": "back refund",
    "thiruppi": "back refund", "vara": "arrive", "varala": "not arrived",
    "varalai": "not arrived", "varum": "arrive", "varuvadharku": "arrive",
    "varudhu": "", "vandhuchu": "arrived", "vanthuchu": "arrived", "sernthuchu": "reached",
    "kidaikala": "not received", "kedaikala": "not received", "kidaikkala": "not received",
    "mudiyala": "cannot", "mudiyadhu": "cannot", "mudiyum": "can", "mathunga": "change",
    "maathunga": "change", "mathanum": "change", "maathanum": "change",
    "mugavari": "address", "vilasam": "address", "kanakku": "account", "kanaku": "account",
    "azhikka": "delete", "alikka": "delete", "azhichidunga": "delete",
    "maranthutten": "forgot", "marandhuten": "forgot", "maranthuten": "forgot",
    "marandhutten": "forgot", "pesanum": "talk", "pesanumnu": "talk", "pesa": "talk",
    "manushan": "human", "manusha": "human", "aal": "human", "oruthar": "human",
    "kooda": "with", "oru": "", "irukku": "", "iruku": "", "irukkum": "", "ulla": "",
    "oda": "", "dhaan": "", "dhan": "", "nu": "", "nnu": "", "ku": "", "kku": "",
    "romba": "very", "rombha": "very", "seekiram": "urgent", "seekirama": "urgent",
    "udane": "immediately urgent", "udanadiya": "immediately urgent",
    "udanadiyaga": "immediately urgent", "mosam": "terrible", "mokka": "terrible",
    "thappa": "wrong", "thappu": "wrong", "thapa": "wrong", "poten": "put", "potten": "put", "emathitanga": "cheated fraud",
    "emathittanga": "cheated fraud", "emaathitanga": "cheated fraud",
    "emathitaanga": "cheated fraud", "kuduthen": "paid", "kattinen": "paid",
    "kattitten": "paid", "pudhu": "new", "puthusa": "new", "puthu": "new",
    "udainjiduchu": "damaged", "udanjiduchu": "damaged", "sariyilla": "wrong",
    "sollunga": "tell", "kaattunga": "show", "pathi": "about", "patri": "about",
    "anuppunga": "send", "anuppu": "send", "anupunga": "send", "anuppuren": "send",
    "ippo": "now", "ippove": "now", "inniki": "today", "innum": "still",
    "poiduchu": "deducted", "pochu": "deducted", "poiduchi": "deducted",
    "aagala": "not happened", "aagalai": "not happened", "eluthanum": "write",
    "eluthu": "write", "rendu": "two", "dhadava": "times", "thadava": "times",
}

LEXICON = {**HINGLISH, **TANGLISH}

_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)


def clean_tokens(text):
    t = str(text).lower()
    t = re.sub(r"\{\{.*?\}\}", " ", t)  # Bitext placeholders like {{Order Number}}
    t = _PUNCT.sub(" ", t)
    return t.split()


def normalize(text):
    """Map code-mixed words to English so the English-trained model can use them."""
    out = [LEXICON.get(tok, tok) for tok in clean_tokens(text)]
    return re.sub(r"\s+", " ", " ".join(out)).strip()


def detect_language(text):
    toks = set(clean_tokens(text))
    h = sum(1 for t in toks if t in HINGLISH)
    ta = sum(1 for t in toks if t in TANGLISH)
    if h == 0 and ta == 0:
        return "English"
    return "Hinglish" if h >= ta else "Tanglish"


# ---------------------------------------------------------------------------
# 2. Urgency rules (explainable: we return the keywords that fired)
# ---------------------------------------------------------------------------
HIGH_KW = [
    "fraud", "unauthorized", "unauthorised", "scam", "hacked", "stolen", "cheated",
    "urgent", "immediately", "asap", "emergency", "legal", "consumer court", "police",
    "safety", "unsafe", "dangerous", "account hacked",
    "charged twice", "double charge", "money deducted", "deducted", "not my transaction",
    "account blocked", "locked out", "locked", "lost money",
]
MED_KW = [
    "refund", "not received", "not arrived", "delay", "delayed", "late", "wrong",
    "damaged", "broken", "defective", "complaint", "terrible", "bad", "problem", "issue",
    "cannot", "cancel", "not working", "failed", "error", "twice", "poor", "upset",
    "failed delivery", "not delivered", "wrong product", "wrong item", "refund delay",
]
URGENCY_FLOOR = {"complaint": "Medium", "payment_issue": "Medium"}
_RANK = {"Low": 0, "Medium": 1, "High": 2}


def _find(keywords, blob):
    return [k for k in keywords if re.search(r"\b" + re.escape(k) + r"\b", blob)]


def detect_urgency(raw, norm, intent=None):
    blob = str(raw).lower() + " " + norm
    high, med = _find(HIGH_KW, blob), _find(MED_KW, blob)
    if high:
        return "High", [f"high-urgency keyword: '{k}'" for k in high]
    level, reasons = "Low", []
    if med:
        level, reasons = "Medium", [f"medium-urgency keyword: '{k}'" for k in med]
    floor = URGENCY_FLOOR.get(intent)
    if floor and _RANK[floor] > _RANK[level]:
        level, reasons = floor, reasons + [f"intent '{intent}' is at least {floor}"]
    return level, reasons or ["no urgency keywords found"]


# ---------------------------------------------------------------------------
# 3. Reply drafting (template based, in the customer's language mix)
# ---------------------------------------------------------------------------
ACTIONS = {
    "cancel_order": "We can cancel your order if it has not shipped yet. Please share your order number and we will process it.",
    "change_order": "We can modify your order before it ships. Please share the order number and the change you need.",
    "change_shipping_address": "Please share your order number and the new address, and we will update it before dispatch.",
    "check_cancellation_fee": "Cancellation charges depend on the order status. Share your order number and we will confirm the exact fee.",
    "check_invoice": "Please share your order number and we will show you the invoice details.",
    "check_payment_methods": "We accept UPI, cards, net banking and cash on delivery on eligible orders.",
    "check_refund_policy": "Eligible items can be returned within the return window and refunded to the original payment method.",
    "complaint": "We are sorry for the trouble. Your complaint has been logged and a team member will look into it.",
    "contact_customer_service": "Our support team is available to help. Tell us what you need and we will assist you.",
    "contact_human_agent": "We are connecting you to a human support agent.",
    "create_account": "You can create an account from the Sign Up page using your email or phone number.",
    "delete_account": "We can delete your account after identity verification. Please confirm your registered email or phone.",
    "delivery_options": "We offer standard and express delivery. Options vary by pincode.",
    "delivery_period": "Standard delivery usually takes 3-7 working days depending on your location.",
    "edit_account": "You can update your details under Account > Profile. We can also help if you tell us what to change.",
    "get_invoice": "We will email the invoice to your registered email shortly.",
    "get_refund": "Please share your order number. Eligible refunds are processed to the original payment method.",
    "newsletter_subscription": "We have updated your newsletter preference.",
    "payment_issue": "Please share the transaction ID or order number. We will check the payment and any deducted amount.",
    "place_order": "You can place your order from the app or website. Tell us if you face any problem at checkout.",
    "recover_password": "Use 'Forgot Password' on the login page and follow the reset link we send to your email.",
    "registration_problems": "Sorry about the sign-up trouble. Please share the error you see and we will fix it.",
    "review": "Thanks for wanting to share feedback. You can add a review from the product page under Your Orders.",
    "set_up_shipping_address": "You can add a delivery address under Account > Addresses. We can help if needed.",
    "switch_account": "Please log out and log in with the other account. We can help link or switch accounts if needed.",
    "track_order": "Please share your order number. You can also track it under My Orders.",
    "track_refund": "Refunds usually reach you within 5-7 working days. Share your order number to check the status.",
}
GENERIC_ACTION = "Thanks for reaching out. Please share a few more details so we can help."

WRAP = {
    "English": ("Hello! Thanks for contacting us.", "We will update you shortly.",
                "We have marked this as urgent.",
                "A human support agent will review your case and contact you shortly."),
    "Hinglish": ("Namaste! Aapka message mil gaya.", "Hum jald hi aapko update denge, dhanyavaad!",
                 "Isse urgent mark kiya gaya hai.",
                 "Hamara support agent aapka case dekhega aur jaldi sampark karega."),
    "Tanglish": ("Vanakkam! Ungal message kidaichiduchu.", "Seekiram update tharom, nandri!",
                 "Idhai urgent-nu mark pannirukom.",
                 "Oru support agent ungal case-a paathu seekiram thodarbu kolvaar."),
}


def draft_reply(intent, language, urgency, escalate):
    hello, bye, urgent_line, human_line = WRAP.get(language, WRAP["English"])
    parts = [hello]
    if urgency == "High":
        parts.append(urgent_line)
    parts.append(human_line if escalate else ACTIONS.get(intent, GENERIC_ACTION))
    parts.append(bye)
    return " ".join(parts)


# ---------------------------------------------------------------------------
# 4. Model loading + triage
# ---------------------------------------------------------------------------
_BUNDLE = None


def load_bundle(path=MODEL_PATH):
    global _BUNDLE
    if _BUNDLE is None:
        if not os.path.exists(path):
            raise FileNotFoundError(f"{path} not found. Run:  python train_model.py")
        _BUNDLE = joblib.load(path)
    return _BUNDLE


def triage(text, threshold=CONF_THRESHOLD):
    b = load_bundle()
    vec, model = b["vectorizer"], b["model"]
    norm = normalize(text)
    if not norm:
        return None
    X = vec.transform([norm])
    proba = model.predict_proba(X)[0]
    order = np.argsort(proba)[::-1]
    intent = model.classes_[order[0]]
    conf = float(proba[order[0]])
    top3 = [(model.classes_[i], float(proba[i])) for i in order[:3]]

    # similar training examples (cosine similarity on TF-IDF) + kNN vote
    sims = linear_kernel(X, b["X_index"]).ravel()
    idx = np.argsort(sims)[-5:][::-1]
    similar = [{"example": b["index_texts"][i], "intent": b["index_labels"][i],
                "similarity": float(sims[i])} for i in idx[:3]]
    votes = {}
    for i in idx:
        votes[b["index_labels"][i]] = votes.get(b["index_labels"][i], 0) + sims[i]
    knn_intent = max(votes, key=votes.get) if votes and max(votes.values()) > 0 else None

    # vocabulary coverage: how much of the (normalized) message the model has seen
    toks = [t for t in norm.split() if len(t) >= 3]
    vocab = vec.vocabulary_
    coverage = sum(t in vocab for t in toks) / len(toks) if toks else 0.0

    urgency, urgency_reasons = detect_urgency(text, norm, intent)
    language = detect_language(text)

    reasons = []
    if conf < threshold:
        reasons.append(f"Low confidence ({conf:.0%} is below the {threshold:.0%} threshold)")
    if len(top3) > 1 and top3[0][1] - top3[1][1] < 0.08 and conf < 0.6:
        reasons.append(f"Top two intents are close: {top3[0][0]} vs {top3[1][0]}")
    if coverage < 0.4:
        reasons.append("Most words in the message were not seen in training (unfamiliar code-mixed wording)")
    if knn_intent and knn_intent != intent and conf < 0.7:
        reasons.append(f"Similar past examples point to a different intent ({knn_intent})")
    if intent == "contact_human_agent":
        reasons.append("Customer asked for a human agent")
    if urgency == "High" and intent in ("complaint", "payment_issue"):
        reasons.append("High-urgency complaint/payment case needs human review")

    escalate = bool(reasons)
    return {
        "text": text, "normalized": norm, "language": language,
        "intent": intent, "category": b["intent_to_category"].get(intent, ""),
        "confidence": conf, "top3": top3,
        "urgency": urgency, "urgency_reasons": urgency_reasons,
        "escalate": escalate, "escalation_reasons": reasons,
        "reply": draft_reply(intent, language, urgency, escalate),
        "similar": similar, "knn_intent": knn_intent, "coverage": coverage,
    }
