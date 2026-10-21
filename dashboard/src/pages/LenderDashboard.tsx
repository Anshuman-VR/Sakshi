import { useCallback, useEffect, useRef, useState } from 'react';
import { AlertTriangle, ArrowUpRight, ShieldCheck, Building } from 'lucide-react';
import { fetchHealth, fetchSummary } from '../api/client';
import type { DashboardSummary } from '../api/types';
import { StatsOverview } from '../components/StatsOverview';
import { LiveDecisionFeed } from '../components/LiveDecisionFeed';
import { HashChainViewer } from '../components/HashChainViewer';
import { Link } from 'react-router-dom';

export function LenderDashboard() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [, setHealthy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [lastUpdated, setLastUpdated] = useState('');
  const refreshInFlight = useRef(false);

  const refresh = useCallback(async () => {
    if (refreshInFlight.current) return;
    refreshInFlight.current = true;
    try {
      const isHealthy = await fetchHealth();
      setHealthy(isHealthy);
      try {
        const summary = await fetchSummary();
        setData(summary);
        setError('');
        setLastUpdated(new Date().toISOString());
      } catch {
        setError('Unable to retrieve latest underwriting summary from lender node.');
      }
    } catch {
      setHealthy(false);
      setError('Lender verification node is currently unreachable.');
    } finally {
      refreshInFlight.current = false;
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const id = window.setInterval(() => void refresh(), 4000);
    return () => window.clearInterval(id);
  }, [refresh]);

  return (
    <main className="relative mx-auto w-[calc(100%-32px)] md:w-[calc(100%-48px)] xl:w-[calc(100%-64px)] max-w-[1600px] py-7 sm:py-10">
      {/* Top Banner */}
      <section className="mb-8 grid gap-6 lg:grid-cols-[1.5fr_.8fr] lg:items-end">
        <div>
          <div className="mb-3 flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-bold uppercase tracking-wider bg-indigo-50 text-indigo-900 border border-indigo-200">
              <Building size={14} className="text-indigo-700" />
              LSP Partner: Quick FinCorp Pvt Ltd
            </span>
          </div>
          <h1 className="max-w-4xl text-3xl sm:text-5xl font-extrabold tracking-tight text-slate-900">
            Lender Dashboard
          </h1>
          <p className="mt-2.5 max-w-2xl text-sm sm:text-base text-slate-600">
            Real-time underwriting oversight, borrower loan records, zero-knowledge contract conformance verification, and fail-closed disbursal enforcement for Quick FinCorp Pvt Ltd.
          </p>
        </div>
        <HashChainViewer data={data} />
      </section>

      {error && (
        <div role="status" className="mb-6 flex items-start gap-3 border border-rose-200 bg-rose-50 p-4 rounded-xl text-rose-800 text-xs">
          <AlertTriangle size={18} className="mt-0.5 shrink-0 text-rose-600" />
          <div>
            <p className="font-bold">Node Communication Alert</p>
            <p className="mt-0.5 text-xs text-rose-700">{error}</p>
          </div>
        </div>
      )}

      {/* Aggregate Metrics */}
      <StatsOverview data={data} />

      {/* Live Stream & Side Controls */}
      <section className="mt-8 grid gap-6 xl:grid-cols-[1.7fr_.8fr]">
        <LiveDecisionFeed
          decisions={data?.recent_decisions ?? []}
          loading={loading}
          onRefresh={() => {
            setLoading(true);
            void refresh();
          }}
          lastUpdated={lastUpdated}
        />

        <aside className="space-y-5">
          {/* Fail-Closed Card */}
          <div className="bg-slate-900 rounded-2xl p-6 text-white border border-slate-800 shadow-md">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <span className="font-mono text-[10px] uppercase tracking-wider text-emerald-400 font-bold flex items-center gap-1.5">
                <ShieldCheck size={14} /> Disbursal Gate Protocol
              </span>
              <span className="text-[10px] font-mono text-slate-400">Strict Enforcement</span>
            </div>
            <h2 className="mt-4 text-xl font-bold tracking-tight text-white">
              Fail-Closed Disbursal Authorization
            </h2>
            <p className="mt-2 text-xs leading-relaxed text-slate-300">
              The Loan Management System (LMS) strictly holds loan disbursals. Funds may be released only when the verifier confirms all 9 cryptographic checks (<code className="rounded bg-slate-800 px-1 py-0.5 text-emerald-400 font-mono">VERIFIED</code>).
            </p>
            <div className="mt-5 pt-4 border-t border-slate-800 flex items-center justify-between">
              <Link to="/ledger" className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-400 hover:text-emerald-300">
                Inspect Immutable Audit Ledger <ArrowUpRight size={13} />
              </Link>
            </div>
          </div>

          {/* Underwriting Model Specifications */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Agreed Contract Parameters
              </span>
              <span className="text-[11px] font-mono font-bold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-200">
                v1.0 Active
              </span>
            </div>
            <div className="mt-4 space-y-3 text-xs">
              <div className="flex justify-between py-1.5 border-b border-slate-100">
                <span className="text-slate-500">Partner LSP:</span>
                <span className="font-bold text-slate-900">Quick FinCorp Pvt Ltd</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-100">
                <span className="text-slate-500">Lender Entity:</span>
                <span className="font-bold text-slate-900">Meridian Digital</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-100">
                <span className="text-slate-500">Policy Contract:</span>
                <span className="font-mono font-semibold text-slate-800">pol_meridian_quickfin_v1</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-100">
                <span className="text-slate-500">Decision Cutoff (tau):</span>
                <span className="font-mono font-bold text-slate-900">0.500 (50.0%)</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-100">
                <span className="text-slate-500">Underwriting Prover:</span>
                <span className="font-mono text-slate-700">Halo2 / EZKL (KZG)</span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-slate-500">Audit Commitment (C):</span>
                <span className="font-mono text-slate-500 text-[11px]">0xd031786a...</span>
              </div>
            </div>
          </div>
        </aside>
      </section>
    </main>
  );
}
