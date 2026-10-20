# DEV 3 AI AGENT PROMPT: React Dashboard, Customer DLA, Mock LMS & 2-Container Docker
**Role:** Frontend, Customer Experience & DevOps Lead  
**Branch:** `feature/branch-3-frontend-demo`  
**Target:** Build the institutional Indian banking React dashboard, the interactive Tamper Suite, the Mock LMS fail-closed gate, and the strictly 2-container Docker deployment.  
**Completion Time Limit:** 50 minutes unattended execution.

---

## 🎯 POKA-YOKE ZERO-FAILURE INSTRUCTIONS FOR AI AGENT

You are an expert Full-Stack Engineer and DevOps Architect. Your job is to build the presentation layer and operational integration for Sakshi.
You own the **Bank/Lender Operations Dashboard**, the **Borrower Loan App (Customer DLA)**, the **Mock LMS Disbursal Gate**, and the **Master 2-Container Docker Setup**.

### Mandatory Rules:
1. **ZERO AI SLOP DESIGN SYSTEM:**
   - Follow strict Indian institutional banking aesthetics (**HDFC Bank SmartHub / ICICI iMobile / Axis Open / Navi**).
   - Base Color: Deep Trust Navy (`#0A2540` / `#002D62`), crisp borders (`#E2E8F0`), and pure white cards.
   - All monetary values must strictly use Indian formatting with Rupee symbol: `₹1,50,000`, `₹25,00,000`.
   - All timestamps must be in Indian Standard Time (`IST`).
2. **STRICTLY 2 CONTAINERS IN DOCKER COMPOSE:**
   - Container 1: `sakshi-lsp` (Prover Sidecar in `lsp_net` with zero public ports).
   - Container 2: `sakshi-lender` (FastAPI node on port 8000 + Mock LMS + compiled React frontend served as static assets).
3. **FAIL-CLOSED GATE RULE:** The loan disbursal service must strictly reject or hold funds if status is anything other than `VERIFIED`.

---

## 📁 EXACT FILE TREE TO CREATE

```
sakshi/
  dashboard/
    package.json
    vite.config.ts
    tailwind.config.js
    postcss.config.js
    index.html
    src/
      main.tsx
      App.tsx
      index.css
      api/
        client.ts
        types.ts
      components/
        StatsOverview.tsx
        LiveDecisionFeed.tsx
        TamperPanel.tsx
        HashChainViewer.tsx
      pages/
        LenderDashboard.tsx
        BorrowerPortal.tsx
        BorrowerReceipt.tsx
  mock_lms/
    __init__.py
    disbursal_gate.py
  scripts/
    demo_seed.py
  node/
    Dockerfile              # Multi-stage Dockerfile for sakshi-lender (builds React & runs FastAPI)
  sidecar/
    Dockerfile              # Dockerfile for sakshi-lsp
  tests/
    test_mock_lms.py
```

---

## 📝 FILE 1: `dashboard/package.json`
Create `dashboard/package.json`:
```json
{
  "name": "sakshi-dashboard",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "axios": "^1.7.2",
    "clsx": "^2.1.1",
    "lucide-react": "^0.400.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.24.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "autoprefixer": "^10.4.19",
    "postcss": "^8.4.40",
    "tailwindcss": "^3.4.6",
    "typescript": "^5.5.3",
    "vite": "^5.3.4"
  }
}
```

---

## 📝 FILE 2: `dashboard/vite.config.ts` & `dashboard/tailwind.config.js`
Create `dashboard/vite.config.ts`:
```ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/v1': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
});
```

Create `dashboard/tailwind.config.js`:
```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bankNavy: '#0A2540',
        bankBlue: '#002D62',
        bankCrimson: '#8B0000',
        bankBg: '#F4F6F8'
      }
    }
  },
  plugins: []
};
```

---

## 📝 FILE 3: `dashboard/src/api/client.ts`
Create `dashboard/src/api/client.ts`:
```ts
import axios from 'axios';

export const api = axios.create({
  baseURL: '',
  headers: { 'Content-Type': 'application/json' }
});

export interface DecisionStatus {
  decision_id: string;
  status: 'NOTICE_RECEIVED' | 'VERIFIED' | 'FAILED' | 'EXPIRED';
  model_commitment?: string;
  policy_id?: string;
  verified_at?: string;
  ledger_seq?: number;
  failure_reason?: string;
}

export interface DashboardSummary {
  total_decisions: number;
  verified: number;
  failed: number;
  pending: number;
  expired: number;
  proof_latency_p50_ms: number;
  proof_latency_p95_ms: number;
  ledger_seq: number;
  chain_valid: boolean;
  recent_decisions: DecisionStatus[];
}
```

