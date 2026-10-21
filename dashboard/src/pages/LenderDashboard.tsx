import { useCallback, useEffect, useRef, useState } from 'react';
import { AlertTriangle, ArrowUpRight, RotateCcw } from 'lucide-react';
import { fetchHealth, fetchSummary, resetDatabase } from '../api/client';
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
  const [resetting, setResetting] = useState(false);
  const [actionNotice, setActionNotice] = useState<string | null>(null);
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

  const handleResetDb = async () => {
    if (!window.confirm('Reset database? This will wipe all decision records and ledger entries, then re-seed the baseline verified policy and model.')) {
      return;
    }
    setResetting(true);
    setActionNotice(null);
    try {
      const res = await resetDatabase();
      setActionNotice(res.message || 'Database reset and initial record seeded.');
      await refresh();
      setTimeout(() => setActionNotice(null), 4000);
    } catch (err: any) {
      alert('Failed to reset database: ' + (err?.message || 'Server error'));
    } finally {
      setResetting(false);
    }
  };

  useEffect(() => {
    void refresh();
    const id = window.setInterval(() => void refresh(), 4000);
    return () => window.clearInterval(id);
  }, [refresh]);

  return (
    <main className="relative mx-auto w-[calc(100%-32px)] md:w-[calc(100%-48px)] xl:w-[calc(100%-64px)] max-w-[1600px] py-7 sm:py-9">
      {/* Top Banner */}
      <section className="mb-7 grid gap-6 lg:grid-cols-[1.5fr_.8fr] lg:items-end">
        <div>
          <div className="mb-2.5 flex items-center justify-between">
            <span className="inline-flex items-center px-3 py-1 rounded-md text-xs font-black uppercase tracking-wider bg-indigo-100 text-indigo-950 border border-indigo-300">
              LSP Partner: Quick FinCorp Pvt Ltd
            </span>

            {/* Quick Reset Action Button */}
            <button
              type="button"
              disabled={resetting}
              onClick={handleResetDb}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-extrabold text-rose-700 bg-white border border-rose-300 rounded-lg hover:bg-rose-50 shadow-2xs transition-colors"
              title="Wipe database and re-seed baseline verified policy & record"
            >
              <RotateCcw size={13} className={resetting ? 'animate-spin' : ''} />
              <span>{resetting ? 'Resetting DB...' : 'Reset & Seed DB'}</span>
            </button>
          </div>
          <h1 className="max-w-4xl text-3xl sm:text-5xl font-black tracking-tight text-slate-950">
            Lender Dashboard
          </h1>
          <p className="mt-2 max-w-2xl text-sm sm:text-base text-slate-700 font-medium">
            Real-time underwriting oversight, borrower loan records, zero-knowledge contract conformance verification, and fail-closed disbursal enforcement for Quick FinCorp Pvt Ltd.
          </p>
        </div>
        <HashChainViewer data={data} />
      </section>

      {actionNotice && (
        <div className="mb-5 flex items-center justify-between bg-emerald-100 border border-emerald-300 px-4 py-3 rounded-xl text-emerald-950 text-xs font-bold shadow-xs animate-in fade-in">
          <span>✓ {actionNotice}</span>
        </div>
      )}

      {error && (
        <div role="status" className="mb-6 flex items-start gap-3 border-2 border-rose-300 bg-rose-50 p-4 rounded-xl text-rose-950 text-xs font-semibold">
          <AlertTriangle size={18} className="mt-0.5 shrink-0 text-rose-600" />
          <div>
            <p className="font-extrabold">Node Communication Alert</p>
            <p className="mt-0.5 text-xs text-rose-800">{error}</p>
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
          <div className="bg-slate-950 rounded-2xl p-6 text-white border border-slate-800 shadow-md">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <span className="font-mono text-[10px] uppercase tracking-wider text-emerald-400 font-black">
                Disbursal Gate Protocol
              </span>
              <span className="text-[10px] font-mono text-slate-400 font-bold">Strict Enforcement</span>
            </div>
            <h2 className="mt-4 text-xl font-extrabold tracking-tight text-white">
              Fail-Closed Disbursal Authorization
            </h2>
            <p className="mt-2 text-xs leading-relaxed text-slate-300">
              The Loan Management System (LMS) strictly holds loan disbursals. Funds may be released only when the verifier confirms all 9 cryptographic checks (<code className="rounded bg-slate-800 px-1.5 py-0.5 text-emerald-400 font-mono font-bold">VERIFIED</code>).
            </p>
            <div className="mt-5 pt-4 border-t border-slate-800 flex items-center justify-between">
              <Link to="/ledger" className="inline-flex items-center gap-1.5 text-xs font-extrabold text-emerald-400 hover:text-emerald-300">
                Inspect Immutable Audit Ledger <ArrowUpRight size={13} />
              </Link>
            </div>
          </div>

          {/* Underwriting Model Specifications */}
          <div className="bg-white rounded-2xl p-6 border-2 border-slate-300 shadow-sm">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <span className="text-xs font-black uppercase tracking-wider text-slate-700">
                Agreed Contract Parameters
              </span>
              <span className="text-[11px] font-mono font-black text-indigo-900 bg-indigo-100 px-2 py-0.5 rounded border border-indigo-300">
                v1.0 Active
              </span>
            </div>
            <div className="mt-4 space-y-3 text-xs">
              <div className="flex justify-between py-1.5 border-b border-slate-200">
                <span className="text-slate-600 font-semibold">Partner LSP:</span>
                <span className="font-black text-slate-950">Quick FinCorp Pvt Ltd</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-200">
                <span className="text-slate-600 font-semibold">Lender Entity:</span>
                <span className="font-black text-slate-950">Meridian Digital</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-200">
                <span className="text-slate-600 font-semibold">Policy Contract:</span>
                <span className="font-mono font-bold text-slate-900">pol_meridian_quickfin_v1</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-200">
                <span className="text-slate-600 font-semibold">Decision Cutoff (tau):</span>
                <span className="font-mono font-black text-slate-950">0.500 (50.0%)</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-200">
                <span className="text-slate-600 font-semibold">Underwriting Prover:</span>
                <span className="font-mono font-bold text-slate-800">Halo2 / EZKL (KZG)</span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-slate-600 font-semibold">Audit Commitment (C):</span>
                <span className="font-mono text-slate-600 text-xs font-bold">0xd031786a...</span>
              </div>
            </div>
          </div>
        </aside>
      </section>
    </main>
  );
}
