import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, ArrowUpRight, CheckCircle2, CircleAlert, FileCheck2, Printer, ShieldCheck, XCircle } from 'lucide-react';
import { fetchDecision } from '../api/client';
import type { DecisionRecord } from '../api/types';

const ist = (v?: string | null) => { 
  if (!v) return '—'; 
  const d = new Date(v); 
  return Number.isNaN(d.getTime()) ? v : new Intl.DateTimeFormat('en-IN', { dateStyle:'long', timeStyle:'medium', timeZone:'Asia/Kolkata' }).format(d)+' IST'; 
};

export function BorrowerReceipt() {
  const { id = '' } = useParams(); 
  const [record, setRecord] = useState<DecisionRecord | null>(null); 
  const [error, setError] = useState(''); 
  const [loading, setLoading] = useState(true);

  useEffect(() => { 
    let alive = true; 
    fetchDecision(id)
      .then(r => { if (alive) setRecord(r); })
      .catch(() => { if (alive) setError('Could not load this decision from the lender API.'); })
      .finally(() => { if (alive) setLoading(false); }); 
    return () => { alive = false; }; 
  }, [id]);

  const verified = record?.status === 'VERIFIED';
  const approved = record?.decision === 1;

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 sm:px-7 sm:py-12">
      <div className="no-print mb-6 flex items-center justify-between">
        <Link to="/borrower" className="inline-flex items-center gap-2 text-xs font-bold text-slate-600 hover:text-slate-900">
          <ArrowLeft size={14}/> Back to borrower portal
        </Link>
        <button 
          onClick={() => window.print()} 
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 text-white rounded-lg text-xs font-semibold hover:bg-slate-800 transition-colors"
        >
          <Printer size={13}/> Print Sanction Certificate
        </button>
      </div>

      <article className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        {/* Certificate Header */}
        <div className={`p-6 sm:p-8 border-b ${
          verified && approved 
            ? 'bg-gradient-to-r from-emerald-900 to-slate-900 text-white' 
            : 'bg-slate-900 text-white'
        }`}>
          <div className="flex items-start justify-between gap-4">
            <div>
              <span className="font-mono text-[10px] font-bold uppercase tracking-widest text-emerald-400 block mb-1">
                Official Sanction & Verification Certificate
              </span>
              <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
                {approved && verified ? 'Loan Sanction Authorized' : 'Application Decision Record'}
              </h1>
              <p className="mt-1 text-xs sm:text-sm text-slate-300">
                Regulated Entity: NBFC-42 Capital · Partner LSP: LSP-X Fintech
              </p>
            </div>
            {verified && approved ? (
              <CheckCircle2 size={40} className="text-emerald-400 shrink-0" />
            ) : (
              <FileCheck2 size={40} className="text-slate-400 shrink-0" />
            )}
          </div>

          <div className="mt-6 flex flex-wrap items-center gap-3 pt-4 border-t border-white/10 text-xs font-mono">
            <span>Reference ID: <strong>{id}</strong></span>
            <span>•</span>
            <span>Status: <strong className={verified ? 'text-emerald-400' : 'text-amber-400'}>{record?.status || 'QUERYING'}</strong></span>
          </div>
        </div>

        {/* Certificate Body */}
        <div className="p-6 sm:p-8 space-y-6">
          {error && (
            <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
              <CircleAlert size={16} className="text-rose-600 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {loading ? (
            <div className="py-12 text-center text-slate-500 text-xs">
              Fetching verified decision certificate...
            </div>
          ) : (
            <>
              {/* Decision Box */}
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Underwriting Outcome</span>
                  <div className="flex items-center gap-2 mt-0.5">
                    {approved ? (
                      <span className="text-base font-bold text-emerald-700 flex items-center gap-1">
                        <CheckCircle2 size={16} /> APPROVED
                      </span>
                    ) : (
                      <span className="text-base font-bold text-rose-700 flex items-center gap-1">
                        <XCircle size={16} /> REJECTED / HOLD
                      </span>
                    )}
                  </div>
                </div>

                <div className="text-left sm:text-right">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Disbursal Gate</span>
                  <span className={`text-xs font-bold px-2 py-0.5 rounded inline-block mt-0.5 ${
                    verified && approved ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
                  }`}>
                    {verified && approved ? 'FUNDS AUTHORIZED' : 'DISBURSAL BLOCKED'}
                  </span>
                </div>
              </div>

              {/* Data Fields Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                <div className="p-3 rounded-lg border border-slate-100">
                  <span className="text-slate-400 block text-[10px] uppercase font-semibold">Policy Document</span>
                  <strong className="text-slate-800 font-mono block mt-1">{record?.policy_id || '—'}</strong>
                </div>

                <div className="p-3 rounded-lg border border-slate-100">
                  <span className="text-slate-400 block text-[10px] uppercase font-semibold">Verified Timestamp</span>
                  <strong className="text-slate-800 block mt-1">{ist(record?.verified_at)}</strong>
                </div>

                <div className="p-3 rounded-lg border border-slate-100">
                  <span className="text-slate-400 block text-[10px] uppercase font-semibold">Audit Ledger Block Height</span>
                  <strong className="text-slate-800 font-mono block mt-1">
                    {record?.ledger_seq ? `#${record.ledger_seq}` : 'Pending Commit'}
                  </strong>
                </div>

                <div className="p-3 rounded-lg border border-slate-100">
                  <span className="text-slate-400 block text-[10px] uppercase font-semibold">Model Commitment (C)</span>
                  <strong className="text-slate-800 font-mono block mt-1 truncate" title={record?.model_commitment || ''}>
                    {record?.model_commitment || '—'}
                  </strong>
                </div>
              </div>

              {/* Zero Knowledge Conformance Box */}
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 flex items-start gap-3">
                <ShieldCheck size={20} className="text-emerald-600 mt-0.5 shrink-0" />
                <div className="text-xs text-slate-600 leading-relaxed">
                  <strong className="text-slate-900 block mb-0.5">Cryptographic Conformance Guarantee</strong>
                  This record is cryptographically anchored in the immutable audit ledger. The lender verifier has confirmed through zero-knowledge proof evaluation that the loan decision adheres exactly to the agreed credit scorecard and cutoff policy.
                </div>
              </div>

              {/* Action Buttons */}
              <div className="no-print pt-4 border-t border-slate-100 flex items-center justify-between">
                <Link to="/" className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1">
                  Return to Lender Operations <ArrowUpRight size={13} />
                </Link>
                <button 
                  onClick={() => window.print()}
                  className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-bold transition-colors"
                >
                  Print Certificate
                </button>
              </div>
            </>
          )}
        </div>
      </article>
    </main>
  );
}
