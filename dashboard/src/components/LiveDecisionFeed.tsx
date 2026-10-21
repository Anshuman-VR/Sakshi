import { useState } from 'react';
import { 
  ArrowUpRight, Clock3, RefreshCw, CheckCircle2, XCircle, 
  ShieldCheck, ShieldAlert, Copy, Check, X, FileText
} from 'lucide-react';
import type { DecisionRecord } from '../api/types';
import { InfoTip } from './InfoTip';

const ist = (value?: string | null) => {
  if (!value) return '—';
  const d = new Date(value);
  return Number.isNaN(d.getTime())
    ? value
    : new Intl.DateTimeFormat('en-IN', {
        dateStyle: 'medium',
        timeStyle: 'short',
        timeZone: 'Asia/Kolkata',
      }).format(d) + ' IST';
};

const money = (n?: number | null) => {
  if (n == null) return '—';
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n);
};

export function LiveDecisionFeed({
  decisions,
  loading,
  onRefresh,
  lastUpdated,
}: {
  decisions: DecisionRecord[];
  loading: boolean;
  onRefresh: () => void;
  lastUpdated: string;
}) {
  const [selectedRecord, setSelectedRecord] = useState<DecisionRecord | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const handleCopy = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(label);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  return (
    <div className="bg-white rounded-xl border-2 border-slate-300 shadow-sm min-w-0 overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b-2 border-slate-200 px-6 py-4 bg-slate-100">
        <div>
          <span className="font-mono text-[10px] uppercase tracking-wider text-slate-600 font-extrabold block">
            Partner Underwriting Stream
          </span>
          <h2 className="text-xl font-black text-slate-950 tracking-tight">
            Incoming Loan Decisions & Verifications
          </h2>
        </div>
        <button
          onClick={onRefresh}
          className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-bold text-slate-800 bg-white border border-slate-300 rounded-lg shadow-2xs hover:bg-slate-50 hover:text-slate-950 transition-colors"
        >
          <RefreshCw size={13} className={loading ? 'animate-spin text-indigo-600' : ''} />
          Refresh
        </button>
      </div>

      {decisions.length ? (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[850px] text-left text-sm">
            <thead className="bg-slate-100 text-[10px] uppercase tracking-wider text-slate-700 border-b-2 border-slate-300 font-black">
              <tr>
                <th className="px-6 py-3.5">Decision ID / Timestamp</th>
                <th className="px-4 py-3.5">Borrower / PAN</th>
                <th className="px-4 py-3.5">Credit Decision</th>
                <th className="px-4 py-3.5">Disbursal Gate</th>
                <th className="px-4 py-3.5">
                  Policy{' '}
                  <InfoTip
                    label="Policy reference"
                    text="Dual-signed policy contract governing this underwriting model and cutoff threshold."
                  />
                </th>
                <th className="px-4 py-3.5">
                  Model Commitment (C){' '}
                  <InfoTip
                    label="Model commitment"
                    text="Salted cryptographic SHA-256 commitment of the approved ML model parameters."
                  />
                </th>
                <th className="px-4 py-3.5">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 bg-white">
              {decisions.map((d) => {
                const isApproved = d.decision === 1;
                const isVerified = d.status === 'VERIFIED';
                const customer = d.customer_info;
                return (
                  <tr key={d.decision_id} className="hover:bg-slate-100 transition-colors">
                    <td className="px-6 py-4">
                      <div className="font-mono text-xs font-black text-slate-950">{d.decision_id}</div>
                      <div className="mt-0.5 text-[11px] text-slate-600 font-medium">{ist(d.verified_at || d.received_at)}</div>
                    </td>
                    <td className="px-4 py-4">
                      <div className="text-xs font-extrabold text-slate-950">{customer?.name || 'Applicant'}</div>
                      <div className="font-mono text-[11px] text-slate-600 font-bold uppercase">{customer?.pan || '—'}</div>
                    </td>
                    <td className="px-4 py-4">
                      {d.decision !== undefined && d.decision !== null ? (
                        <span
                          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black border ${
                            isApproved
                              ? 'bg-emerald-100 text-emerald-950 border-emerald-300'
                              : 'bg-rose-100 text-rose-950 border-rose-300'
                          }`}
                        >
                          {isApproved ? <CheckCircle2 size={13} /> : <XCircle size={13} />}
                          {isApproved ? 'APPROVED' : 'REJECTED'}
                        </span>
                      ) : (
                        <span className="text-xs text-slate-400 font-mono">—</span>
                      )}
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex items-center gap-1.5">
                        {isVerified && isApproved ? (
                          <span className="inline-flex items-center gap-1 text-xs font-black text-emerald-950 bg-emerald-100 px-2.5 py-0.5 rounded border border-emerald-300">
                            <ShieldCheck size={14} className="text-emerald-700" /> AUTHORIZED
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-xs font-black text-rose-950 bg-rose-100 px-2.5 py-0.5 rounded border border-rose-300">
                            <ShieldAlert size={14} className="text-rose-700" /> BLOCKED
                          </span>
                        )}
                      </div>
                      {d.failure_reason && (
                        <p className="mt-1 max-w-[170px] text-[10px] text-rose-700 font-bold font-mono">
                          {d.failure_reason}
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-4">
                      <span className="font-mono text-xs font-bold text-slate-900 bg-slate-100 px-2 py-0.5 rounded border border-slate-300">
                        {d.policy_id || 'pol_meridian_quickfin_v1'}
                      </span>
                    </td>
                    <td className="max-w-[170px] truncate px-4 py-4">
                      <span
                        title={d.model_commitment || ''}
                        className="font-mono text-xs font-semibold text-slate-700"
                      >
                        {d.model_commitment ? `${d.model_commitment.slice(0, 14)}…` : '—'}
                      </span>
                    </td>
                    <td className="px-4 py-4">
                      <button
                        type="button"
                        onClick={() => setSelectedRecord(d)}
                        className="inline-flex items-center gap-1 text-xs font-black text-indigo-700 hover:text-indigo-900 underline decoration-indigo-400 underline-offset-4"
                      >
                        Inspect Proof <ArrowUpRight size={13} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="px-6 py-14 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-600 border border-slate-300">
            <Clock3 size={20} />
          </div>
          <h3 className="mt-4 font-black text-slate-900">
            {loading ? 'Connecting to verifier…' : 'No decisions in current session'}
          </h3>
          <p className="mx-auto mt-1.5 max-w-md text-xs text-slate-600 font-medium">
            Submit a loan application in the QuickLoan Borrower Portal to trigger a live proof verification.
          </p>
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-200 px-6 py-3 text-[11px] text-slate-600 font-semibold bg-slate-50">
        <span>Auto-syncing with lender verifier every 4s</span>
        <span>
          Last update:{' '}
          {lastUpdated
            ? new Date(lastUpdated).toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata' }) + ' IST'
            : 'Connecting...'}
        </span>
      </div>

      {/* Expanded Verification Dossier Modal */}
      {selectedRecord && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl border-2 border-slate-300 shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="px-6 py-5 border-b border-slate-200 flex items-center justify-between sticky top-0 bg-white z-10">
              <div>
                <span className="text-[10px] font-black uppercase tracking-wider text-slate-500 block">
                  Lender Loan Dossier & ZK Verification
                </span>
                <h3 className="text-lg font-black text-slate-950 font-mono">
                  {selectedRecord.decision_id}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setSelectedRecord(null)}
                className="p-2 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100"
              >
                <X size={18} />
              </button>
            </div>

            <div className="p-6 space-y-6">
              {/* Customer Information Record - clean heading without icon */}
              <div>
                <h4 className="text-xs font-black uppercase tracking-wider text-slate-800 mb-3">
                  Borrower & Loan Application Record
                </h4>
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 grid grid-cols-2 sm:grid-cols-3 gap-3.5 text-xs">
                  <div>
                    <span className="text-slate-500 block text-[10px] uppercase font-bold">Legal Name</span>
                    <strong className="text-slate-950 text-sm font-black">{selectedRecord.customer_info?.name || 'Priya Sharma'}</strong>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px] uppercase font-bold">PAN Card</span>
                    <strong className="text-slate-950 font-mono text-sm font-black">{selectedRecord.customer_info?.pan || 'BNZPS1042K'}</strong>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px] uppercase font-bold">Mobile</span>
                    <strong className="text-slate-950 font-mono font-bold">{selectedRecord.customer_info?.phone || '+91 98201 44821'}</strong>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px] uppercase font-bold">Disbursal Account</span>
                    <strong className="text-slate-950 font-mono font-bold">{selectedRecord.customer_info?.bank_account || '9182014482103'}</strong>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px] uppercase font-bold">Bank IFSC</span>
                    <strong className="text-slate-950 font-mono uppercase font-bold">{selectedRecord.customer_info?.ifsc || 'HDFC0001234'}</strong>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px] uppercase font-bold">Requested Amount</span>
                    <strong className="text-slate-950 font-mono font-black">{money(selectedRecord.customer_info?.loan_amount || 150000)}</strong>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px] uppercase font-bold">Tenure</span>
                    <strong className="text-slate-950 font-bold">{selectedRecord.customer_info?.tenure || 36} Months</strong>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px] uppercase font-bold">Credit Score (CIBIL)</span>
                    <strong className="text-slate-950 font-mono font-black">{selectedRecord.customer_info?.bureau || 758}</strong>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px] uppercase font-bold">Monthly Income</span>
                    <strong className="text-slate-950 font-mono font-black">{money(selectedRecord.customer_info?.monthly_income || 95000)}</strong>
                  </div>
                </div>
              </div>

              {/* Gate Authorization Status */}
              <div className="p-4 rounded-xl border-2 flex items-center justify-between bg-slate-50 border-slate-300">
                <div>
                  <span className="text-xs text-slate-600 block font-bold">Disbursal Gate Decision</span>
                  <div className="flex items-center gap-2 mt-1">
                    {selectedRecord.status === 'VERIFIED' && selectedRecord.decision === 1 ? (
                      <span className="text-base font-black text-emerald-900 flex items-center gap-1.5">
                        <ShieldCheck size={18} className="text-emerald-700" /> Disbursal Authorized (Ready for 24h Release)
                      </span>
                    ) : (
                      <span className="text-base font-black text-rose-900 flex items-center gap-1.5">
                        <ShieldAlert size={18} className="text-rose-700" /> Disbursal Blocked (Fail-Closed)
                      </span>
                    )}
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-xs text-slate-600 block font-bold">Audit Block Height</span>
                  <strong className="text-base font-mono font-black text-slate-950">
                    {selectedRecord.ledger_seq ? `#${selectedRecord.ledger_seq}` : 'Pending'}
                  </strong>
                </div>
              </div>

              {/* Zero-Knowledge Proof Details - clean heading without icon */}
              <div>
                <div className="flex items-center justify-between mb-2.5">
                  <h4 className="text-xs font-black uppercase tracking-wider text-slate-800">
                    Halo2 Zero-Knowledge Proof Details
                  </h4>
                  {selectedRecord.proof_hash && (
                    <button
                      type="button"
                      onClick={() => handleCopy(selectedRecord.proof_hash || '', 'hash')}
                      className="text-xs font-mono font-bold text-indigo-700 hover:text-indigo-900 flex items-center gap-1"
                    >
                      {copiedKey === 'hash' ? <Check size={12} /> : <Copy size={12} />}
                      <span>Copy Digest</span>
                    </button>
                  )}
                </div>

                <div className="p-4 rounded-xl bg-slate-950 text-slate-100 text-xs font-mono space-y-2">
                  <div className="flex justify-between items-center py-1 border-b border-slate-800">
                    <span className="text-slate-400">Proof Hash (SHA-256):</span>
                    <span className="text-purple-300 truncate max-w-xs font-bold" title={selectedRecord.proof_hash || ''}>
                      {selectedRecord.proof_hash || 'Derived from witness'}
                    </span>
                  </div>

                  <div className="flex justify-between items-center py-1 border-b border-slate-800">
                    <span className="text-slate-400">Estimated Proof Size:</span>
                    <span className="text-slate-200">
                      {selectedRecord.proof_size_bytes || 2496} bytes (Halo2 KZG SNARK)
                    </span>
                  </div>

                  {selectedRecord.public_inputs && (
                    <div className="pt-2">
                      <span className="text-slate-400 block mb-1">Public Inputs Vector:</span>
                      <pre className="p-2.5 rounded bg-black text-[10px] text-slate-300 overflow-x-auto leading-relaxed border border-slate-800">
                        {JSON.stringify(selectedRecord.public_inputs, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </div>

              {/* 9-Step Verification Status Summary */}
              <div>
                <h4 className="text-xs font-black uppercase tracking-wider text-slate-800 mb-2.5">
                  Verifier Engine Validation Summary (V1 to V9)
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                  {[
                    { code: 'V1', label: 'Policy Active & Signed' },
                    { code: 'V2', label: 'Model Commitment (C) Match' },
                    { code: 'V3', label: 'Canonical Policy Hash Match' },
                    { code: 'V4', label: 'Threshold Agreement (tau=0.50)' },
                    { code: 'V5', label: 'Replay Window Valid' },
                    { code: 'V6', label: 'Proof Uniqueness' },
                    { code: 'V7', label: 'Notice & Input Commitment' },
                    { code: 'V8', label: 'Halo2 Circuit Cryptographic Proof' },
                    { code: 'V9', label: 'Hard Policy Rules' },
                  ].map((v) => {
                    const isPassed = selectedRecord.status === 'VERIFIED';
                    return (
                      <div
                        key={v.code}
                        className={`p-2.5 rounded-lg border flex items-center justify-between ${
                          isPassed ? 'bg-emerald-50 border-emerald-300' : 'bg-slate-50 border-slate-300'
                        }`}
                      >
                        <span className="font-mono text-slate-900 font-semibold">
                          <strong>{v.code}</strong>: {v.label}
                        </span>
                        <span
                          className={`text-[10px] font-black px-2 py-0.5 rounded ${
                            isPassed
                              ? 'bg-emerald-200 text-emerald-950'
                              : 'bg-rose-200 text-rose-950'
                          }`}
                        >
                          {isPassed ? 'PASSED' : 'CHECK'}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Footer Actions */}
              <div className="pt-4 border-t border-slate-200 flex items-center justify-between">
                <a
                  href={`/receipt/${encodeURIComponent(selectedRecord.decision_id)}`}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs font-black text-indigo-700 hover:text-indigo-900 flex items-center gap-1"
                >
                  <FileText size={14} /> Open Full Sanction Letter <ArrowUpRight size={13} />
                </a>

                <button
                  type="button"
                  onClick={() => setSelectedRecord(null)}
                  className="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-900 font-bold text-xs rounded-lg transition-colors"
                >
                  Close Dossier
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
