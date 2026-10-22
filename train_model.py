"""Train TF-IDF + Logistic Regression on the Bitext dataset (+ rich code-mixed seeds).

Usage:  python train_model.py [--data data/customer_support.csv]
"""
import argparse
import json
import os
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import train_test_split

from seed_codemixed import SEEDS
from test_cases import TEST_CASES, run_tests
from triage_engine import MODEL_PATH, normalize

parser = argparse.ArgumentParser()
parser.add_argument("--data", default=os.path.join("data", "customer_support.csv"))
args = parser.parse_args()

print("=" * 70)
print("NEXAI MODEL TRAINING & EVALUATION PIPELINE")
print("=" * 70)

# ---- 1. Load + Validate Dataset --------------------------------------------
df = pd.read_csv(args.data)
print(f"Loaded raw dataset: {df.shape[0]:,} rows, columns: {df.columns.tolist()}")
need = {"instruction", "intent", "category"}
if not need.issubset(df.columns):
    sys.exit(f"Missing required columns: {need - set(df.columns)}")

df = df[["instruction", "intent", "category"]].dropna()
for c in df.columns:
    df[c] = df[c].astype(str).str.strip()
df = df[(df.instruction != "") & (df.intent != "")]
print(f"Valid clean rows: {df.shape[0]:,} | Intents: {df.intent.nunique()} | Categories: {df.category.nunique()}")

# Dataset statistics for Streamlit Dataset tab
os.makedirs("results", exist_ok=True)
with open(os.path.join("results", "dataset_stats.json"), "w", encoding="utf-8") as f:
    json.dump({
        "rows_total": int(len(df)),
        "n_intents": int(df.intent.nunique()),
        "n_categories": int(df.category.nunique()),
        "intent_counts": df.intent.value_counts().to_dict(),
        "category_counts": df.category.value_counts().to_dict(),
    }, f, indent=2)

# ---- 2. Consistent Text Normalization & De-duplication ----------------------
df["norm"] = df.instruction.map(normalize)
df = df[df.norm != ""].drop_duplicates(subset="norm").reset_index(drop=True)
print(f"After text normalization & deduplication: {df.shape[0]:,} unique rows")

intent_to_category = df.groupby("intent").category.agg(lambda s: s.mode().iat[0]).to_dict()

# ---- 3. Stratified Split (Held-out Bitext Test Set) -------------------------
strat = df.intent if df.intent.value_counts().min() >= 2 else None
train_df, test_df = train_test_split(df, test_size=0.2, random_state=42, stratify=strat)
print(f"Training split: {len(train_df):,} rows | Held-out test split: {len(test_df):,} rows")

# ---- 4. Code-Mixed Training Seeds & Strict Leakage Guard --------------------
seed_df = pd.DataFrame(SEEDS, columns=["instruction", "intent"])
seed_df["norm"] = seed_df.instruction.map(normalize)
seed_df["category"] = seed_df.intent.map(intent_to_category).fillna("")
seed_df = seed_df.drop_duplicates(subset="norm").reset_index(drop=True)

# Validate seed labels
unknown_labels = set(seed_df.intent) - set(df.intent)
if unknown_labels:
    sys.exit(f"ERROR: Seed intents not in Bitext dataset: {unknown_labels}")

# Strict leakage guard: seed normalized text must NEVER match held-out test messages
test_case_norms = {normalize(t[0]) for t in TEST_CASES}
overlap = set(seed_df.norm) & test_case_norms
if overlap:
    sys.exit(f"CRITICAL ERROR: Data leakage detected! Seeds overlap with test cases: {overlap}")

print(f"Verified {len(seed_df)} unique code-mixed training seeds (0 leakage overlap with test cases).")

# Upweight seeds (x8) to provide sufficient density against 21k English rows
fit_df = pd.concat([train_df] + [seed_df] * 8, ignore_index=True)
print(f"Total training corpus size after code-mixed weighting: {len(fit_df):,} rows")

# ---- 5. TF-IDF + Logistic Regression Fitting --------------------------------
vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True, max_features=40000)
print("Fitting TF-IDF vectorizer (ngram_range=(1,2), min_df=2, sublinear_tf=True)...")
X_fit = vec.fit_transform(fit_df.norm)

print("Training Logistic Regression (C=10, max_iter=350)...")
model = LogisticRegression(max_iter=350, C=10)
model.fit(X_fit, fit_df.intent)

