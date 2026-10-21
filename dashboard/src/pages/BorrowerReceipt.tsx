import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, CheckCircle2, CircleAlert, FileCheck2, Printer, XCircle, Landmark } from 'lucide-react';
import { fetchDecision } from '../api/client';
import type { DecisionRecord } from '../api/types';

const ist = (v?: string | null) => { 
  if (!v) return '—'; 
  const d = new Date(v); 
  return Number.isNaN(d.getTime()) ? v : new Intl.DateTimeFormat('en-IN', { dateStyle:'long', timeStyle:'medium', timeZone:'Asia/Kolkata' }).format(d)+' IST'; 
};

const money = (n: number) => 
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n);

export function BorrowerReceipt() {
  const { id = '' } = useParams(); 
  const [record, setRecord] = useState<DecisionRecord | null>(null); 
  const [error, setError] = useState(''); 
  const [loading, setLoading] = useState(true);

  useEffect(() => { 
    let alive = true; 
    fetchDecision(id)
      .then(r => { if (alive) setRecord(r); })
      .catch(() => { if (alive) setError('Could not load sanction record for this reference ID.'); })
      .finally(() => { if (alive) setLoading(false); }); 
    return () => { alive = false; }; 
  }, [id]);

  const verified = record?.status === 'VERIFIED';
  const approved = record?.decision === 1;
  const customer = record?.customer_info;

  const loanAmount = customer?.loan_amount || 150000;
  const tenure = customer?.tenure || 36;
  const monthlyRate = 11.5 / (12 * 100);
  const emi = Math.round((loanAmount * monthlyRate * Math.pow(1 + monthlyRate, tenure)) / (Math.pow(1 + monthlyRate, tenure) - 1));

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 sm:px-7 sm:py-12">
      <div className="no-print mb-6 flex items-center justify-between">
        <Link to="/borrower" className="inline-flex items-center gap-2 text-xs font-bold text-slate-600 hover:text-slate-900">
          <ArrowLeft size={14}/> Back to QuickLoan Portal
        </Link>
        <button 
          onClick={() => window.print()} 
          className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-slate-900 text-white rounded-lg text-xs font-semibold hover:bg-slate-800 transition-colors shadow-sm"
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
                Official Digital Loan Sanction Letter
              </span>
              <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
                {approved && verified ? 'Loan Sanction Authorized' : 'Application Decision Record'}
              </h1>
              <p className="mt-1 text-xs sm:text-sm text-slate-300">
                Lender: <strong>Meridian Digital</strong> · Loan Service Provider: <strong>Quick FinCorp Pvt Ltd</strong>
              </p>
            </div>
            {verified && approved ? (
              <CheckCircle2 size={40} className="text-emerald-400 shrink-0" />
            ) : (
              <FileCheck2 size={40} className="text-slate-400 shrink-0" />
            )}
          </div>

          <div className="mt-6 flex flex-wrap items-center gap-3 pt-4 border-t border-white/10 text-xs font-mono">
            <span>Loan Reference ID: <strong>{id}</strong></span>
            <span>•</span>
            <span>Status: <strong className={verified ? 'text-emerald-400' : 'text-amber-400'}>{record?.status || 'VERIFYING'}</strong></span>
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
              Loading official sanction certificate...
            </div>
          ) : (
            <>
              {/* Prominent Sanction Announcement Banner */}
              {approved && verified ? (
                <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 flex items-start gap-3">
                  <CheckCircle2 size={22} className="text-emerald-600 mt-0.5 shrink-0" />
                  <div>
                    <h3 className="text-sm font-bold text-emerald-900">
                      Loan Sanction Authorized
                    </h3>
                    <p className="mt-0.5 text-xs text-emerald-800 leading-relaxed font-medium">
                      Your loan has been approved. The loan amount will be disbursed from the Lender within 24 hours directly to your designated bank account.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 flex items-start gap-3">
                  <XCircle size={22} className="text-rose-600 mt-0.5 shrink-0" />
                  <div>
                    <h3 className="text-sm font-bold text-rose-900">
                      Underwriting Policy Criteria Not Satisfied
                    </h3>
                    <p className="mt-0.5 text-xs text-rose-800 leading-relaxed font-medium">
                      The application did not fulfill required credit risk or debt-to-income benchmarks. Disbursal gate has held loan release.
                    </p>
                  </div>
                </div>
              )}

              {/* Customer Details Block */}
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
                  Borrower & Disbursal Information
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs p-4 rounded-xl bg-slate-50 border border-slate-200">
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-semibold">Applicant Name</span>
                    <strong className="text-slate-900 text-sm block mt-0.5">{customer?.name || 'Priya Sharma'}</strong>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-semibold">PAN Card Number</span>
                    <strong className="text-slate-900 font-mono text-sm block mt-0.5">{customer?.pan || 'BNZPS1042K'}</strong>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-semibold">Mobile Number</span>
                    <strong className="text-slate-900 font-mono block mt-0.5">{customer?.phone || '+91 98201 44821'}</strong>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-semibold">Disbursal Bank Account</span>
                    <strong className="text-slate-900 font-mono block mt-0.5 flex items-center gap-1.5">
                      <Landmark size={13} className="text-slate-500" />
                      {customer?.bank_account || '9182014482103'} (IFSC: {customer?.ifsc || 'HDFC0001234'})
                    </strong>
                  </div>
                </div>
              </div>

              {/* Sanction Loan Parameters */}
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
                  Approved Loan Terms
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div className="p-3 rounded-lg border border-slate-200 bg-white">
                    <span className="text-slate-400 block text-[10px] uppercase font-semibold">Sanctioned Principal</span>
                    <strong className="text-slate-900 text-base font-mono block mt-1">{money(loanAmount)}</strong>
                  </div>
                  <div className="p-3 rounded-lg border border-slate-200 bg-white">
                    <span className="text-slate-400 block text-[10px] uppercase font-semibold">Monthly Installment (EMI)</span>
                    <strong className="text-slate-900 text-base font-mono block mt-1">{money(emi)}</strong>
                  </div>
                  <div className="p-3 rounded-lg border border-slate-200 bg-white">
                    <span className="text-slate-400 block text-[10px] uppercase font-semibold">Tenure</span>
                    <strong className="text-slate-900 text-base block mt-1">{tenure} Months</strong>
                  </div>
                  <div className="p-3 rounded-lg border border-slate-200 bg-white">
                    <span className="text-slate-400 block text-[10px] uppercase font-semibold">Interest Rate</span>
                    <strong className="text-slate-900 text-base block mt-1">11.5% p.a.</strong>
                  </div>
                </div>
              </div>

              {/* Standard Terms and Conditions */}
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                  Key Terms & Conditions
                </h3>
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600 space-y-2 leading-relaxed">
                  <p>
                    <strong>1. Disbursal Timeline:</strong> The sanctioned loan amount will be electronically credited via NEFT/RTGS to the verified borrower bank account within 24 hours of digital sanction issuance.
                  </p>
                  <p>
                    <strong>2. Repayment Schedule:</strong> Monthly EMIs shall be automatically debited on the 5th of every calendar month through an approved NACH / e-Mandate facility.
                  </p>
                  <p>
                    <strong>3. Prepayment & Foreclosure:</strong> Zero foreclosure charges apply after completion of 6 regular consecutive monthly installments.
                  </p>
                  <p>
                    <strong>4. Default & Late Payment:</strong> In case of delayed EMI payment, penal interest at 2.0% per month shall accrue on the defaulted installment from the due date until full realization.
                  </p>
                  <p>
                    <strong>5. Regulatory Compliance:</strong> This facility is sanctioned by Meridian Digital through its authorized Loan Service Provider Quick FinCorp Pvt Ltd in full compliance with RBI Digital Lending Directions.
                  </p>
                </div>
              </div>

              {/* Metadata Footer */}
              <div className="pt-4 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3 text-[11px] text-slate-500 font-mono">
                <span>Sanction Timestamp: {ist(record?.verified_at || record?.received_at)}</span>
                <span className="text-slate-400">Policy: {record?.policy_id || 'pol_meridian_quickfin_v1'}</span>
              </div>
            </>
          )}
        </div>
      </article>
    </main>
  );
}
