"""Step 2: check that the CSV loads and that every test-case label exists in it.
Run:  python check_data.py
"""
import pandas as pd

from test_cases import TEST_CASES

df = pd.read_csv("data/customer_support.csv")
print("shape:", df.shape)
print("columns:", df.columns.tolist())
print(df.head(3).to_string())
print("\nmissing values per column:\n", df.isna().sum())
print("\nIntents (%d):" % df.intent.nunique())
print(df.intent.value_counts().to_string())
print("\nCategories (%d):" % df.category.nunique())
print(df.category.value_counts().to_string())

labels = set(df.intent.dropna().unique())
bad = sorted({t[1] for t in TEST_CASES if t[1] not in labels})
print("\nTest-case labels missing from dataset:", bad if bad else "none (all labels are real Bitext intents)")