# ---- 6. Evaluate on Held-out Bitext Split -----------------------------------
print("\n" + "=" * 70)
print("1. EVALUATION ON HELD-OUT BITEXT TEST SET (SYNTHETIC ENGLISH)")
print("=" * 70)
X_test = vec.transform(test_df.norm)
bitext_pred = model.predict(X_test)
bitext_acc = accuracy_score(test_df.intent, bitext_pred)
bitext_macro_f1 = f1_score(test_df.intent, bitext_pred, average="macro")
report = classification_report(test_df.intent, bitext_pred, digits=3, zero_division=0)
print(f"Held-out Bitext Accuracy: {bitext_acc:.3f} | Macro-F1: {bitext_macro_f1:.3f} (n={len(test_df):,})")

# ---- 7. Evaluate on Realistic Code-Mixed Test Set (45 Cases) ----------------
print("\n" + "=" * 70)
print("2. EVALUATION ON REALISTIC CODE-MIXED TEST SET (45 TANGLISH/HINGLISH CASES)")
print("=" * 70)
cm_preds = []
cm_confs = []
cm_oks = []
classes = list(model.classes_)

for text, exp_intent, _ in TEST_CASES:
    norm_t = normalize(text)
    x_c = vec.transform([norm_t])
    probs = model.predict_proba(x_c)[0]
    top_idx = int(np.argmax(probs))
    pred_label = classes[top_idx]
    conf = float(probs[top_idx])
    cm_preds.append(pred_label)
    cm_confs.append(conf)
    cm_oks.append(pred_label == exp_intent)

cm_acc = np.mean(cm_oks)
cm_avg_conf = np.mean(cm_confs)
exp_intents = [t[1] for t in TEST_CASES]
cm_macro_f1 = f1_score(exp_intents, cm_preds, average="macro", zero_division=0)

print(f"Code-mixed Accuracy  : {cm_acc:.1%} ({np.sum(cm_oks)}/45)")
print(f"Code-mixed Macro-F1  : {cm_macro_f1:.3f}")
print(f"Mean Confidence Score: {cm_avg_conf:.1%}")

# Target example check
target_idx = [i for i, t in enumerate(TEST_CASES) if "box damaged" in t[0]][0]
target_text = TEST_CASES[target_idx][0]
target_pred = cm_preds[target_idx]
target_conf = cm_confs[target_idx]
print(f"Target Complaint     : \"{target_text}\"")
print(f"Target Prediction    : {target_pred} (Confidence: {target_conf:.1%})")

# Confusion matrix for code-mixed test cases
unique_labels = sorted(list(set(exp_intents) | set(cm_preds)))
cm_matrix = confusion_matrix(exp_intents, cm_preds, labels=unique_labels)
cm_df = pd.DataFrame(cm_matrix, index=unique_labels, columns=unique_labels)
cm_df.to_csv(os.path.join("results", "confusion_matrix.csv"))

# Save evaluation summary
with open(os.path.join("results", "evaluation_metrics.txt"), "w", encoding="utf-8") as f:
    f.write("NEXAI MODEL EVALUATION REPORT\n")
    f.write("=" * 45 + "\n\n")
    f.write(f"Held-out Bitext Test Split (n={len(test_df):,}):\n")
    f.write(f"  - Accuracy: {bitext_acc:.3f}\n")
    f.write(f"  - Macro-F1: {bitext_macro_f1:.3f}\n\n")
    f.write(f"Realistic Code-Mixed Benchmark (n={len(TEST_CASES)}):\n")
    f.write(f"  - Accuracy: {cm_acc:.1%}\n")
    f.write(f"  - Macro-F1: {cm_macro_f1:.3f}\n")
    f.write(f"  - Mean Confidence: {cm_avg_conf:.1%}\n")
    f.write(f"  - Target Case Confidence: {target_conf:.1%}\n\n")
    f.write(f"Bitext Classification Report:\n{report}\n")

# ---- 8. Save Trained Model Bundle ------------------------------------------
idx_df = pd.concat([train_df, seed_df], ignore_index=True).drop_duplicates(subset="norm")
bundle = {
    "vectorizer": vec,
    "model": model,
    "intent_to_category": intent_to_category,
    "X_index": vec.transform(idx_df.norm),
    "index_texts": idx_df.instruction.tolist(),
    "index_labels": idx_df.intent.tolist(),
}
os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
joblib.dump(bundle, MODEL_PATH, compress=3)
print(f"\nSaved updated model bundle to: {MODEL_PATH}")

with open(os.path.join("results", "classification_report.txt"), "w", encoding="utf-8") as f:
    f.write(f"Held-out Bitext accuracy: {bitext_acc:.3f}\n\n{report}")

# ---- 9. Run Test Cases & Refresh Results -----------------------------------
print("\n" + "=" * 70)
print("3. EXECUTING FULL TEST SUITE RUNNER")
print("=" * 70)
run_tests(verbose=True)
