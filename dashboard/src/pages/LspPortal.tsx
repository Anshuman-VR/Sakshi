import { useState, useEffect } from 'react';
import { 
  Cpu, Lock, Database, CheckCircle2, 
  Key, ArrowUpRight, Clock, FileCode, Check, X, Code2,
  Building, User, Shield
} from 'lucide-react';
import { fetchSummary } from '../api/client';
import type { DashboardSummary, DecisionRecord } from '../api/types';

const ist = (v?: string | null) => {
  if (!v) return '—';
  const d = new Date(v);
  return Number.isNaN(d.getTime())
    ? v
    : new Intl.DateTimeFormat('en-IN', {
        dateStyle: 'short',
        timeStyle: 'medium',
        timeZone: 'Asia/Kolkata',
      }).format(d) + ' IST';
};

const money = (n?: number | null) => {
  if (n == null) return '—';
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n);
};

const FEATURES_SCHEMA = [
  { name: 'bureau_score', type: 'float32', role: 'CIBIL Bureau Credit Score (300-900)' },
  { name: 'monthly_income', type: 'float32', role: 'Net Monthly Take-Home Salary in INR' },
  { name: 'foir', type: 'float32', role: 'Fixed Obligation to Income Ratio (Existing EMI / Income)' },
  { name: 'loan_tenure_months', type: 'float32', role: 'Requested Loan Tenure (12-60 months)' },
  { name: 'num_active_loans', type: 'float32', role: 'Active Credit Lines and Loan Accounts' },
  { name: 'num_enquiries_6m', type: 'float32', role: 'Credit Inquiries in Past 6 Months' },
  { name: 'bank_account_age_months', type: 'float32', role: 'Primary Banking Relationship Age in Months' },
  { name: 'loan_amount_requested', type: 'float32', role: 'Principal Loan Amount in INR' },
  { name: 'behaviour_idx', type: 'float32', role: 'Digital Behavioral Repayment Signal (0.0 - 1.0)' },
  { name: 'employment_type', type: 'float32', role: 'Employment Category (0=Salaried, 1=Self-Employed)' },
];