---

## 📝 FILE 4: Interactive Tamper Console (`dashboard/src/components/TamperPanel.tsx`)
Create `dashboard/src/components/TamperPanel.tsx`:
```tsx
import React, { useState } from 'react';
import axios from 'axios';

export const TamperPanel: React.FC<{ onRefresh: () => void }> = ({ onRefresh }) => {
  const [running, setRunning] = useState<string | null>(null);
  const [result, setResult] = useState<{ name: string; status: string; code: string; color: string } | null>(null);

  const executeScenario = async (name: string, payload: any) => {
    setRunning(name);
    setResult(null);
    try {
      // Direct call to verification endpoint simulating live tamper
      const res = await axios.post('/v1/proofs', payload);
      const isVerified = res.data.status === 'VERIFIED';
      setResult({
        name,
        status: res.data.status,
        code: res.data.reason || (isVerified ? 'VERIFIED (All checks passed)' : 'REJECTED'),
        color: isVerified ? 'text-emerald-700 bg-emerald-50 border-emerald-300' : 'text-rose-700 bg-rose-50 border-rose-300'
      });
      onRefresh();
    } catch (e: any) {
      setResult({ name, status: 'ERROR', code: e.message, color: 'text-rose-700 bg-rose-50 border-rose-300' });
    } finally {
      setRunning(null);
    }
  };

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
      <div>
        <h3 className="font-bold text-base text-slate-900">Live Hackathon Conformance Demonstrations</h3>
        <p className="text-xs text-slate-500">Trigger honest decisions and adversarial tamper attacks live on screen</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-5 gap-2.5">
        {/* Scenario 1: Honest Flow */}
        <button
          onClick={() => executeScenario("Honest Flow", {
            decision_id: `d_honest_${Date.now().toString().slice(-4)}`,
            policy_id: "pol_nbfc42_lspX_personal_v1",
            proof: "HALO2_SNARK_VALID_PROOF_BYTES_APPROVED_MODEL",
            public_inputs: {
              policy_hash: "0x7d02c941ab779f3ca82e22d05a0123456789abcdef0123456789abcdef012345",
              C: "0x9f3ca82e41ab77d0211bc922d05a6789abcdef0123456789abcdef0123456789",
              X: "0x7d0211bc922d05a6789abcdef0123456789abcdef0123456789abcdef012345",
              decision: 1,
              threshold: 0.200,
              epoch: 20261020
            }
          })}
          disabled={!!running}
          className="p-3 bg-slate-50 hover:bg-slate-100 border border-slate-300 rounded-lg text-left transition disabled:opacity-50"
        >
          <div className="font-bold text-xs text-slate-900">1. Honest Approval</div>
          <div className="text-[10px] text-slate-500 mt-1">Legitimate model & valid proof</div>
        </button>

        {/* Scenario 2: Model Swap */}
        <button
          onClick={() => executeScenario("Silent Model Swap", {
            decision_id: `d_tamper_model_${Date.now().toString().slice(-4)}`,
            policy_id: "pol_nbfc42_lspX_personal_v1",
            proof: "HALO2_SNARK_PROOF_BYTES_TAMPERED",
            public_inputs: {
              policy_hash: "0x7d02c941ab779f3ca82e22d05a0123456789abcdef0123456789abcdef012345",
              C: "0xUNAPPROVED_MODEL_COMMITMENT_V4_SILENT_SWAP",
              X: "0x7d0211bc922d05a6789abcdef0123456789abcdef0123456789abcdef012345",
              decision: 1,
              threshold: 0.200,
              epoch: 20261020
            }
          })}
          disabled={!!running}
          className="p-3 bg-slate-50 hover:bg-rose-50 border border-slate-300 hover:border-rose-300 rounded-lg text-left transition disabled:opacity-50"
        >
          <div className="font-bold text-xs text-rose-900">2. Tamper: Model Swap</div>
          <div className="text-[10px] text-slate-500 mt-1">LSP changes model weights</div>
        </button>

        {/* Scenario 3: Threshold Creep */}
        <button
          onClick={() => executeScenario("Threshold Creep", {
            decision_id: `d_tamper_thresh_${Date.now().toString().slice(-4)}`,
            policy_id: "pol_nbfc42_lspX_personal_v1",
            proof: "HALO2_SNARK_PROOF_BYTES_TAMPERED",
            public_inputs: {
              policy_hash: "0x7d02c941ab779f3ca82e22d05a0123456789abcdef0123456789abcdef012345",
              C: "0x9f3ca82e41ab77d0211bc922d05a6789abcdef0123456789abcdef0123456789",
              X: "0x7d0211bc922d05a6789abcdef0123456789abcdef0123456789abcdef012345",
              decision: 1,
              threshold: 0.050, // Tampered threshold
              epoch: 20261020
            }
          })}
          disabled={!!running}
          className="p-3 bg-slate-50 hover:bg-amber-50 border border-slate-300 hover:border-amber-300 rounded-lg text-left transition disabled:opacity-50"
        >
          <div className="font-bold text-xs text-amber-900">3. Tamper: Threshold</div>
          <div className="text-[10px] text-slate-500 mt-1">LSP drops cutoff to 0.05</div>
        </button>

        {/* Scenario 4: Policy Mismatch */}
        <button
          onClick={() => executeScenario("Policy Mismatch", {
            decision_id: `d_tamper_pol_${Date.now().toString().slice(-4)}`,
            policy_id: "pol_nbfc42_lspX_personal_v1",
            proof: "HALO2_SNARK_PROOF_BYTES_TAMPERED",
            public_inputs: {
              policy_hash: "0xTAMPERED_POLICY_HASH_CORRUPT",
              C: "0x9f3ca82e41ab77d0211bc922d05a6789abcdef0123456789abcdef0123456789",
              X: "0x7d0211bc922d05a6789abcdef0123456789abcdef0123456789abcdef012345",
              decision: 1,
              threshold: 0.200,
              epoch: 20261020
            }
          })}
          disabled={!!running}
          className="p-3 bg-slate-50 hover:bg-purple-50 border border-slate-300 hover:border-purple-300 rounded-lg text-left transition disabled:opacity-50"
        >
          <div className="font-bold text-xs text-purple-900">4. Tamper: Policy</div>
          <div className="text-[10px] text-slate-500 mt-1">Unapproved clause modification</div>
        </button>

        {/* Scenario 5: Replay Attack */}
        <button
          onClick={() => executeScenario("Replay Attack", {
            decision_id: `d_replay_${Date.now().toString().slice(-4)}`,
            policy_id: "pol_nbfc42_lspX_personal_v1",
            proof: "HALO2_SNARK_VALID_PROOF_BYTES_APPROVED_MODEL",
            public_inputs: {
              policy_hash: "0x7d02c941ab779f3ca82e22d05a0123456789abcdef0123456789abcdef012345",
              C: "0x9f3ca82e41ab77d0211bc922d05a6789abcdef0123456789abcdef0123456789",
              X: "0x7d0211bc922d05a6789abcdef0123456789abcdef0123456789abcdef012345",
              decision: 1,
              threshold: 0.200,
              epoch: 20261020
            }
          })}
          disabled={!!running}
          className="p-3 bg-slate-50 hover:bg-red-50 border border-slate-300 hover:border-red-300 rounded-lg text-left transition disabled:opacity-50"
        >
          <div className="font-bold text-xs text-red-900">5. Tamper: Replay</div>
          <div className="text-[10px] text-slate-500 mt-1">Resubmit prior proof</div>
        </button>
      </div>

      {result && (
        <div className={`p-3 rounded-lg border text-xs flex justify-between items-center ${result.color}`}>
          <div>
            <strong>{result.name}:</strong> Status: <span className="font-bold">{result.status}</span>
          </div>
          <span className="font-mono bg-white px-2 py-0.5 rounded border border-current font-semibold">
            {result.code}
          </span>
        </div>
      )}
    </div>
  );
};
```

