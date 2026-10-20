"""
Sakshi - Real Credit Dataset Loader (LendingClub Real Loan Records)
Downloads real retail loan application dataset (9,578 real borrowers),
maps features to standard digital lending parameters (CIBIL bureau score, FOIR, income in INR),
and saves clean training data to model/data/lendingclub_clean.csv.
"""

import os
import sys
import urllib.request
import io
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from shared.types import FEATURE_ORDER

DATA_URL = "https://raw.githubusercontent.com/tirthajyoti/Machine-Learning-with-Python/master/Datasets/loan_data.csv"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "data")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "lendingclub_clean.csv")

def download_and_process():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Downloading real LendingClub credit dataset from: {DATA_URL}")
    req = urllib.request.Request(DATA_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        content = resp.read()
    
    raw_df = pd.read_csv(io.BytesIO(content))
    print(f"Raw dataset shape: {raw_df.shape}")
    
    # Process and map to canonical retail credit features
    clean_df = pd.DataFrame()
    
    # 1. Bureau Score: Real FICO score (600-850) mapped directly to CIBIL scale
    clean_df["bureau_score"] = raw_df["fico"].astype(float)
    
    # 2. Monthly Income: log.annual.inc converted to INR monthly income (approx ₹30k - ₹3L)
    annual_usd = np.exp(raw_df["log.annual.inc"])
    monthly_inr = (annual_usd / 12.0) * 40.0  # Normalized purchasing power to INR
    clean_df["monthly_income"] = np.round(monthly_inr, 2)
    
    # 3. FOIR (Fixed Obligation to Income Ratio): dti percentage to ratio (0.05 to 0.65)
    clean_df["foir"] = np.clip(raw_df["dti"] / 100.0, 0.05, 0.85).round(4)
    
    # 4. Loan Tenure: Standard personal loan tenure in months (36 months)
    clean_df["loan_tenure_months"] = 36.0
    
    # 5. Number of Active Loans / Derogatory credit accounts
    clean_df["num_active_loans"] = (raw_df["delinq.2yrs"] + raw_df["pub.rec"] + 1.0).astype(float)
    
    # 6. Inquiries in last 6 months (exact bureau metric)
    clean_df["num_enquiries_6m"] = raw_df["inq.last.6mths"].astype(float)
    
    # 7. Bank Account Age / Credit Line History (days to months)
    clean_df["bank_account_age_months"] = (raw_df["days.with.cr.line"] / 30.0).round(1)
    
    # 8. Loan Amount Requested (Derived from installment scaled to INR)
    clean_df["loan_amount_requested"] = (raw_df["installment"] * 36.0 * 20.0).round(2)
    
    # 9. Behavioural / Utilization Index (revolving line utilization 0.0 - 1.0)
    clean_df["behaviour_idx"] = np.clip(raw_df["revol.util"] / 100.0, 0.0, 1.0).round(4)
    
    # 10. Employment Type (Derived from purpose: 0=Salaried, 1=Self-Employed, 2=Other)
    purpose_map = {
        "debt_consolidation": 0.0,
        "credit_card": 0.0,
        "home_improvement": 0.0,
        "small_business": 1.0,
        "major_purchase": 0.0,
        "educational": 2.0,
        "all_other": 2.0
    }
    clean_df["employment_type"] = raw_df["purpose"].map(purpose_map).fillna(0.0)
    
    # Target Underwriting Decision:
    # Underwriting Policy: approved if borrower met credit policy AND paid in full
    # 1 = Approved / Creditworthy, 0 = High Default Risk
    clean_df["decision"] = np.where(
        (raw_df["credit.policy"] == 1) & (raw_df["not.fully.paid"] == 0),
        1,
        0
    )
    
    # Ensure exact column order matches FEATURE_ORDER
    ordered_cols = [c for c in FEATURE_ORDER if c in clean_df.columns] + ["decision"]
    final_df = clean_df[ordered_cols]
    
    final_df.to_csv(OUTPUT_PATH, index=False)
    print(f"Clean real credit dataset saved to: {OUTPUT_PATH}")
    print(f"Total rows: {len(final_df)} | Approvals: {sum(final_df['decision'] == 1)} | Rejections: {sum(final_df['decision'] == 0)}")
    return OUTPUT_PATH

if __name__ == "__main__":
    download_and_process()
