import { useCallback, useEffect, useState } from 'react';
import { ArrowUpRight, CheckCheck, CircleAlert, RefreshCw, RotateCcw } from 'lucide-react';
import { fetchLedger, resetDatabase } from '../api/client';
import type { LedgerRecord } from '../api/types';
import { InfoTip } from '../components/InfoTip';
import { StatusPill } from '../components/StatusPill';

export function AuditLedger() {
  const [entries, setEntries] = useState<LedgerRecord[]>([]); 
  const [loading, setLoading] = useState(true); 
  const [error, setError] = useState('');
  const [resetting, setResetting] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setEntries(await fetchLedger());
      setError('');
    } catch {
      setError('The ledger endpoint is unavailable or returned an unrecognized response.');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleReset = async () => {
    if (!window.confirm('Reset database? This will clear all ledger entries and re-seed the verified policy and baseline block.')) {
      return;
    }
    setResetting(true);
    setNotice(null);
    try {
      const res = await resetDatabase();
      setNotice(res.message || 'Database reset successfully.');
      await load();
      setTimeout(() => setNotice(null), 4000);
    } catch (err: any) {
      alert('Reset failed: ' + (err?.message || 'Server error'));
    } finally {
      setResetting(false);
    }
  };

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <main className="mx-auto w-[calc(100%-32px)] md:w-[calc(100%-48px)] xl:w-[calc(100%-64px)] max-w-[1600px] py-7 sm:py-9">
      {/* Header */}
      <div className="mb-7 flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="mb-2.5 flex items-center gap-2">
            <span className="inline-flex items-center px-3 py-1 rounded-md text-xs font-black uppercase tracking-wider bg-indigo-100 text-indigo-950 border border-indigo-300">
              LSP Partner: Quick FinCorp Pvt Ltd
            </span>
          </div>
          <h1 className="text-3xl sm:text-5xl font-black tracking-tight text-slate-950">
            Audit Ledger
          </h1>
          <p className="mt-2 max-w-2xl text-sm sm:text-base text-slate-700 font-medium">
            Immutable, sequential cryptographic record of digital lending underwriting conformance proofs, block hashes, and gate decisions.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            type="button"
            disabled={resetting}
            onClick={handleReset}
            className="inline-flex items-center gap-1.5 bg-white px-3.5 py-2.5 text-xs font-black text-rose-700 border border-rose-300 rounded-lg shadow-2xs hover:bg-rose-50 transition-colors"
          >
            <RotateCcw size={13} className={resetting ? 'animate-spin' : ''} />
            <span>{resetting ? 'Resetting...' : 'Reset & Seed DB'}</span>
          </button>

          <button 
            onClick={() => void load()} 
            className="inline-flex items-center gap-2 bg-white px-4 py-2.5 text-xs font-black text-slate-800 border-2 border-slate-300 rounded-lg shadow-2xs hover:bg-slate-50 transition-colors"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin text-indigo-600' : ''}/> Refresh Ledger
          </button>
        </div>
      </div>

      {notice && (
        <div className="mb-5 bg-emerald-100 border border-emerald-300 px-4 py-3 rounded-xl text-emerald-950 text-xs font-bold shadow-xs animate-in fade-in">
          ✓ {notice}
        </div>
      )}

      {/* Compliance / Partner LSP Ledger Banner - clean heading without icon */}
      <div className="mb-6 flex flex-wrap items-start gap-4 rounded-xl border-2 border-indigo-300 bg-indigo-50 p-5 text-indigo-950 shadow-xs">
        <div className="flex-1">
          <h2 className="text-sm font-black text-indigo-950">
            Conformance Ledger for Partner LSP: Quick FinCorp Pvt Ltd
          </h2>
          <p className="mt-1 text-xs leading-relaxed text-indigo-900 font-medium">
            This ledger maintains immutable cryptographic decision records from Partner LSP Quick FinCorp Pvt Ltd in compliance with RBI Digital Lending Directions. Every credit decision is anchored into a continuous SHA-256 hash chain without exposing borrower personal identity (PII) or proprietary scoring weights.
          </p>
        </div>
        <div className="font-mono text-[10px] font-black uppercase tracking-wider bg-white px-2.5 py-1 rounded border border-indigo-300 text-indigo-900">
          Append-Only Ledger
        </div>
      </div>

      {error && (
        <div role="alert" className="mb-5 flex gap-3 border-2 border-rose-300 bg-rose-50 p-4 rounded-xl text-rose-950 text-xs font-semibold">
          <CircleAlert size={18} className="shrink-0 text-rose-600"/>
          <div>
            <p className="font-bold">Ledger Connection Notice</p>
            <p className="mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Ledger Table */}
      <section className="bg-white rounded-xl border-2 border-slate-300 shadow-sm overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b-2 border-slate-200 px-6 py-4 bg-slate-100">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-wider text-slate-600 font-black">Audit Trail</p>
            <h2 className="mt-0.5 text-lg font-black text-slate-950">
              Ledger Blocks <span className="font-mono text-xs font-bold text-slate-600">({entries.length} recorded)</span>
            </h2>
          </div>
        </div>

        {entries.length ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[960px] text-left text-xs">
              <thead className="bg-slate-100 text-[10px] uppercase tracking-wider text-slate-700 border-b-2 border-slate-300 font-black">
                <tr>
                  <th className="px-5 py-3.5">
                    Seq <InfoTip label="Sequence number" text="Sequential block height in the append-only ledger." />
                  </th>
                  <th className="px-4 py-3.5">
                    Decision ID <InfoTip label="Decision ID" text="Loan decision identifier generated at underwriting." />
                  </th>
                  <th className="px-4 py-3.5">
                    Status <InfoTip label="Status" text="Cryptographic verification status." />
                  </th>
                  <th className="px-4 py-3.5">
                    Reason <InfoTip label="Reason" text="Verification outcome or failure step explanation." />
                  </th>
                  {/* Hash Columns ordered: Proof Hash, Block Hash, Previous Block Hash */}
                  <th className="px-4 py-3.5">
                    Proof Hash <InfoTip label="Proof Hash" text="Fixed-length SHA-256 fingerprint of the Zero-Knowledge proof bytes." />
                  </th>
                  <th className="px-4 py-3.5">
                    Block Hash <InfoTip label="Block Hash" text="Cryptographic SHA-256 digest of this ledger block." />
                  </th>
                  <th className="px-4 py-3.5">
                    Previous Block Hash <InfoTip label="Previous Block Hash" text="Hash pointer linking to the prior sequential ledger entry." />
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 bg-white font-mono">
                {entries.map((e, i) => (
                  <tr key={`${e.seq}-${e.decision_id}-${i}`} className="hover:bg-slate-100 transition-colors">
                    <td className="px-5 py-3.5 font-black text-slate-950">#{e.seq}</td>
                    <td className="px-4 py-3.5 text-slate-900 font-bold">{e.decision_id}</td>
                    <td className="px-4 py-3.5 font-sans"><StatusPill status={e.status}/></td>
                    <td className="px-4 py-3.5 font-sans text-slate-700 font-medium">{e.reason || '—'}</td>
                    <td className="max-w-[170px] truncate px-4 py-3.5 text-purple-700 font-semibold" title={e.proof_hash || undefined}>
                      {e.proof_hash ? `${e.proof_hash.slice(0, 16)}…` : '—'}
                    </td>
                    <td className="max-w-[170px] truncate px-4 py-3.5 text-slate-950 font-black" title={e.row_hash || undefined}>
                      {e.row_hash ? `${e.row_hash.slice(0, 16)}…` : '—'}
                    </td>
                    <td className="max-w-[170px] truncate px-4 py-3.5 text-slate-500 font-medium" title={e.prev_hash || undefined}>
                      {e.prev_hash ? `${e.prev_hash.slice(0, 16)}…` : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="px-6 py-14 text-center">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-600 border border-slate-300">
              <CheckCheck size={22}/>
            </div>
            <h3 className="mt-4 font-black text-slate-900">{loading ? 'Loading ledger blocks…' : 'No audit records in session'}</h3>
            <p className="mx-auto mt-2 max-w-md text-xs text-slate-600 font-medium">
              Records will appear when underwriting applications are processed.
            </p>
            <a href="/" className="mt-4 inline-flex items-center gap-1 text-xs font-bold text-indigo-700 hover:text-indigo-900">
              Return to Lender Dashboard <ArrowUpRight size={13}/>
            </a>
          </div>
        )}
      </section>
    </main>
  );
}