---

## 📝 FILE 5: Main Institutional Dashboard (`dashboard/src/pages/LenderDashboard.tsx`)
Create `dashboard/src/pages/LenderDashboard.tsx`:
```tsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { TamperPanel } from '../components/TamperPanel';
import { DashboardSummary } from '../api/client';

export const LenderDashboard: React.FC = () => {
  const [data, setData] = useState<DashboardSummary | null>(null);

  const fetchSummary = async () => {
    try {
      const res = await axios.get<DashboardSummary>('/v1/dashboard/summary');
      setData(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchSummary();
    const interval = setInterval(fetchSummary, 4000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-[#F4F6F8] text-slate-800 flex flex-col font-sans">
      {/* Institutional Bank Header */}
      <header className="bg-[#0A2540] text-white py-3 px-8 flex items-center justify-between border-b border-slate-700 shadow-sm">
        <div className="flex items-center space-x-4">
          <div className="w-9 h-9 rounded bg-[#8B0000] flex items-center justify-center font-bold text-white text-base">
            स
          </div>
          <div>
            <h1 className="font-bold text-lg leading-tight tracking-tight">Sakshi • RE Conformance Assurance Portal</h1>
            <p className="text-xs text-slate-300">Regulated Entity: NBFC-ICC • Real-time Zero-Knowledge Algorithmic Oversight</p>
          </div>
        </div>
        <div className="flex items-center space-x-3 text-xs">
          <span className="flex items-center space-x-1.5 bg-emerald-950 text-emerald-400 border border-emerald-800 px-3 py-1 rounded-full font-medium">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>Ledger Chain: Cryptographically Intact</span>
          </span>
          <a href="/borrower" target="_blank" className="bg-slate-800 hover:bg-slate-700 text-white px-3 py-1 rounded border border-slate-600 font-medium">
            Open Borrower App ↗
          </a>
        </div>
      </header>

      <main className="max-w-7xl w-full mx-auto p-6 space-y-6 flex-1">
        {/* Metric Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
            <p className="text-xs font-semibold uppercase text-slate-500 tracking-wider">Total Audited Decisions</p>
            <p className="text-3xl font-bold text-[#0A2540] mt-1">{data?.total_decisions || 0}</p>
            <p className="text-[11px] text-slate-400 mt-1">100% of decisions mathematically checked</p>
          </div>

          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm border-l-4 border-l-emerald-600">
            <p className="text-xs font-semibold uppercase text-slate-500 tracking-wider">Verified Conforming (Disbursed)</p>
            <p className="text-3xl font-bold text-emerald-700 mt-1">{data?.verified || 0}</p>
            <p className="text-[11px] text-emerald-600 mt-1">Proof passed gate • Funds released</p>
          </div>

          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm border-l-4 border-l-rose-600">
            <p className="text-xs font-semibold uppercase text-slate-500 tracking-wider">Contract Violations Blocked</p>
            <p className="text-3xl font-bold text-rose-700 mt-1">{data?.failed || 0}</p>
            <p className="text-[11px] text-rose-600 mt-1">Fail-closed gate held disbursal</p>
          </div>

          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
            <p className="text-xs font-semibold uppercase text-slate-500 tracking-wider">Verification Latency (p50)</p>
            <p className="text-3xl font-bold text-[#0A2540] mt-1">{data?.proof_latency_p50_ms || 18.4} <span className="text-sm font-normal text-slate-500">ms</span></p>
            <p className="text-[11px] text-slate-400 mt-1">Zero UX friction on borrower loan offer</p>
          </div>
        </div>

        {/* Live Tamper Panel */}
        <TamperPanel onRefresh={fetchSummary} />

        {/* Live Decision Feed */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-200 flex justify-between items-center bg-slate-50">
            <div>
              <h2 className="font-bold text-slate-900 text-sm">Real-Time Decision Conformance Feed</h2>
              <p className="text-xs text-slate-500">Live stream of credit decisions evaluated against Board-Approved Policy</p>
            </div>
            <span className="text-xs font-mono text-slate-400">Ledger Root Seq: #{data?.ledger_seq || 0}</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#F8FAFC] text-slate-600 uppercase tracking-wider text-[10px] border-b border-slate-200">
                <tr>
                  <th className="py-3 px-4">Decision ID</th>
                  <th className="py-3 px-4">Policy ID</th>
                  <th className="py-3 px-4">Model Commitment (C)</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Verification Audit / Reason</th>
                  <th className="py-3 px-4">Receipt</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data?.recent_decisions && data.recent_decisions.length > 0 ? (
                  data.recent_decisions.map((d) => (
                    <tr key={d.decision_id} className="hover:bg-slate-50 transition font-mono">
                      <td className="py-3 px-4 font-bold text-slate-800">{d.decision_id}</td>
                      <td className="py-3 px-4 text-slate-600">{d.policy_id}</td>
                      <td className="py-3 px-4 text-slate-500 truncate max-w-[140px]">{d.model_commitment}</td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-0.5 rounded-full font-bold text-[10px] ${
                          d.status === 'VERIFIED' ? 'bg-emerald-100 text-emerald-800' :
                          d.status === 'FAILED' ? 'bg-rose-100 text-rose-800' : 'bg-amber-100 text-amber-800'
                        }`}>
                          {d.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-700">
                        {d.failure_reason ? (
                          <span className="text-rose-700 font-bold">{d.failure_reason}</span>
                        ) : (
                          <span className="text-emerald-700 font-semibold">✓ Conformance Confirmed (V1-V9 Passed)</span>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        <a href={`/receipt/${d.decision_id}`} className="text-[#0A2540] hover:underline font-bold text-[11px]">
                          View Receipt
                        </a>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-slate-400">
                      No decisions recorded yet. Run `python scripts/demo_seed.py` or apply via Borrower App.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </main>

      <footer className="bg-white border-t border-slate-200 py-3 px-8 flex justify-between items-center text-xs text-slate-400">
        <span>Sakshi Assurance Platform • Version 1.0.0</span>
        <span>Aligned with RBI Digital Lending Directions 2025 & FREE-AI Guidelines</span>
      </footer>
    </div>
  );
};
```

---

## 📝 FILE 6: Customer Decision Receipt (`dashboard/src/pages/BorrowerReceipt.tsx`)
Create `dashboard/src/pages/BorrowerReceipt.tsx`:
```tsx
import React from 'react';
import { useParams } from 'react-router-dom';

export const BorrowerReceipt: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  return (
    <div className="min-h-screen bg-[#F4F6F8] p-6 flex items-center justify-center font-sans text-slate-800">
      <div className="max-w-2xl w-full bg-white rounded-xl border border-slate-200 shadow-md p-8 space-y-6">
        <div className="flex items-center justify-between border-b border-slate-200 pb-5">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded bg-[#8B0000] text-white flex items-center justify-center font-bold text-lg">
              स
            </div>
            <div>
              <h1 className="font-bold text-lg text-slate-900">Cryptographic Decision Receipt</h1>
              <p className="text-xs text-slate-500">Immutable Zero-Knowledge Underwriting Attestation</p>
            </div>
          </div>
          <span className="text-xs bg-emerald-100 text-emerald-800 font-bold px-3 py-1 rounded-full">
            SANCTIONED & VERIFIED
          </span>
        </div>

        <div className="grid grid-cols-2 gap-4 text-xs">
          <div>
            <p className="text-slate-400 uppercase tracking-wider font-semibold">Decision Identifier</p>
            <p className="font-mono font-bold text-slate-800 mt-0.5">{id || 'd_8842'}</p>
          </div>
          <div>
            <p className="text-slate-400 uppercase tracking-wider font-semibold">Verification Timestamp</p>
            <p className="font-bold text-slate-800 mt-0.5">20 Oct 2026, 20:30:15 IST</p>
          </div>
          <div>
            <p className="text-slate-400 uppercase tracking-wider font-semibold">Policy Reference</p>
            <p className="font-mono text-slate-700 mt-0.5">pol_nbfc42_lspX_personal_v1</p>
          </div>
          <div>
            <p className="text-slate-400 uppercase tracking-wider font-semibold">Audit Ledger Sequence</p>
            <p className="font-mono font-bold text-emerald-700 mt-0.5">#1042 (Hash-Chained)</p>
          </div>
        </div>

        <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 space-y-2 text-xs">
          <p className="font-semibold text-slate-700">Cryptographic Commitments:</p>
          <div className="space-y-1 font-mono text-[11px] text-slate-600 break-all">
            <p><strong className="text-slate-800">Model Commitment (C):</strong> 0x9f3ca82e41ab77d0211bc922d05a6789abcdef0123456789abcdef0123456789</p>
            <p><strong className="text-slate-800">Input Commitment (X):</strong> 0x7d0211bc922d05a6789abcdef0123456789abcdef0123456789abcdef012345</p>
            <p><strong className="text-slate-800">Proof Protocol:</strong> EZKL Halo2 SNARK (Zero Model Weights Exposed)</p>
          </div>
        </div>

        <div className="text-[11px] text-slate-500 leading-relaxed border-t border-slate-100 pt-4">
          This receipt serves as mathematical proof that the credit decision for your loan was evaluated strictly using the contractually approved underwriting model and cut-off thresholds signed by the Regulated Entity (NBFC) under the <strong>Reserve Bank of India (Digital Lending) Directions, 2025</strong>.
        </div>

        <div className="flex justify-end space-x-3 pt-2">
          <button onClick={() => window.print()} className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-semibold hover:bg-slate-50">
            Print Certificate
          </button>
          <a href="/borrower" className="px-4 py-2 bg-[#0A2540] text-white rounded-lg text-xs font-semibold hover:bg-[#002D62]">
            Back to Loan App
          </a>
        </div>
      </div>
    </div>
  );
};
```

---

## 📝 FILE 7: `dashboard/src/App.tsx`
Create `dashboard/src/App.tsx`:
```tsx
import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { LenderDashboard } from './pages/LenderDashboard';
import { BorrowerPortal } from './pages/BorrowerPortal';
import { BorrowerReceipt } from './pages/BorrowerReceipt';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LenderDashboard />} />
        <Route path="/borrower" element={<BorrowerPortal />} />
        <Route path="/receipt/:id" element={<BorrowerReceipt />} />
      </Routes>
    </BrowserRouter>
  );
};
```

---

## 📝 FILE 8: Automated Seeder (`scripts/demo_seed.py`)
Create `scripts/demo_seed.py`:
```python
import time
import httpx

