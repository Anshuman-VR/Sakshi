import { useState, useMemo } from 'react';
import { 
  CheckCircle2, XCircle, ArrowRight, Shield, 
  Sparkles, CreditCard, Clock, UserCheck, 
  ChevronRight
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { calculateEmi } from '../lib/loanEstimate';
import { submitLoanApplication, type ApplyLoanResponse } from '../api/client';

const money = (n: number) => 
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n);

interface PersonaPreset {
  id: string;
  name: string;
  role: string;
  pan: string;
  phone: string;
  bureau: number;
  income: number;
  foir: number;
  amount: number;
  tenure: number;
  expected: 'APPROVED' | 'REJECTED';
  tag: string;
}

const PRESETS: PersonaPreset[] = [
  {
    id: 'priya',
    name: 'Priya Sharma',
    role: 'Senior Software Engineer',
    pan: 'BNZPS1042K',
    phone: '+91 98201 44821',
    bureau: 758,
    income: 95000,
    foir: 28,
    amount: 150000,
    tenure: 36,
    expected: 'APPROVED',
    tag: 'Salaried Tech'
  },
  {
    id: 'rahul',
    name: 'Rahul Verma',
    role: 'Logistics Executive',
    pan: 'AXRPV8841M',
    phone: '+91 97112 55290',
    bureau: 542,
    income: 32000,
    foir: 68,
    amount: 200000,
    tenure: 36,
    expected: 'REJECTED',
    tag: 'Contract / Gig'
  },
  {
    id: 'amit',
    name: 'Amit Patel',
    role: 'Retail Store Owner',
    pan: 'CPZPA3391J',
    phone: '+91 99042 18834',
    bureau: 672,
    income: 52000,
    foir: 44,
    amount: 80000,
    tenure: 24,
    expected: 'APPROVED',
    tag: 'Self-Employed'
  }
];

