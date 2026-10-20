import { ArrowUpRight, Clock3, RefreshCw, CheckCircle2, XCircle } from 'lucide-react';
import type { DecisionRecord } from '../api/types';
import { InfoTip } from './InfoTip';
import { StatusPill } from './StatusPill';

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
  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm min-w-0 overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-6 py-4 bg-slate-50/50">
        <div>
          <span className="font-mono text-[10px] uppercase tracking-wider text-slate-500 font-bold block">
            Real-Time Decision Stream
          </span>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">
            Recent Decisions & Conformance Records
          </h2>
        </div>
        <button
          onClick={onRefresh}
          className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg shadow-sm hover:bg-slate-50 hover:text-slate-900 transition-colors"
        >
          <RefreshCw size={13} className={loading ? 'animate-spin text-indigo-600' : ''} />
          Refresh
        </button>
      </div>

      {decisions.length ? (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="bg-slate-50 text-[10px] uppercase tracking-wider text-slate-500 border-b border-slate-200 font-semibold">
              <tr>
                <th className="px-6 py-3">Decision ID / Timestamp</th>
                <th className="px-4 py-3">Underwriting Decision</th>
                <th className="px-4 py-3">
                  Policy{' '}
                  <InfoTip
                    label="Policy reference"
                    text="Dual-signed policy contract ID governing this underwriting model and loan criteria."
                  />
                </th>
                <th className="px-4 py-3">
                  Model Commitment (C){' '}
                  <InfoTip
                    label="Model commitment"
                    text="Salted cryptographic SHA-256 commitment of the approved ML model parameters."
                  />
                </th>
                <th className="px-4 py-3">ZK Conformance</th>
                <th className="px-4 py-3">Receipt</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {decisions.map((d) => {
                const isApproved = d.decision === 1;
                return (
                  <tr key={d.decision_id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="px-6 py-4">
                      <div className="font-mono text-xs font-bold text-slate-900">{d.decision_id}</div>
                      <div className="mt-0.5 text-[11px] text-slate-500">{ist(d.verified_at)}</div>
                    </td>
                    <td className="px-4 py-4">
                      {d.decision !== undefined && d.decision !== null ? (
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
                            isApproved
                              ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                              : 'bg-rose-50 text-rose-800 border-rose-200'
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
                      <span className="font-mono text-xs text-slate-700 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                        {d.policy_id || '—'}
                      </span>
                    </td>
                    <td className="max-w-[180px] truncate px-4 py-4">
                      <span
                        title={d.model_commitment || ''}
                        className="font-mono text-xs text-slate-500"
                      >
                        {d.model_commitment ? `${d.model_commitment.slice(0, 12)}…` : '—'}
                      </span>
                    </td>
                    <td className="px-4 py-4">
                      <StatusPill status={d.status} />
                      {d.failure_reason && (
                        <p className="mt-1 max-w-[170px] text-[10px] text-red-600 font-medium">
                          {d.failure_reason}
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-4">
                      <a
                        href={`/receipt/${encodeURIComponent(d.decision_id)}`}
                        className="inline-flex items-center gap-1 text-xs font-bold text-indigo-600 hover:text-indigo-800 underline decoration-indigo-300 underline-offset-4"
                      >
                        Inspect <ArrowUpRight size={13} />
                      </a>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="px-6 py-14 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-600 border border-slate-200">
            <Clock3 size={20} />
          </div>
          <h3 className="mt-4 font-bold text-slate-800">
            {loading ? 'Connecting to verifier…' : 'No live decisions yet'}
          </h3>
          <p className="mx-auto mt-1.5 max-w-md text-xs text-slate-500">
            Submit a live borrower application in the Borrower Portal to execute the full ZK proving pipeline.
          </p>
          <a
            href="/borrower"
            className="mt-4 inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-semibold hover:bg-indigo-700 transition-colors"
          >
            Open Borrower Portal <ArrowUpRight size={14} />
          </a>
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-200 px-6 py-3 text-[11px] text-slate-500 bg-slate-50/30">
        <span>Polling lender API every 5 seconds</span>
        <span>
          Last update:{' '}
          {lastUpdated
            ? new Date(lastUpdated).toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata' }) + ' IST'
            : 'Connecting...'}
        </span>
      </div>
    </div>
  );
}
