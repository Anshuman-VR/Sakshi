import { Activity, CheckCircle2, ShieldX, Zap } from 'lucide-react';
import type { DashboardSummary } from '../api/types';
import { InfoTip } from './InfoTip';
import type { ReactNode } from 'react';

function StatCard({ 
  label, 
  value, 
  detail, 
  icon: Icon, 
  suffix 
}: { 
  label: ReactNode; 
  value: string | number; 
  detail: string; 
  icon: typeof Activity; 
  suffix?: string 
}) { 
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-bold uppercase tracking-wider text-slate-500">{label}</p>
        <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-100 text-slate-700 border border-slate-200">
          <Icon size={18} />
        </span>
      </div>
      <div className="mt-4 flex items-baseline gap-1">
        <span className="text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">{value}</span>
        {suffix && <span className="font-mono text-xs text-slate-500 font-semibold">{suffix}</span>}
      </div>
      <p className="mt-2 text-xs text-slate-500 font-medium">{detail}</p>
    </div>
  );
}

export function StatsOverview({ data }: { data: DashboardSummary | null }) { 
  return (
    <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <StatCard 
        label={<>Decisions Audited <InfoTip label="Decisions Audited" text="Total decision records received and evaluated by the lender node verifier." /></>} 
        value={data?.total_decisions ?? '—'} 
        detail="Underwritten by partner LSP" 
        icon={Activity} 
      />
      <StatCard 
        label={<>Verified Proofs <InfoTip label="Verified Proofs" text="Total proofs that passed all 9 mathematical and cryptographic verifications." /></>} 
        value={data?.verified ?? '—'} 
        detail="Zero-knowledge proofs confirmed" 
        icon={CheckCircle2} 
      />
      <StatCard 
        label={<>Disbursals Blocked <InfoTip label="Disbursals Blocked" text="Records where verification failed or under-threshold criteria triggered fail-closed block." /></>} 
        value={data?.failed ?? '—'} 
        detail="Fail-closed protections enforced" 
        icon={ShieldX} 
      />
      <StatCard 
        label={<>Proof Latency · p50 <InfoTip label="Proof Latency p50" text="Median time for zero-knowledge verification proof generation and ingestion." /></>} 
        value={data?.proof_latency_p50_ms == null ? '—' : data.proof_latency_p50_ms.toFixed(1)} 
        suffix="ms" 
        detail={data?.proof_latency_p95_ms == null ? 'Target SLA < 10 mins' : `p95 ${data.proof_latency_p95_ms.toFixed(1)} ms`} 
        icon={Zap} 
      />
    </section>
  ); 
}
