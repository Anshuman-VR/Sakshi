import { useCallback, useEffect, useRef, useState } from 'react';
import { AlertTriangle, ArrowUpRight, ShieldCheck, Database } from 'lucide-react';
import { fetchHealth, fetchSummary } from '../api/client';
import type { DashboardSummary } from '../api/types';
import { StatsOverview } from '../components/StatsOverview';
import { LiveDecisionFeed } from '../components/LiveDecisionFeed';
import { HashChainViewer } from '../components/HashChainViewer';
import { Link } from 'react-router-dom';

export function LenderDashboard() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [healthy, setHealthy] = useState(false);
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
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <span className="font-mono inline-flex items-center gap-2 border border-slate-300 bg-white px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider rounded-md text-slate-800 shadow-2xs">
              <span className="h-2 w-2 rounded-full bg-indigo-600" /> Regulated Entity Node
            </span>
            <span
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider ${
                healthy
                  ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                  : 'bg-slate-100 text-slate-600 border border-slate-200'
              }`}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${healthy ? 'bg-emerald-600' : 'bg-slate-400'}`} />
              {healthy ? 'NODE ONLINE (PORT 8000)' : 'NODE OFFLINE'}
            </span>
          </div>
          <h1 className="max-w-4xl text-3xl sm:text-5xl font-extrabold tracking-tight text-slate-900">
            Credit Risk & Underwriting Operations
          </h1>
          <p className="mt-3 max-w-2xl text-sm sm:text-base text-slate-600">
            Real-time monitoring of loan decisions, cryptographic zero-knowledge conformance verifications, and fail-closed disbursal gate policies.
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
              The Loan Management System (LMS) strictly holds disbursals. Funds may be released only when the verifier confirms all 9 cryptographic checks (<code className="rounded bg-slate-800 px-1 py-0.5 text-emerald-400 font-mono">VERIFIED</code>).
            </p>
            <div className="mt-5 pt-4 border-t border-slate-800 flex items-center justify-between">
              <Link to="/ledger" className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-400 hover:text-emerald-300">
                Inspect Immutable Audit Ledger <ArrowUpRight size={13} />
              </Link>
            </div>
          </div>

          {/* Active Policy & Model Specs Card */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm text-xs space-y-3">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <span className="font-bold text-slate-900 flex items-center gap-1.5">
                <Database size={15} className="text-indigo-600" /> Active Policy Specification
              </span>
              <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                ACTIVE
              </span>
            </div>
            <div className="space-y-2 font-mono text-slate-600">
              <div className="flex justify-between py-1 border-b border-slate-50">
                <span className="text-slate-400">Policy Contract:</span>
                <span className="text-slate-900 font-bold">pol_nbfc42_lspX_personal_v1</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-50">
                <span className="text-slate-400">Regulated Entity:</span>
                <span className="text-slate-900">NBFC-42 Capital</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-50">
                <span className="text-slate-400">Partner LSP:</span>
                <span className="text-slate-900">LSP-X Fintech</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-400">Cutoff Threshold:</span>
                <span className="text-indigo-600 font-bold">0.200 (Cutoff)</span>
              </div>
            </div>
          </div>
        </aside>
      </section>
    </main>
  );
}