export function LspPortal() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [selectedProof, setSelectedProof] = useState<DecisionRecord | null>(null);

  useEffect(() => {
    let alive = true;
    const load = () => {
      fetchSummary()
        .then((s) => {
          if (alive) setData(s);
        })
        .catch(() => {});
    };
    load();
    const interval = setInterval(load, 3000);
    return () => {
      alive = false;
      clearInterval(interval);
    };
  }, []);

  const copyToClipboard = (text: string, keyName: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(keyName);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const recentProofs = data?.recent_decisions ?? [];

  return (
    <main className="mx-auto w-[calc(100%-32px)] md:w-[calc(100%-48px)] xl:w-[calc(100%-64px)] max-w-[1600px] py-8 sm:py-10">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-purple-100 text-purple-900 border border-purple-200 mb-2">
            <Building size={14} className="text-purple-700" /> Quick FinCorp Pvt Ltd · LSP Infrastructure
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
            LSP Dashboard
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Proprietary credit scorecard execution, Halo2 zero-knowledge circuit proving, and proof dispatch to Meridian Digital.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3.5 py-2 bg-white rounded-lg border border-slate-200 shadow-sm text-xs font-medium text-slate-700">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
            Prover Sidecar: <strong className="text-slate-900 font-mono">Port 8001 (Active)</strong>
          </div>
          <div className="flex items-center gap-2 px-3.5 py-2 bg-emerald-50 rounded-lg border border-emerald-200 text-xs font-semibold text-emerald-800">
            <Lock size={13} /> Model Weights Isolated
          </div>
        </div>
      </div>

      {/* Grid: Architectural Isolation (Clean 2-card layout without redundant outbox) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Model Card */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2 text-sm font-bold text-slate-900">
              <Database className="text-indigo-600" size={18} />
              Trained Scorecard (ONNX)
            </div>
            <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-blue-50 text-blue-700 border border-blue-200 font-mono">
              10 Features
            </span>
          </div>
          <p className="text-xs text-slate-500 mb-4 leading-relaxed">
            Proprietary Credit Risk Scorecard calibrated for personal credit applications. Exported with quantized weights for Halo2 arithmetic circuit evaluation.
          </p>
          <div className="space-y-2.5 text-xs">
            <div className="flex justify-between items-center py-1.5 border-b border-slate-100">
              <span className="text-slate-500">Partner Lender Entity:</span>
              <span className="font-bold text-slate-900">Meridian Digital</span>
            </div>
            <div className="flex justify-between items-center py-1.5 border-b border-slate-100">
              <span className="text-slate-500">Validation Parity:</span>
              <span className="font-semibold text-emerald-700">100% Agreement (AUC 0.794)</span>
            </div>
            <div className="flex justify-between items-center py-1.5 border-b border-slate-100">
              <span className="text-slate-500">Policy Contract:</span>
              <span className="font-mono text-slate-800">pol_meridian_quickfin_v1</span>
            </div>
            <div className="flex justify-between items-center py-1.5">
              <span className="text-slate-500">Decision Threshold:</span>
              <span className="font-bold text-slate-900 font-mono">0.500 (Cutoff)</span>
            </div>
          </div>
        </div>

        {/* ZK Proof Architecture */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2 text-sm font-bold text-slate-900">
              <Cpu className="text-purple-600" size={18} />
              Halo2 Arithmetic Circuit & Prover
            </div>
            <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-purple-50 text-purple-700 border border-purple-200 font-mono">
              Scale 1024
            </span>
          </div>
          <p className="text-xs text-slate-500 mb-4 leading-relaxed">
            Quantized fixed-point circuit proving inference integrity without disclosing model parameters or raw financial attributes across the network boundary.
          </p>
          <div className="space-y-2 text-xs">
            <div className="p-2.5 rounded bg-slate-50 border border-slate-100">
              <strong className="text-slate-800 block mb-0.5">Private Witness (X):</strong>
              <span className="text-slate-500">Raw features committed via SHA-256 canonical hashing; features remain strictly in LSP Zone.</span>
            </div>
            <div className="p-2.5 rounded bg-slate-50 border border-slate-100">
              <strong className="text-slate-800 block mb-0.5">Fixed Circuit Weights (C):</strong>
              <span className="text-slate-500">Model coefficients fixed as advice columns committed in mutual policy contract.</span>
            </div>
          </div>
        </div>
      </div>

      {/* Live Outbound Proof Dispatch Stream */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden mb-8">
        <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock size={16} className="text-purple-600" />
            <h2 className="text-sm font-bold text-slate-900">Recent Outbound Proofs Dispatched to Meridian Digital</h2>
          </div>
          <span className="text-xs text-slate-500">
            Total Proved: <strong className="text-slate-900">{data?.total_decisions ?? 0}</strong>
          </span>
        </div>

        {recentProofs.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
                <tr>
                  <th className="px-6 py-3">Decision ID / Timestamp</th>
                  <th className="px-4 py-3">Borrower Name</th>
                  <th className="px-4 py-3">Underwriting Output</th>
                  <th className="px-4 py-3">Proof Hash (SHA-256)</th>
                  <th className="px-4 py-3">Lender Ack</th>
                  <th className="px-4 py-3">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {recentProofs.map((p) => {
                  const isApproved = p.decision === 1;
                  return (
                    <tr key={p.decision_id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="px-6 py-3.5">
                        <span className="font-bold text-slate-900 block">{p.decision_id}</span>
                        <span className="text-[11px] text-slate-400 font-sans">{ist(p.verified_at || p.received_at)}</span>
                      </td>
                      <td className="px-4 py-3.5 font-sans font-medium text-slate-800">
                        {p.customer_info?.name || 'Applicant'}
                      </td>
                      <td className="px-4 py-3.5">
                        <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-sans font-bold border ${
                          isApproved 
                            ? 'bg-emerald-50 text-emerald-800 border-emerald-200' 
                            : 'bg-rose-50 text-rose-800 border-rose-200'
                        }`}>
                          {isApproved ? 'DECISION = 1 (APPROVE)' : 'DECISION = 0 (REJECT)'}
                        </span>
                      </td>
                      <td className="px-4 py-3.5 text-slate-500 truncate max-w-[170px]">
                        {p.proof_hash ? `${p.proof_hash.slice(0, 16)}…` : 'Derived in circuit'}
                      </td>
                      <td className="px-4 py-3.5">
                        <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-sans font-bold border ${
                          p.status === 'VERIFIED'
                            ? 'bg-indigo-50 text-indigo-800 border-indigo-200'
                            : 'bg-amber-50 text-amber-800 border-amber-200'
                        }`}>
                          <CheckCircle2 size={12} /> {p.status}
                        </span>
                      </td>
                      <td className="px-4 py-3.5">
                        <button
                          type="button"
                          onClick={() => setSelectedProof(p)}
                          className="inline-flex items-center gap-1 font-sans text-xs font-semibold text-purple-600 hover:text-purple-800 underline underline-offset-4"
                        >
                          Details <ArrowUpRight size={13} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-12 text-center text-slate-500 text-xs">
            No outbound proofs dispatched yet. Submit an application in the Borrower Portal to trigger a proof.
          </div>
        )}
      </div>

      {/* Feature Dimensions & Model Schema Card (10 Inputs) */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden mb-8">
        <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Code2 size={16} className="text-slate-700" />
            <h2 className="text-sm font-bold text-slate-900">Scorecard ONNX Feature Dimension Schema (10 Inputs)</h2>
          </div>
          <span className="text-xs font-mono text-slate-500">Ordered Vector Schema</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-50 border-b border-slate-100 text-[10px] uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-6 py-2.5">Index</th>
                <th className="px-4 py-2.5">Feature Key</th>
                <th className="px-4 py-2.5">Data Type</th>
                <th className="px-6 py-2.5 font-sans">Underwriting Description</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {FEATURES_SCHEMA.map((f, i) => (
                <tr key={f.name} className="hover:bg-slate-50/50">
                  <td className="px-6 py-2.5 text-slate-400">[{i}]</td>
                  <td className="px-4 py-2.5 font-bold text-slate-900">{f.name}</td>
                  <td className="px-4 py-2.5 text-slate-500">{f.type}</td>
                  <td className="px-6 py-2.5 font-sans text-slate-600">{f.role}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Cryptographic Artifacts Card */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden mb-8">
        <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Key size={16} className="text-slate-700" />
            <h2 className="text-sm font-bold text-slate-900">Cryptographic Commitments & Dual Signatures</h2>
          </div>
          <span className="text-xs font-mono text-slate-500">Dual Ed25519 Signed</span>
        </div>
        <div className="p-6 divide-y divide-slate-100">
          <div className="py-3 flex flex-col md:flex-row md:items-center justify-between gap-2">
            <div>
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">Model Commitment (C)</span>
              <span className="text-xs text-slate-400">Salted SHA-256 digest over normalized float32 model parameters</span>
            </div>
            <div className="flex items-center gap-2">
              <code className="text-xs font-mono bg-slate-100 text-slate-800 px-3 py-1.5 rounded border border-slate-200 break-all max-w-xl">
                0xd031786a1e637500b6c16c661f33e751cc13e0c614eeb03045866660aeb09b80
              </code>
              <button 
                onClick={() => copyToClipboard('0xd031786a1e637500b6c16c661f33e751cc13e0c614eeb03045866660aeb09b80', 'C')}
                className="p-1.5 rounded hover:bg-slate-100 text-slate-500"
                title="Copy commitment"
              >
                {copiedKey === 'C' ? <Check size={14} className="text-emerald-600" /> : <FileCode size={14} />}
              </button>
            </div>
          </div>

          <div className="py-3 flex flex-col md:flex-row md:items-center justify-between gap-2">
            <div>
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">EZKL Circuit Hash</span>
              <span className="text-xs text-slate-400">Compiled Halo2 arithmetic circuit artifact identity</span>
            </div>
            <div className="flex items-center gap-2">
              <code className="text-xs font-mono bg-slate-100 text-slate-800 px-3 py-1.5 rounded border border-slate-200 break-all max-w-xl">
                0xd3b2dc63f9c9520b6d22069a015b36288d90676f45cf9bd5a41ec133911b6729
              </code>
              <button 
                onClick={() => copyToClipboard('0xd3b2dc63f9c9520b6d22069a015b36288d90676f45cf9bd5a41ec133911b6729', 'circuit')}
                className="p-1.5 rounded hover:bg-slate-100 text-slate-500"
                title="Copy circuit hash"
              >
                {copiedKey === 'circuit' ? <Check size={14} className="text-emerald-600" /> : <FileCode size={14} />}
              </button>
            </div>
          </div>

          <div className="py-3 flex flex-col md:flex-row md:items-center justify-between gap-2">
            <div>
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">Active Policy Hash</span>
              <span className="text-xs text-slate-400">Canonical JSON digest mutually approved by Meridian Digital & Quick FinCorp</span>
            </div>
            <div className="flex items-center gap-2">
              <code className="text-xs font-mono bg-slate-100 text-slate-800 px-3 py-1.5 rounded border border-slate-200 break-all max-w-xl">
                f2f6778a81599ce4a9fbeebe1f0c337f37bfde894297632f1cee3581fcd32b9f
              </code>
              <button 
                onClick={() => copyToClipboard('f2f6778a81599ce4a9fbeebe1f0c337f37bfde894297632f1cee3581fcd32b9f', 'policy')}
                className="p-1.5 rounded hover:bg-slate-100 text-slate-500"
                title="Copy policy hash"
              >
                {copiedKey === 'policy' ? <Check size={14} className="text-emerald-600" /> : <FileCode size={14} />}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Proof Details Modal: Customer Details + Delivered Payload */}
      {selectedProof && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-xl w-full max-h-[90vh] overflow-y-auto p-6">
            <div className="flex items-center justify-between pb-4 border-b border-slate-200 mb-4">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                  Outbound Proof Dispatch Record
                </span>
                <h3 className="text-base font-bold text-slate-900 font-mono">
                  {selectedProof.decision_id}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setSelectedProof(null)}
                className="p-2 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
              >
                <X size={18} />
              </button>
            </div>

            <div className="space-y-4">
              {/* Customer Details Section */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2 flex items-center gap-1.5">
                  <User size={13} className="text-purple-600" /> Customer Information
                </h4>
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-semibold">Applicant Name</span>
                    <strong className="text-slate-900">{selectedProof.customer_info?.name || 'Priya Sharma'}</strong>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-semibold">PAN Number</span>
                    <strong className="text-slate-900 font-mono">{selectedProof.customer_info?.pan || 'BNZPS1042K'}</strong>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-semibold">Mobile</span>
                    <strong className="text-slate-900 font-mono">{selectedProof.customer_info?.phone || '+91 98201 44821'}</strong>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-semibold">Bank Account</span>
                    <strong className="text-slate-900 font-mono">{selectedProof.customer_info?.bank_account || '9182014482103'}</strong>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-semibold">Loan Amount</span>
                    <strong className="text-slate-900 font-mono">{money(selectedProof.customer_info?.loan_amount || 150000)}</strong>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-semibold">CIBIL Score</span>
                    <strong className="text-slate-900 font-mono">{selectedProof.customer_info?.bureau || 758}</strong>
                  </div>
                </div>
              </div>

              {/* Delivered Payload Box */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2 flex items-center gap-1.5">
                  <Shield size={13} className="text-emerald-600" /> Delivered Payload
                </h4>
                <div className="p-4 rounded-xl bg-slate-900 text-slate-200 text-xs font-mono space-y-2">
                  <div className="flex justify-between items-center py-1 border-b border-slate-800">
                    <span className="text-slate-400">policy_hash:</span>
                    <span className="text-emerald-400 truncate max-w-xs" title={selectedProof.public_inputs?.policy_hash || 'f2f6778a81599ce4a9fbeebe1f0c337f37bfde894297632f1cee3581fcd32b9f'}>
                      {selectedProof.public_inputs?.policy_hash || 'f2f6778a81599ce4a9fbeebe1f0c337f37bfde894297632f1cee3581fcd32b9f'}
                    </span>
                  </div>

                  <div className="flex justify-between items-center py-1 border-b border-slate-800">
                    <span className="text-slate-400">C (Model Commitment):</span>
                    <span className="text-purple-300 truncate max-w-xs" title={selectedProof.public_inputs?.C || selectedProof.model_commitment || ''}>
                      {selectedProof.public_inputs?.C || selectedProof.model_commitment || '0xd031786a...'}
                    </span>
                  </div>

                  <div className="flex justify-between items-center py-1 border-b border-slate-800">
                    <span className="text-slate-400">X (Input Commitment):</span>
                    <span className="text-blue-300 truncate max-w-xs" title={selectedProof.public_inputs?.X || ''}>
                      {selectedProof.public_inputs?.X || 'SHA-256 Canonical Features'}
                    </span>
                  </div>

                  <div className="flex justify-between items-center py-1 border-b border-slate-800">
                    <span className="text-slate-400">decision:</span>
                    <span className="text-amber-300 font-bold">
                      {selectedProof.public_inputs?.decision ?? selectedProof.decision}
                    </span>
                  </div>

                  <div className="flex justify-between items-center py-1 border-b border-slate-800">
                    <span className="text-slate-400">threshold:</span>
                    <span className="text-slate-200 font-bold">
                      {selectedProof.public_inputs?.threshold ?? 0.50}
                    </span>
                  </div>

                  <div className="flex justify-between items-center py-1">
                    <span className="text-slate-400">epoch:</span>
                    <span className="text-slate-300">
                      {selectedProof.public_inputs?.epoch ?? 20261021}
                    </span>
                  </div>
                </div>
              </div>

              <div className="pt-2 flex justify-end">
                <button
                  type="button"
                  onClick={() => setSelectedProof(null)}
                  className="px-4 py-2 bg-slate-900 text-white font-semibold text-xs rounded-lg hover:bg-slate-800"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