export function BorrowerPortal() {
  const [selectedPersona, setSelectedPersona] = useState<string>('priya');
  const [name, setName] = useState<string>('Priya Sharma');
  const [phone, setPhone] = useState<string>('+91 98201 44821');
  const [pan, setPan] = useState<string>('BNZPS1042K');
  const [amount, setAmount] = useState<number>(150000);
  const [tenure, setTenure] = useState<number>(36);
  const [income, setIncome] = useState<number>(95000);
  const [foir, setFoir] = useState<number>(28);
  const [bureauScore, setBureauScore] = useState<number>(758);
  const [consent, setConsent] = useState<boolean>(true);

  // Submission state
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [stepLabel, setStepLabel] = useState<string>('');
  const [result, setResult] = useState<ApplyLoanResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const emi = useMemo(() => calculateEmi(amount, tenure), [amount, tenure]);

  const handleSelectPreset = (p: PersonaPreset) => {
    setSelectedPersona(p.id);
    setName(p.name);
    setPhone(p.phone);
    setPan(p.pan);
    setAmount(p.amount);
    setTenure(p.tenure);
    setIncome(p.income);
    setFoir(p.foir);
    setBureauScore(p.bureau);
    setResult(null);
    setErrorMsg(null);
  };

  const handleSubmitApplication = async () => {
    if (!consent) return;
    setSubmitting(true);
    setResult(null);
    setErrorMsg(null);

    try {
      setStepLabel('Verifying identity & credit score...');
      await new Promise(r => setTimeout(r, 400));
      
      setStepLabel('Evaluating underwriting criteria...');
      await new Promise(r => setTimeout(r, 450));

      const features: Record<string, number> = {
        bureau_score: bureauScore,
        monthly_income: income,
        foir: foir / 100.0,
        loan_tenure_months: tenure,
        num_active_loans: selectedPersona === 'rahul' ? 5.0 : 1.0,
        num_enquiries_6m: selectedPersona === 'rahul' ? 4.0 : 0.0,
        bank_account_age_months: selectedPersona === 'rahul' ? 22.0 : 84.0,
        loan_amount_requested: amount,
        behaviour_idx: selectedPersona === 'rahul' ? 0.88 : 0.18,
        employment_type: selectedPersona === 'rahul' ? 1.0 : 0.0,
      };

      const resp = await submitLoanApplication({
        persona: selectedPersona,
        features: features,
      });

      setStepLabel('Finalizing sanction details...');
      await new Promise(r => setTimeout(r, 300));
      setResult(resp);
    } catch (err: any) {
      console.error('Submission failed', err);
      setErrorMsg(err?.response?.data?.detail || err?.message || 'Could not process application at this moment.');
    } finally {
      setSubmitting(false);
      setStepLabel('');
    }
  };

  return (
    <main className="mx-auto w-[calc(100%-32px)] md:w-[calc(100%-48px)] xl:w-[calc(100%-64px)] max-w-5xl py-8 sm:py-12">
      {/* Brand Header */}
      <div className="text-center max-w-2xl mx-auto mb-10">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200 mb-3 shadow-xs">
          <Sparkles size={14} className="text-emerald-600" /> Instant Digital Loan
        </div>
        <h1 className="text-3xl sm:text-5xl font-extrabold text-slate-900 tracking-tight">
          Personal Credit in Minutes
        </h1>
        <p className="mt-2 text-sm sm:text-base text-slate-600">
          Fast, paperless personal loans with direct disbursal to your bank account.
        </p>

        {/* Value Props */}
        <div className="mt-5 flex flex-wrap items-center justify-center gap-4 text-xs font-medium text-slate-600">
          <span className="flex items-center gap-1.5"><Shield size={14} className="text-emerald-600" /> 100% Paperless</span>
          <span>•</span>
          <span className="flex items-center gap-1.5"><Clock size={14} className="text-indigo-600" /> Instant Sanction</span>
          <span>•</span>
          <span className="flex items-center gap-1.5"><CreditCard size={14} className="text-blue-600" /> Transparent 11.5% APR</span>
        </div>
      </div>

      {/* Preset Applicant Selector (Demo Helper) */}
      <div className="mb-8 bg-slate-100/70 p-4 rounded-2xl border border-slate-200/80">
        <div className="flex items-center justify-between mb-3 px-1">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-600 flex items-center gap-1.5">
            <UserCheck size={14} className="text-indigo-600" /> Quick-Fill Demo Profiles:
          </span>
          <span className="text-[11px] text-slate-500">Pick an applicant to test loan outcomes</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {PRESETS.map((p) => {
            const isSelected = selectedPersona === p.id;
            return (
              <button
                key={p.id}
                type="button"
                onClick={() => handleSelectPreset(p)}
                className={`p-3 rounded-xl border text-left transition-all ${
                  isSelected 
                    ? 'border-indigo-600 bg-white shadow-sm ring-2 ring-indigo-600/20' 
                    : 'border-slate-200 bg-white/60 hover:bg-white hover:border-slate-300'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-900 text-sm">{p.name}</span>
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                    p.expected === 'APPROVED' ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'
                  }`}>
                    {p.tag}
                  </span>
                </div>
                <div className="mt-1 text-xs text-slate-500 font-medium">{p.role}</div>
                <div className="mt-2 text-[11px] text-slate-600 font-mono flex items-center justify-between pt-1 border-t border-slate-100">
                  <span>₹{p.income.toLocaleString('en-IN')}/mo</span>
                  <span className={p.expected === 'APPROVED' ? 'text-emerald-700 font-semibold' : 'text-rose-700 font-semibold'}>
                    Will {p.expected}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Loan Application Card */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden mb-8">
        <div className="p-6 sm:p-8 space-y-8">
          
          {/* Section 1: Loan Configuration */}
          <div>
            <h2 className="text-base font-bold text-slate-900 mb-4 flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-indigo-50 text-indigo-700 text-xs flex items-center justify-center font-bold">1</span>
              Configure Desired Loan
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 p-6 rounded-xl bg-slate-50 border border-slate-100">
              {/* Amount */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label htmlFor="loan-amount-slider" className="text-xs font-semibold text-slate-700">Loan Amount</label>
                  <span className="text-lg font-bold text-slate-900 font-mono">{money(amount)}</span>
                </div>
                <input 
                  id="loan-amount-slider"
                  type="range" 
                  min={50000} 
                  max={500000} 
                  step={10000} 
                  value={amount} 
                  onChange={(e) => setAmount(Number(e.target.value))}
                  className="w-full accent-indigo-600 cursor-pointer h-2 bg-slate-200 rounded-lg"
                />
                <div className="flex justify-between text-[11px] text-slate-400 mt-1 font-mono">
                  <span>₹50,000</span>
                  <span>₹5,00,000</span>
                </div>
                
                {/* Quick Pills */}
                <div className="mt-3 flex gap-2">
                  {[50000, 100000, 150000, 250000].map((amt) => (
                    <button
                      key={amt}
                      type="button"
                      onClick={() => setAmount(amt)}
                      className={`text-[11px] font-semibold px-2.5 py-1 rounded-md border transition-colors ${
                        amount === amt 
                          ? 'bg-indigo-600 text-white border-indigo-600' 
                          : 'bg-white text-slate-700 border-slate-200 hover:border-slate-300'
                      }`}
                    >
                      {money(amt)}
                    </button>
                  ))}
                </div>
              </div>

              {/* Tenure */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-semibold text-slate-700">Repayment Period</label>
                  <span className="text-lg font-bold text-slate-900">{tenure} Months</span>
                </div>
                <div className="grid grid-cols-5 gap-1.5 mt-2">
                  {[12, 24, 36, 48, 60].map((m) => (
                    <button
                      key={m}
                      type="button"
                      onClick={() => setTenure(m)}
                      className={`py-2 text-xs font-bold rounded-lg border transition-all ${
                        tenure === m
                          ? 'bg-indigo-600 text-white border-indigo-600 shadow-sm'
                          : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-100'
                      }`}
                    >
                      {m}M
                    </button>
                  ))}
                </div>

                {/* Live Monthly EMI Banner */}
                <div className="mt-4 p-3 rounded-lg bg-indigo-50/70 border border-indigo-100 flex items-center justify-between">
                  <div>
                    <span className="text-[11px] text-indigo-900/70 block font-medium">Estimated Monthly Installment</span>
                    <span className="text-base font-extrabold text-indigo-950 font-mono">{money(emi)} / mo</span>
                  </div>
                  <span className="text-xs font-semibold text-indigo-700 bg-white px-2 py-1 rounded border border-indigo-200">
                    @ 11.5% APR
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Section 2: Personal Details */}
          <div>
            <h2 className="text-base font-bold text-slate-900 mb-4 flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-indigo-50 text-indigo-700 text-xs flex items-center justify-center font-bold">2</span>
              Applicant Profile
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Full Legal Name</label>
                <input 
                  type="text" 
                  value={name} 
                  onChange={(e) => setName(e.target.value)}
                  className="w-full text-sm font-medium px-3.5 py-2.5 rounded-lg border border-slate-200 focus:outline-indigo-600"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Mobile Number</label>
                <input 
                  type="text" 
                  value={phone} 
                  onChange={(e) => setPhone(e.target.value)}
                  className="w-full text-sm font-medium px-3.5 py-2.5 rounded-lg border border-slate-200 focus:outline-indigo-600 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">PAN Card Number</label>
                <input 
                  type="text" 
                  value={pan} 
                  onChange={(e) => setPan(e.target.value)}
                  className="w-full text-sm font-medium px-3.5 py-2.5 rounded-lg border border-slate-200 focus:outline-indigo-600 font-mono uppercase"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Monthly In-Hand Salary</label>
                <div className="relative">
                  <span className="absolute left-3 top-2.5 text-slate-400 text-sm font-mono">₹</span>
                  <input 
                    type="number" 
                    value={income} 
                    onChange={(e) => setIncome(Number(e.target.value))}
                    className="w-full text-sm font-medium pl-7 pr-3.5 py-2.5 rounded-lg border border-slate-200 focus:outline-indigo-600 font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Existing Monthly Loan EMIs (%)</label>
                <input 
                  type="number" 
                  value={foir} 
                  onChange={(e) => setFoir(Number(e.target.value))}
                  className="w-full text-sm font-medium px-3.5 py-2.5 rounded-lg border border-slate-200 focus:outline-indigo-600 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Credit Score (Bureau)</label>
                <input 
                  type="number" 
                  value={bureauScore} 
                  onChange={(e) => setBureauScore(Number(e.target.value))}
                  className="w-full text-sm font-medium px-3.5 py-2.5 rounded-lg border border-slate-200 focus:outline-indigo-600 font-mono"
                />
              </div>
            </div>
          </div>

          {/* Section 3: Standard Borrower Consent */}
          <div className="pt-2 border-t border-slate-100">
            <label className="flex items-start gap-3 cursor-pointer select-none">
              <input 
                type="checkbox" 
                checked={consent} 
                onChange={(e) => setConsent(e.target.checked)}
                className="mt-1 h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
              />
              <span className="text-xs text-slate-600 leading-relaxed">
                I hereby declare that the information provided is accurate and authorize the lending partner to verify my credit profile to process this loan application in accordance with terms and conditions.
              </span>
            </label>
          </div>

          {/* Submission Button & Feedback */}
          <div>
            {errorMsg && (
              <div className="mb-4 p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
                <XCircle size={16} className="text-rose-600 shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}

            <button
              type="button"
              disabled={submitting || !consent}
              onClick={handleSubmitApplication}
              className={`w-full py-3.5 px-6 rounded-xl font-bold text-sm shadow-sm flex items-center justify-center gap-2 transition-all ${
                submitting || !consent
                  ? 'bg-slate-200 text-slate-400 cursor-not-allowed'
                  : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-indigo-600/20 shadow-md hover:-translate-y-0.5'
              }`}
            >
              {submitting ? (
                <>
                  <span className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin"></span>
                  <span>{stepLabel || 'Processing Application...'}</span>
                </>
              ) : (
                <>
                  <span>Check Eligibility & Get Loan Offer</span>
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Result Card (Appears after submission) */}
      {result && (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-300">
          {result.status === 'VERIFIED' && result.decision === 1 ? (
            /* APPROVAL SCREEN */
            <div className="bg-gradient-to-b from-emerald-50/50 to-white rounded-2xl border-2 border-emerald-500 shadow-md p-6 sm:p-8">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-emerald-100">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-xl bg-emerald-600 text-white flex items-center justify-center shadow-sm">
                    <CheckCircle2 size={28} />
                  </div>
                  <div>
                    <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-800 bg-emerald-100 px-2 py-0.5 rounded-full inline-block mb-1">
                      Loan Offer Approved
                    </span>
                    <h3 className="text-2xl font-extrabold text-slate-900">
                      Congratulations, {name.split(' ')[0]}!
                    </h3>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-xs text-slate-500 block">Sanctioned Amount</span>
                  <span className="text-2xl sm:text-3xl font-extrabold text-emerald-700 font-mono">
                    {money(amount)}
                  </span>
                </div>
              </div>

              {/* Sanction Details Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 py-6 border-b border-slate-100 text-xs">
                <div>
                  <span className="text-slate-400 block mb-0.5">Monthly EMI</span>
                  <strong className="text-slate-900 text-sm font-mono">{money(emi)}</strong>
                </div>
                <div>
                  <span className="text-slate-400 block mb-0.5">Tenure</span>
                  <strong className="text-slate-900 text-sm">{tenure} Months</strong>
                </div>
                <div>
                  <span className="text-slate-400 block mb-0.5">Interest Rate</span>
                  <strong className="text-slate-900 text-sm">11.5% p.a. Fixed</strong>
                </div>
                <div>
                  <span className="text-slate-400 block mb-0.5">Application ID</span>
                  <strong className="text-slate-900 font-mono text-[11px]">{result.decision_id}</strong>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="pt-6 flex flex-col sm:flex-row items-center justify-between gap-4">
                <Link
                  to={`/receipt/${encodeURIComponent(result.decision_id)}`}
                  className="text-xs font-semibold text-slate-600 hover:text-slate-900 flex items-center gap-1"
                >
                  View Sanction Letter & Terms <ChevronRight size={14} />
                </Link>

                <div className="flex items-center gap-3 w-full sm:w-auto">
                  <button
                    type="button"
                    onClick={() => alert('Proceeding to NetBanking e-Mandate setup for direct disbursal.')}
                    className="w-full sm:w-auto px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl shadow-sm transition-colors"
                  >
                    Select Bank Account & Disburse
                  </button>
                </div>
              </div>
            </div>
          ) : (
            /* REJECTION / POLICY HOLD SCREEN */
            <div className="bg-white rounded-2xl border-2 border-slate-300 shadow-sm p-6 sm:p-8">
              <div className="flex items-start gap-4 mb-4">
                <div className="w-10 h-10 rounded-xl bg-slate-100 text-slate-700 flex items-center justify-center shrink-0">
                  <XCircle size={22} className="text-rose-600" />
                </div>
                <div>
                  <span className="text-[11px] font-bold uppercase tracking-wider text-rose-800 bg-rose-50 px-2 py-0.5 rounded-full inline-block mb-1">
                    Application Under Review
                  </span>
                  <h3 className="text-xl font-bold text-slate-900">
                    We Cannot Approve This Loan Offer Right Now
                  </h3>
                  <p className="mt-1 text-xs text-slate-600 leading-relaxed max-w-xl">
                    Thank you for applying with us, {name.split(' ')[0]}. Based on the credit policy guidelines regarding credit bureau obligations and debt-to-income limits, your application cannot be approved at this time.
                  </p>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-1 font-mono text-slate-600 mb-6">
                <div>Reference ID: <strong>{result.decision_id}</strong></div>
                <div>Status: <strong className="text-rose-700">Policy Criteria Not Met</strong></div>
              </div>

              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-500">You may re-apply after 90 days.</span>
                <Link
                  to={`/receipt/${encodeURIComponent(result.decision_id)}`}
                  className="font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1"
                >
                  View Application Details <ChevronRight size={14} />
                </Link>
              </div>
            </div>
          )}
        </div>
      )}
    </main>
  );
}
