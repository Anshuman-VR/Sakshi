# Sakshi — Zero-Knowledge Decision Evidence for Digital Lending

> "Every AI credit decision, independently verifiable. No raw data shared. No model weights exposed."

## What it does

Sakshi is an evidence layer for AI-driven loan decisions. It wraps every inference in a
cryptographic receipt that anyone — a lender, auditor, or RBI Ombudsman — can verify
independently, without seeing the applicant's data or the LSP's model.

## Quick Start (single command)

```bash
cd /home/kali/MCPWork/TejasMVP/sakshi
python3 run.py
```

This will:
1. Train the credit model and export to ONNX
2. Register the model hash in the policy registry
3. Run 3 demo decisions with tamper detection
4. Start the dashboard at http://localhost:5001

## Manual steps

```bash
# 1. Train model
python3 models/train_model.py

# 2. Run gateway demo (3 decisions + Merkle batch)
python3 gateway/gateway.py

# 3. Verify all decisions + tamper detection demo
python3 verifier/verifier.py

# 4. Start dashboard
python3 dashboard/app.py
# → open http://localhost:5001
```

## Architecture

```
Borrower → Loan App (LSP) → Sakshi Gateway → Decision Record
                                  │               │
                          ① Hash check       ② Input commitment
                          ③ RSA signature    ④ Merkle batch
                          ⑤ ZK proof (EZKL)
                                  │
                         External Witness (Merkle root log)
                                  │
                    Lender / Auditor / Ombudsman
                    → verify: sig ✓ + hash ✓ + Merkle ✓ + ZK ✓
```

## Three personas

| Persona | What they see | What Sakshi gives them |
|---------|---------------|----------------------|
| Borrower (Priya) | Loan app, decision, certificate ID | Independent receipt to dispute with |
| Lender (Arjun) | Compliance dashboard | Continuous model integrity + verified evidence packages |
| LSP (Vikram) | API integration | Governance compliance without sharing model weights |

## Components

| File | Purpose |
|------|---------|
| `models/train_model.py` | Train LR model, export ONNX, register hash |
| `gateway/gateway.py` | Hash check, commitment, signing, Merkle batching |
| `verifier/verifier.py` | Independent verification + tamper detection |
| `dashboard/app.py` | Flask API + three-persona web dashboard |

## Tamper detection proof

When a record is altered (e.g. REJECT flipped to APPROVE):
- ❌ RSA signature fails — record bytes no longer match signed payload
- ❌ SHA-256 hash fails — computed hash ≠ stored hash
- ✅ Merkle root still matches (the root was published to external witness before tampering)

All three checks must pass for a decision to be VERIFIED.

## Regulatory alignment

- RBI Digital Lending Guidelines 2022
- RBI Draft Model Risk Management Guidelines (model change detection)
- DPDP Act 2023 (no raw data shared in verification)
- IndiaAI Safe & Trusted AI pillar (sovereign, offline verification)

## Team: TEJAS045 — SASTRA University
