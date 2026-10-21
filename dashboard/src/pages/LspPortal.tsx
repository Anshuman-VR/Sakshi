import { useState, useEffect } from 'react';
import { 
  Cpu, Lock, Database, CheckCircle2, 
  Key, Server, ArrowUpRight, Clock, FileCode, Check, X, Code2
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

const FEATURES_SCHEMA = [
  { name: 'bureau_score', type: 'float32', role: 'CIBIL Bureau Credit Score (300-900)' },
  { name: 'monthly_income', type: 'float32', role: 'Net Monthly Take-Home Salary in INR' },
  { name: 'foir', type: 'float32', role: 'Fixed Obligation to Income Ratio (0.0-1.0)' },
  { name: 'loan_tenure_months', type: 'float32', role: 'Requested Loan Tenure (12-60 months)' },
  { name: 'num_active_loans', type: 'float32', role: 'Current Active Credit Lines' },
  { name: 'num_enquiries_6m', type: 'float32', role: 'Hard Credit Enquiries in Past 6 Months' },
  { name: 'bank_account_age_months', type: 'float32', role: 'Primary Banking Relationship Age' },
  { name: 'loan_amount_requested', type: 'float32', role: 'Principal Loan Amount in INR' },
  { name: 'behaviour_idx', type: 'float32', role: 'Digital Behavioral Repayment Signal' },
  { name: 'employment_type', type: 'float32', role: 'Employment Category (0=Salaried, 1=Self)' },
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
            <Cpu size={14} className="text-purple-700" /> Zone 1: Private LSP Infrastructure
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
            LSP Prover & Underwriting Engine
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Proprietary credit scoring model execution, EZKL Halo2 circuit compilation, and zero-knowledge proof dispatch.
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

      {/* Grid: Architectural Isolation */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
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
            Calibrated Credit Risk Model trained on LendingClub credit portfolio (9,578 records). Exported with MatMul, Add, and Sigmoid operators.
          </p>
          <div className="space-y-2.5 text-xs">
            <div className="flex justify-between items-center py-1.5 border-b border-slate-100">
              <span className="text-slate-500">Validation Parity</span>
              <span className="font-semibold text-emerald-700">100% (AUC 0.794)</span>
            </div>
            <div className="flex justify-between items-center py-1.5 border-b border-slate-100">
              <span className="text-slate-500">Quantization Loss</span>
              <span className="font-mono text-slate-800">&lt; 3.3e-07</span>
            </div>
            <div className="flex justify-between items-center py-1.5">
              <span className="text-slate-500">Decision Threshold</span>
              <span className="font-bold text-slate-900 font-mono">0.200 (Cutoff)</span>
            </div>
          </div>
        </div>

        {/* ZK Proof Architecture */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2 text-sm font-bold text-slate-900">
              <Cpu className="text-purple-600" size={18} />
              Halo2 Arithmetic Circuit
            </div>
            <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-purple-50 text-purple-700 border border-purple-200 font-mono">
              Scale 1024
            </span>
          </div>
          <p className="text-xs text-slate-500 mb-4 leading-relaxed">
            Quantized fixed-point Halo2 circuit proving model inference integrity. Zero model parameters or borrower witness leaked across boundary.
          </p>
          <div className="space-y-2 text-xs">
            <div className="p-2.5 rounded bg-slate-50 border border-slate-100">
              <strong className="text-slate-800 block mb-0.5">Private Witness (X):</strong>
              <span className="text-slate-500">Raw financial features committed via SHA-256 canonical hashing.</span>
            </div>
            <div className="p-2.5 rounded bg-slate-50 border border-slate-100">
              <strong className="text-slate-800 block mb-0.5">Fixed Circuit Weights (C):</strong>
              <span className="text-slate-500">Model coefficients fixed as circuit advice columns.</span>
            </div>
          </div>
        </div>

        {/* Outbox & Transport */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2 text-sm font-bold text-slate-900">
              <Server className="text-emerald-600" size={18} />
              Transactional Outbox
            </div>
            <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 font-mono">
              At-Least-Once
            </span>
          </div>
          <p className="text-xs text-slate-500 mb-4 leading-relaxed">
            Guarantees proof dispatch even under network partitions. Outbox worker retries with exponential backoff.
          </p>
          <div className="space-y-2.5 text-xs">
            <div className="flex justify-between items-center py-1.5 border-b border-slate-100">
              <span className="text-slate-500">Notice SLA Window</span>
              <span className="font-semibold text-slate-900">10 Minutes</span>
            </div>
            <div className="flex justify-between items-center py-1.5 border-b border-slate-100">
              <span className="text-slate-500">Outbox Storage</span>
              <span className="font-mono text-slate-800">SQLite (WAL Mode)</span>
            </div>
            <div className="flex justify-between items-center py-1.5">
              <span className="text-slate-500">Lender Transport</span>
              <span className="font-semibold text-emerald-700">Authenticated (X-Sakshi-Key)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Live Outbound Proof Dispatch Stream */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden mb-8">
        <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock size={16} className="text-purple-600" />
            <h2 className="text-sm font-bold text-slate-900">Recent Outbound Proofs Dispatched to Lender Node</h2>
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
                  <th className="px-4 py-3">Underwriting Output</th>
                  <th className="px-4 py-3">Proof Hash (SHA-256)</th>
                  <th className="px-4 py-3">Lender Ack</th>
                  <th className="px-4 py-3">Proof Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {recentProofs.map((p) => {
                  const isApproved = p.decision === 1;
                  return (
                    <tr key={p.decision_id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="px-6 py-3.5">
                        <span className="font-bold text-slate-900 block">{p.decision_id}</span>
                        <span className="text-[11px] text-slate-400 font-sans">{ist(p.verified_at)}</span>
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
                      <td className="px-4 py-3.5 text-slate-500 truncate max-w-[180px]">
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
                          View Payload <ArrowUpRight size={13} />
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

      {/* Feature Dimensions & Model Schema Card */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden mb-8">
        <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Code2 size={16} className="text-slate-700" />
            <h2 className="text-sm font-bold text-slate-900">Scorecard ONNX Feature Dimension Schema (10 Inputs)</h2>
          </div>
          <span className="text-xs font-mono text-slate-500">Fixed Column Ordering</span>
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
              <span className="text-xs text-slate-400">Canonical JSON digest mutually approved by NBFC-42 Capital & LSP-X</span>
            </div>
            <div className="flex items-center gap-2">
              <code className="text-xs font-mono bg-slate-100 text-slate-800 px-3 py-1.5 rounded border border-slate-200 break-all max-w-xl">
                447930887ea48c1d40442e0a7c3ba681d9168e663df2d9920ddb814cfb5cbf47
              </code>
              <button 
                onClick={() => copyToClipboard('447930887ea48c1d40442e0a7c3ba681d9168e663df2d9920ddb814cfb5cbf47', 'policy')}
                className="p-1.5 rounded hover:bg-slate-100 text-slate-500"
                title="Copy policy hash"
              >
                {copiedKey === 'policy' ? <Check size={14} className="text-emerald-600" /> : <FileCode size={14} />}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Proof Payload Inspection Modal */}
      {selectedProof && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-xl w-full p-6">
            <div className="flex items-center justify-between pb-4 border-b border-slate-200 mb-4">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                  Outbound Proof Payload
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

            <div className="space-y-4 text-xs font-mono">
              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
                <span className="text-slate-400 block text-[10px] uppercase">SHA-256 Proof Digest</span>
                <span className="text-slate-900 break-all">{selectedProof.proof_hash || 'Calculated via witness polynomial'}</span>
              </div>

              {selectedProof.public_inputs && (
                <div className="p-3 rounded-lg bg-slate-900 text-slate-200">
                  <span className="text-[10px] uppercase text-slate-400 block mb-1">Public Inputs Transmitted:</span>
                  <pre className="text-[11px] text-slate-300 leading-relaxed overflow-x-auto">
                    {JSON.stringify(selectedProof.public_inputs, null, 2)}
                  </pre>
                </div>
              )}

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
