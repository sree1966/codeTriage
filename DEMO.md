# 3-minute demo script

1. **Problem (20s)** – Indian customers write to support in Tanglish/Hinglish ("Refund innum varala"). Standard English
   classifiers struggle, so we triage them: intent, urgency, a draft reply, and a human hand-off when we're unsure.
2. **Data honesty (20s)** – Open *Dataset statistics*. "Bitext is synthetic English with 27 intents. We did not train on real
   Tanglish/Hinglish; we added a code-mixed word-normalization layer plus ~60 hand-written seed examples."
3. **Confident case (40s)** – Triage inbox → example "Refund innum varala, please check pannunga."
   Point at intent, urgency, confidence, Tanglish detection, suggested reply, and *Why this result?* (the normalized text).
4. **High urgency (30s)** – "URGENT: mere card se do baar paise kat gaye, ye fraud lagta hai!" → High urgency, shows which
   keywords fired, and is routed to a human because it's a high-urgency payment case.
5. **Uncertain case (30s)** – "Bro, app romba slow, enna pannalam?" → **Needs human review** with reasons; reply is only a
   holding message. Drag the threshold slider to show it is configurable.
6. **Test suite (30s)** – *Test suite* tab: 45 team-written messages, pass rate, expected vs predicted, escalation status.
   Say clearly: "This is a small team-written set, not a benchmark of Indian languages."
7. **Dashboard (10s)** – *Ticket dashboard*: volume by intent and urgency from the tickets you just submitted.

Likely questions: *Why not an LLM?* Offline, free, explainable, runs in the 2-hour limit. *Biggest weakness?* Small lexicon and
English-only training data; unfamiliar spellings get escalated rather than guessed. *Next step?* Collect real labeled
code-mixed tickets and fine-tune a multilingual model.
