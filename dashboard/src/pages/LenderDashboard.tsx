import { useCallback, useEffect, useRef, useState } from 'react';
import { Activity, AlertTriangle, ArrowDownRight, ArrowUpRight, ShieldCheck } from 'lucide-react';
import { fetchHealth, fetchSummary } from '../api/client';
import type { DashboardSummary } from '../api/types';
import { StatsOverview } from '../components/StatsOverview';
import { LiveDecisionFeed } from '../components/LiveDecisionFeed';
import { HashChainViewer } from '../components/HashChainViewer';
import { InfoTip } from '../components/InfoTip';

export function LenderDashboard() {
  const [data, setData] = useState<DashboardSummary | null>(null); const [healthy, setHealthy] = useState(false); const [loading, setLoading] = useState(true); const [error, setError] = useState(''); const [lastUpdated, setLastUpdated] = useState('');
  const refreshInFlight = useRef(false);
  const refresh = useCallback(async () => {
    // Skip a tick while the previous request is still in flight, so older responses
    // cannot overwrite newer dashboard state.
    if (refreshInFlight.current) return;
    refreshInFlight.current = true;
    try {
      const isHealthy = await fetchHealth(); setHealthy(isHealthy);
      try { const summary = await fetchSummary(); setData(summary); setError(''); setLastUpdated(new Date().toISOString()); }
      catch { setError('The lender API did not return dashboard data. This view does not invent live decisions.'); }
    } catch { setHealthy(false); setError('The lender API health check failed. Live data may be unavailable.'); }
    finally { refreshInFlight.current = false; setLoading(false); }
  }, []);
  useEffect(() => { void refresh(); const id = window.setInterval(() => void refresh(), 5000); return () => window.clearInterval(id); }, [refresh]);
  return <main className="relative mx-auto w-[calc(100%-32px)] md:w-[calc(100%-48px)] xl:w-[calc(100%-64px)] max-w-[1600px] py-7 sm:py-10">
    <section className="mb-8 grid gap-6 lg:grid-cols-[1.5fr_.8fr] lg:items-end"><div><div className="mb-4 flex flex-wrap items-center gap-2"><span className="mono inline-flex items-center gap-2 border border-line bg-accent px-2.5 py-1 text-[10px] font-bold uppercase tracking-[.14em]"><span className="h-2 w-2 rounded-full bg-surface"/> Lender operations</span><span className={`status-pill ${healthy ? 'bg-emerald-100 text-emerald-800' : 'bg-surface text-stone-700'}`}><span className={`h-1.5 w-1.5 rounded-full ${healthy ? 'bg-emerald-700' : 'bg-stone-400'}`}/>{healthy ? 'API ONLINE' : 'API NOT CONNECTED'}</span></div><h1 className="max-w-4xl text-4xl font-bold leading-[.98] tracking-[-.07em] sm:text-6xl">Every decision.<br/><span className="text-stone-600">Accounted for.</span></h1><p className="mt-5 max-w-2xl text-sm leading-6 text-stone-600 sm:text-base">Monitor whether lending decisions follow the configured rules, review verification outcomes, and inspect the audit record.</p></div><HashChainViewer data={data}/></section>
    {error && <div role="status" className="mb-6 flex items-start gap-3 border-[1.5px] border-line bg-surface p-4"><AlertTriangle size={19} className="mt-0.5 shrink-0"/><div><p className="font-bold">Live data unavailable</p><p className="mt-1 text-sm">{error} Check that the Dev 2 API is running on port 8000. For a safe presentation, open the separate Demo Lab.</p></div></div>}
    <StatsOverview data={data}/>
    <section className="mt-8 grid gap-6 xl:grid-cols-[1.7fr_.8fr]"><LiveDecisionFeed decisions={data?.recent_decisions ?? []} loading={loading} onRefresh={() => {setLoading(true); void refresh();}} lastUpdated={lastUpdated}/><aside className="space-y-4"><div className="brutal-card bg-accent p-5 text-white"><div className="flex items-center justify-between"><span className="mono text-[10px] uppercase tracking-[.15em] text-white">Control principle <InfoTip label="Fail-closed control" text="When required verification is missing, fails, or cannot be reached, the safe outcome is to block the action rather than assume it is allowed." /></span><ShieldCheck className="text-white" size={23}/></div><h2 className="mt-4 text-2xl font-bold leading-tight tracking-tight">No proof.<br/>No disbursal.</h2><p className="mt-3 text-sm leading-6 text-slate-200">The mock Loan Management System (LMS) may release funds only when the verifier returns exactly <code className="rounded bg-surface/10 px-1.5 py-0.5 text-white">VERIFIED</code>. Pending, missing, failed, or unreachable results must always hold disbursal.</p><div className="mt-5 border-t border-white/20 pt-4"><a href="/ledger" className="inline-flex items-center gap-2 text-sm font-bold text-white underline underline-offset-4">Inspect audit ledger <ArrowUpRight size={14}/></a></div></div>
      <div className="brutal-card bg-surface p-5"><div className="flex items-center gap-2"><ArrowDownRight size={18}/><p className="mono text-[10px] font-bold uppercase tracking-[.13em]">Safe presentation</p></div><h3 className="mt-3 text-xl font-bold">Demo without side effects.</h3><p className="mt-2 text-sm leading-6">The Demo Lab uses local browser fixtures. Simulated scenarios never send fabricated proof payloads to the lender API.</p><a href="/demo" className="brutal-button mt-4 inline-flex items-center gap-2 bg-surface px-3 py-2 text-xs font-bold">Launch demo lab <ArrowUpRight size={14}/></a></div>
      <div className="flex items-center gap-2 px-1 text-[11px] text-stone-500"><Activity size={13}/><span>Live values are sourced from the verifier API only.</span></div>
    </aside></section>
  </main>;
}