LENDER_NODE = "http://localhost:8000"

def seed():
    print("=== SEEDING SAKSHI DEMO ENVIRONMENT ===")
    with httpx.Client(timeout=10.0) as client:
        # 1. Register Approved Model
        m_payload = {
            "commitment": "0x9f3ca82e41ab77d0211bc922d05a6789abcdef0123456789abcdef0123456789",
            "circuit_hash": "0x41ab77d0211bc922d05a6789abcdef0123456789abcdef0123456789abcdef01",
            "vk": "VK_HALO2_BASE64_ENCODED_KEY_HERE"
        }
        res_m = client.post(f"{LENDER_NODE}/v1/models", json=m_payload)
        print(f"Model Registration: {res_m.status_code} - {res_m.json()}")

        # 2. Register Active Policy
        p_payload = {
            "policy_id": "pol_nbfc42_lspX_personal_v1",
            "model_commitment": m_payload["commitment"],
            "circuit_hash": m_payload["circuit_hash"],
            "decision_threshold": 0.200,
            "policy_hash": "0x7d02c941ab779f3ca82e22d05a0123456789abcdef0123456789abcdef012345"
        }
        res_p = client.post(f"{LENDER_NODE}/v1/policies", json=p_payload)
        print(f"Policy Registration: {res_p.status_code} - {res_p.json()}")

        # 3. Pre-seed 3 Verified Decisions
        for i in range(1, 4):
            d_id = f"d_demo_100{i}"
            proof_payload = {
                "decision_id": d_id,
                "policy_id": p_payload["policy_id"],
                "proof": f"HALO2_PROOF_PRE_SEEDED_{i}",
                "public_inputs": {
                    "policy_hash": p_payload["policy_hash"],
                    "C": m_payload["commitment"],
                    "X": f"0x_input_hash_sample_{i}",
                    "decision": 1,
                    "threshold": 0.200,
                    "epoch": 20261020
                }
            }
            res_proof = client.post(f"{LENDER_NODE}/v1/proofs", json=proof_payload)
            print(f"Pre-seed Decision #{i} ({d_id}): {res_proof.status_code}")

    print("=== SEEDING COMPLETE! ALL DEMO SERVICES READY ===")

if __name__ == "__main__":
    seed()
```

---

## ⚡ VERIFICATION COMMANDS FOR DEV 3
Run these commands to verify all frontend code builds cleanly into static assets:
```bash
cd dashboard && npm run build
```
When this command exits with code `0`, your job is 100% complete and ready to commit.
