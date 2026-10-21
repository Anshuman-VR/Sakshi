import { useState, useMemo } from 'react';
import { 
  CheckCircle2, XCircle, ArrowRight,
  ChevronRight, Clock
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
  bankAccount: string;
  ifsc: string;
  bureau: number;
  income: number;
  existingEmi: number;
  amount: number;
  tenure: number;
  activeLoans: number;
  enquiries6m: number;
  accountAgeMonths: number;
  employmentType: number; // 0=Salaried, 1=Self-employed
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
    bankAccount: '9182014482103',
    ifsc: 'HDFC0001234',
    bureau: 758,
    income: 95000,
    existingEmi: 15000,
    amount: 150000,
    tenure: 36,
    activeLoans: 1,
    enquiries6m: 0,
    accountAgeMonths: 84,
    employmentType: 0,
    expected: 'APPROVED',
    tag: 'Salaried Tech'
  },
  {
    id: 'rahul',
    name: 'Rahul Verma',
    role: 'Logistics Executive',
    pan: 'AXRPV8841M',
    phone: '+91 97112 55290',
    bankAccount: '8871125529041',
    ifsc: 'ICIC0000456',
    bureau: 542,
    income: 32000,
    existingEmi: 22000,
    amount: 200000,
    tenure: 36,
    activeLoans: 5,
    enquiries6m: 4,
    accountAgeMonths: 22,
    employmentType: 1,
    expected: 'REJECTED',
    tag: 'Contract / Gig'
  },
  {
    id: 'amit',
    name: 'Amit Patel',
    role: 'Retail Store Owner',
    pan: 'CPZPA3391J',
    phone: '+91 99042 18834',
    bankAccount: '5504218834092',
    ifsc: 'SBIN0002100',
    bureau: 672,
    income: 52000,
    existingEmi: 18000,
    amount: 80000,
    tenure: 24,
    activeLoans: 2,
    enquiries6m: 1,
    accountAgeMonths: 45,
    employmentType: 1,
    expected: 'APPROVED',
    tag: 'Self-Employed'
  }
];

export function BorrowerPortal() {
  const [selectedPersona, setSelectedPersona] = useState<string>('priya');
  const [name, setName] = useState<string>('Priya Sharma');
  const [phone, setPhone] = useState<string>('+91 98201 44821');
  const [pan, setPan] = useState<string>('BNZPS1042K');
  const [bankAccount, setBankAccount] = useState<string>('9182014482103');
  const [ifsc, setIfsc] = useState<string>('HDFC0001234');
  const [amount, setAmount] = useState<number>(150000);
  const [tenure, setTenure] = useState<number>(36);
  const [income, setIncome] = useState<number>(95000);
  const [existingEmi, setExistingEmi] = useState<number>(15000);
  const [bureauScore, setBureauScore] = useState<number>(758);
  const [activeLoans, setActiveLoans] = useState<number>(1);
  const [enquiries6m, setEnquiries6m] = useState<number>(0);
  const [accountAgeMonths, setAccountAgeMonths] = useState<number>(84);
  const [employmentType, setEmploymentType] = useState<number>(0);
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
    setBankAccount(p.bankAccount);
    setIfsc(p.ifsc);
    setAmount(p.amount);
    setTenure(p.tenure);
    setIncome(p.income);
    setExistingEmi(p.existingEmi);
    setBureauScore(p.bureau);
    setActiveLoans(p.activeLoans);
    setEnquiries6m(p.enquiries6m);
    setAccountAgeMonths(p.accountAgeMonths);
    setEmploymentType(p.employmentType);
    setResult(null);
    setErrorMsg(null);
  };

  const handleSubmitApplication = async () => {
    if (!consent) return;
    setSubmitting(true);
    setResult(null);
    setErrorMsg(null);

    try {
      setStepLabel('Verifying identity & CIBIL score...');
      await new Promise(r => setTimeout(r, 400));
      
      setStepLabel('Evaluating underwriting criteria...');
      await new Promise(r => setTimeout(r, 450));

      const calculatedFoir = Math.min(1.0, existingEmi / Math.max(1, income));

      const features: Record<string, number> = {
        bureau_score: bureauScore,
        monthly_income: income,
        foir: calculatedFoir,
        loan_tenure_months: tenure,
        num_active_loans: activeLoans,
        num_enquiries_6m: enquiries6m,
        bank_account_age_months: accountAgeMonths,
        loan_amount_requested: amount,
        behaviour_idx: selectedPersona === 'rahul' ? 0.88 : 0.18,
        employment_type: employmentType,
      };

      const customerInfo = {
        name,
        phone,
        pan,
        bank_account: bankAccount,
        ifsc,
        employment: employmentType === 0 ? 'Salaried' : 'Self-Employed',
        monthly_income: income,
        loan_amount: amount,
        tenure,
        bureau: bureauScore,
        existing_emi: existingEmi,
      };

      const resp = await submitLoanApplication({
        persona: selectedPersona,
        features: features,
        customer_info: customerInfo,
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
      {/* Brand Header without sloppy icons */}
      <div className="text-center max-w-2xl mx-auto mb-10">
        <div className="inline-flex items-center px-3.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-950 border border-emerald-300 mb-3 shadow-xs">
          QuickLoan · Quick FinCorp Pvt Ltd
        </div>
        <h1 className="text-3xl sm:text-5xl font-black text-slate-950 tracking-tight">
          Instant Personal Loan Application
        </h1>
        <p className="mt-2 text-sm sm:text-base text-slate-700 font-medium">
          Fast, paperless digital credit with transparent terms and direct disbursal within 24 hours.
        </p>

        {/* Value Props - clean text without icons */}
        <div className="mt-5 flex flex-wrap items-center justify-center gap-4 text-xs font-bold text-slate-700">
          <span>100% Paperless Process</span>
          <span className="text-slate-400">•</span>
          <span>Instant Decisioning</span>
          <span className="text-slate-400">•</span>
          <span>Transparent 11.5% APR Fixed</span>
        </div>
      </div>

      {/* Preset Applicant Selector (Demo Helper) */}
      <div className="mb-8 bg-slate-100 p-5 rounded-2xl border border-slate-300 shadow-xs">
        <div className="flex items-center justify-between mb-3 px-1">
          <span className="text-xs font-extrabold uppercase tracking-wider text-slate-800">
            Demo Applicant Profiles:
          </span>
          <span className="text-[11px] text-slate-600 font-semibold">Select a profile to populate verified credit records</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
          {PRESETS.map((p) => {
            const isSelected = selectedPersona === p.id;
            return (
              <button
                key={p.id}
                type="button"
                onClick={() => handleSelectPreset(p)}
                className={`p-4 rounded-xl border-2 text-left transition-all ${
                  isSelected 
                    ? 'border-indigo-600 bg-white shadow-md ring-2 ring-indigo-600/20' 
                    : 'border-slate-300 bg-white hover:border-slate-400 hover:shadow-xs'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-extrabold text-slate-950 text-sm">{p.name}</span>
                  <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded border ${
                    p.expected === 'APPROVED' ? 'bg-emerald-100 text-emerald-950 border-emerald-300' : 'bg-rose-100 text-rose-950 border-rose-300'
                  }`}>
                    {p.tag}
                  </span>
                </div>
                <div className="mt-1 text-xs text-slate-700 font-semibold">{p.role}</div>
                <div className="mt-2 text-xs text-slate-800 font-mono flex items-center justify-between pt-1.5 border-t border-slate-200">
                  <span className="font-bold">Req: {money(p.amount)}</span>
                  <span className={p.expected === 'APPROVED' ? 'text-emerald-800 font-bold' : 'text-rose-800 font-bold'}>
                    Will be {p.expected === 'APPROVED' ? 'Approved' : 'Rejected'}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Loan Application Card */}
      <div className="bg-white rounded-2xl border-2 border-slate-300 shadow-sm overflow-hidden mb-8">
        <div className="p-6 sm:p-8 space-y-8">
          
          {/* Section 1: Loan Configuration */}
          <div>
            <h2 className="text-base font-extrabold text-slate-950 mb-4 flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-indigo-100 text-indigo-900 text-xs flex items-center justify-center font-black border border-indigo-300">1</span>
              Configure Desired Loan
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 p-6 rounded-xl bg-slate-50 border border-slate-200">
              {/* Amount */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label htmlFor="loan-amount-slider" className="text-xs font-bold text-slate-800">Loan Amount</label>
                  <span className="text-xl font-black text-slate-950 font-mono">{money(amount)}</span>
                </div>
                <input 
                  id="loan-amount-slider"
                  type="range" 
                  min={50000} 
                  max={500000} 
                  step={10000} 
                  value={amount} 
                  onChange={(e) => setAmount(Number(e.target.value))}
                  className="w-full accent-indigo-600 cursor-pointer h-2.5 bg-slate-300 rounded-lg"
                />
                <div className="flex justify-between text-xs text-slate-600 mt-1 font-mono font-semibold">
                  <span>₹50,000</span>
                  <span>₹5,00,000</span>
                </div>

                {/* Quick Pills */}
                <div className="mt-3 flex gap-2">
                  {[50000, 80000, 150000, 200000, 300000].map((amt) => (
                    <button
                      key={amt}
                      type="button"
                      onClick={() => setAmount(amt)}
                      className={`text-xs font-bold px-3 py-1 rounded-lg border transition-colors ${
                        amount === amt 
                          ? 'bg-indigo-600 text-white border-indigo-600' 
                          : 'bg-white text-slate-800 border-slate-300 hover:border-slate-400 hover:bg-slate-50'
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
                  <label className="text-xs font-bold text-slate-800">Repayment Period</label>
                  <span className="text-lg font-black text-slate-950">{tenure} Months</span>
                </div>
                <div className="grid grid-cols-5 gap-1.5 mt-2">
                  {[12, 24, 36, 48, 60].map((m) => (
                    <button
                      key={m}
                      type="button"
                      onClick={() => setTenure(m)}
                      className={`py-2 text-xs font-black rounded-lg border transition-all ${
                        tenure === m
                          ? 'bg-indigo-600 text-white border-indigo-600 shadow-sm'
                          : 'bg-white text-slate-800 border-slate-300 hover:bg-slate-100 font-bold'
                      }`}
                    >
                      {m}M
                    </button>
                  ))}
                </div>

                {/* Live Monthly EMI Banner */}
                <div className="mt-4 p-3.5 rounded-xl bg-indigo-50 border border-indigo-200 flex items-center justify-between">
                  <div>
                    <span className="text-[11px] text-indigo-950 block font-bold">Estimated Monthly Installment</span>
                    <span className="text-lg font-black text-indigo-950 font-mono">{money(emi)} / mo</span>
                  </div>
                  <span className="text-xs font-extrabold text-indigo-950 bg-white px-2.5 py-1 rounded-md border border-indigo-300 shadow-2xs">
                    @ 11.5% APR
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Section 2: Personal & Financial Profile */}
          <div>
            <h2 className="text-base font-extrabold text-slate-950 mb-4 flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-indigo-100 text-indigo-900 text-xs flex items-center justify-center font-black border border-indigo-300">2</span>
              Applicant & Financial Details
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-bold text-slate-800 mb-1">Full Legal Name</label>
                <input 
                  type="text" 
                  value={name} 
                  onChange={(e) => setName(e.target.value)}
                  className="w-full text-sm font-semibold px-3.5 py-2.5 rounded-lg border-2 border-slate-300 focus:border-indigo-600 text-slate-950 bg-white"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-800 mb-1">Mobile Number</label>
                <input 
                  type="text" 
                  value={phone} 
                  onChange={(e) => setPhone(e.target.value)}
                  className="w-full text-sm font-semibold px-3.5 py-2.5 rounded-lg border-2 border-slate-300 focus:border-indigo-600 text-slate-950 font-mono bg-white"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-800 mb-1">PAN Card Number</label>
                <input 
                  type="text" 
                  value={pan} 
                  onChange={(e) => setPan(e.target.value.toUpperCase())}
                  className="w-full text-sm font-semibold px-3.5 py-2.5 rounded-lg border-2 border-slate-300 focus:border-indigo-600 text-slate-950 font-mono uppercase bg-white"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-800 mb-1">Monthly In-Hand Salary</label>
                <div className="relative">
                  <span className="absolute left-3 top-2.5 text-slate-500 text-sm font-bold font-mono">₹</span>
                  <input 
                    type="number" 
                    value={income} 
                    onChange={(e) => setIncome(Number(e.target.value))}
                    className="w-full text-sm font-semibold pl-7 pr-3.5 py-2.5 rounded-lg border-2 border-slate-300 focus:border-indigo-600 text-slate-950 font-mono bg-white"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-800 mb-1">Existing Monthly Loan EMIs (₹)</label>
                <div className="relative">
                  <span className="absolute left-3 top-2.5 text-slate-500 text-sm font-bold font-mono">₹</span>
                  <input 
                    type="number" 
                    value={existingEmi} 
                    onChange={(e) => setExistingEmi(Number(e.target.value))}
                    className="w-full text-sm font-semibold pl-7 pr-3.5 py-2.5 rounded-lg border-2 border-slate-300 focus:border-indigo-600 text-slate-950 font-mono bg-white"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-800 mb-1">Credit Score (CIBIL)</label>
                <input 
                  type="number" 
                  value={bureauScore} 
                  onChange={(e) => setBureauScore(Number(e.target.value))}
                  className="w-full text-sm font-semibold px-3.5 py-2.5 rounded-lg border-2 border-slate-300 focus:border-indigo-600 text-slate-950 font-mono bg-white"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-800 mb-1">Employment Type</label>
                <select 
                  value={employmentType} 
                  onChange={(e) => setEmploymentType(Number(e.target.value))}
                  className="w-full text-sm font-semibold px-3.5 py-2.5 rounded-lg border-2 border-slate-300 focus:border-indigo-600 bg-white text-slate-950"
                >
                  <option value={0}>Salaried Professional</option>
                  <option value={1}>Self-Employed / Business</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-800 mb-1">Active Loan Accounts</label>
                <input 
                  type="number" 
                  value={activeLoans} 
                  onChange={(e) => setActiveLoans(Number(e.target.value))}
                  className="w-full text-sm font-semibold px-3.5 py-2.5 rounded-lg border-2 border-slate-300 focus:border-indigo-600 text-slate-950 font-mono bg-white"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-800 mb-1">Recent Inquiries (Past 6M)</label>
                <input 
                  type="number" 
                  value={enquiries6m} 
                  onChange={(e) => setEnquiries6m(Number(e.target.value))}
                  className="w-full text-sm font-semibold px-3.5 py-2.5 rounded-lg border-2 border-slate-300 focus:border-indigo-600 text-slate-950 font-mono bg-white"
                />
              </div>
            </div>
          </div>

          {/* Section 3: Bank Disbursal Account Details */}
          <div>
            <h2 className="text-base font-extrabold text-slate-950 mb-4 flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-indigo-100 text-indigo-900 text-xs flex items-center justify-center font-black border border-indigo-300">3</span>
              Bank Account for Disbursal
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-5 rounded-xl bg-slate-50 border border-slate-200">
              <div>
                <label className="block text-xs font-bold text-slate-800 mb-1">
                  Bank Account Number
                </label>
                <input 
                  type="text" 
                  value={bankAccount} 
                  onChange={(e) => setBankAccount(e.target.value)}
                  className="w-full text-sm font-semibold px-3.5 py-2.5 rounded-lg border-2 border-slate-300 focus:border-indigo-600 text-slate-950 font-mono bg-white"
                  placeholder="e.g. 9182014482103"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-800 mb-1">
                  Bank IFSC Code
                </label>
                <input 
                  type="text" 
                  value={ifsc} 
                  onChange={(e) => setIfsc(e.target.value.toUpperCase())}
                  className="w-full text-sm font-semibold px-3.5 py-2.5 rounded-lg border-2 border-slate-300 focus:border-indigo-600 text-slate-950 font-mono uppercase bg-white"
                  placeholder="e.g. HDFC0001234"
                />
              </div>
            </div>
          </div>

          {/* Section 4: Standard Borrower Consent */}
          <div className="pt-2 border-t border-slate-200">
            <label className="flex items-start gap-3 cursor-pointer select-none">
              <input 
                type="checkbox" 
                checked={consent} 
                onChange={(e) => setConsent(e.target.checked)}
                className="mt-1 h-4 w-4 rounded border-slate-400 text-indigo-600 focus:ring-indigo-500"
              />
              <span className="text-xs text-slate-700 leading-relaxed font-medium">
                I hereby declare that the information provided is accurate and authorize Quick FinCorp Pvt Ltd and its partner lender Meridian Digital to evaluate my credit eligibility and process this loan application in accordance with terms and conditions.
              </span>
            </label>
          </div>

          {/* Submission Button & Feedback */}
          <div>
            {errorMsg && (
              <div className="mb-4 p-4 rounded-xl bg-rose-50 border-2 border-rose-300 text-rose-950 text-xs flex items-center gap-2 font-semibold">
                <XCircle size={16} className="text-rose-600 shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}

            <button
              type="button"
              disabled={submitting || !consent}
              onClick={handleSubmitApplication}
              className={`w-full py-4 px-6 rounded-xl font-black text-sm shadow-sm flex items-center justify-center gap-2 transition-all ${
                submitting || !consent
                  ? 'bg-slate-200 text-slate-400 cursor-not-allowed'
                  : 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-emerald-600/30 shadow-md hover:-translate-y-0.5'
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
            <div className="bg-gradient-to-b from-emerald-50 to-white rounded-2xl border-2 border-emerald-500 shadow-md p-6 sm:p-8">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-emerald-200">
                <div className="flex items-center gap-3.5">
                  <div className="w-12 h-12 rounded-xl bg-emerald-600 text-white flex items-center justify-center shadow-sm">
                    <CheckCircle2 size={28} />
                  </div>
                  <div>
                    <span className="text-[11px] font-black uppercase tracking-wider text-emerald-950 bg-emerald-200 px-2.5 py-0.5 rounded-full inline-block mb-1 border border-emerald-300">
                      Loan Offer Approved
                    </span>
                    <h3 className="text-2xl font-black text-slate-950">
                      Congratulations, {name.split(' ')[0]}!
                    </h3>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-xs text-slate-600 block font-bold">Sanctioned Amount</span>
                  <span className="text-2xl sm:text-3xl font-black text-emerald-800 font-mono">
                    {money(amount)}
                  </span>
                </div>
              </div>

              {/* Sanction Details Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 py-6 border-b border-slate-200 text-xs">
                <div>
                  <span className="text-slate-500 block mb-0.5 font-bold">Monthly EMI</span>
                  <strong className="text-slate-950 text-base font-mono font-black">{money(emi)}</strong>
                </div>
                <div>
                  <span className="text-slate-500 block mb-0.5 font-bold">Tenure</span>
                  <strong className="text-slate-950 text-base font-black">{tenure} Months</strong>
                </div>
                <div>
                  <span className="text-slate-500 block mb-0.5 font-bold">Interest Rate</span>
                  <strong className="text-slate-950 text-base font-black">11.5% p.a. Fixed</strong>
                </div>
                <div>
                  <span className="text-slate-500 block mb-0.5 font-bold">Application ID</span>
                  <strong className="text-slate-950 font-mono text-xs font-black">{result.decision_id}</strong>
                </div>
              </div>

              {/* Disbursal 24h Notice & View Sanction Letter */}
              <div className="pt-6 flex flex-col sm:flex-row items-center justify-between gap-4">
                <div className="flex items-center gap-2 text-emerald-950 bg-emerald-100 px-4 py-3 rounded-xl border border-emerald-300">
                  <Clock size={18} className="text-emerald-700 shrink-0" />
                  <span className="text-xs font-black">
                    Loan will be disbursed within 24 hours to your bank account ({bankAccount.slice(-4).padStart(bankAccount.length, '•')}).
                  </span>
                </div>

                <Link
                  to={`/receipt/${encodeURIComponent(result.decision_id)}`}
                  className="px-5 py-3 bg-slate-900 hover:bg-slate-800 text-white font-extrabold text-xs rounded-xl shadow-sm transition-colors flex items-center gap-1.5 shrink-0"
                >
                  View Sanction Letter & Terms <ChevronRight size={14} />
                </Link>
              </div>
            </div>
          ) : (
            /* REJECTION / POLICY HOLD SCREEN */
            <div className="bg-white rounded-2xl border-2 border-slate-400 shadow-sm p-6 sm:p-8">
              <div className="flex items-start gap-4 mb-4">
                <div className="w-10 h-10 rounded-xl bg-rose-100 text-rose-800 flex items-center justify-center shrink-0 border border-rose-300">
                  <XCircle size={22} className="text-rose-700" />
                </div>
                <div>
                  <span className="text-[11px] font-black uppercase tracking-wider text-rose-950 bg-rose-100 px-2.5 py-0.5 rounded-full inline-block mb-1 border border-rose-300">
                    Application Under Review
                  </span>
                  <h3 className="text-xl font-black text-slate-950">
                    We Cannot Approve This Loan Offer Right Now
                  </h3>
                  <p className="mt-1 text-xs text-slate-700 leading-relaxed max-w-xl font-medium">
                    Thank you for applying with us, {name.split(' ')[0]}. Based on the credit underwriting policy regarding credit bureau obligations, existing EMIs, and debt-to-income limits, your application cannot be approved at this time.
                  </p>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-slate-100 border border-slate-300 text-xs space-y-1 font-mono text-slate-800 mb-6">
                <div>Reference ID: <strong>{result.decision_id}</strong></div>
                <div>Status: <strong className="text-rose-700">Policy Criteria Not Met</strong></div>
              </div>

              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-600 font-semibold">You may re-apply after 90 days.</span>
                <Link
                  to={`/receipt/${encodeURIComponent(result.decision_id)}`}
                  className="font-bold text-indigo-700 hover:text-indigo-900 flex items-center gap-1"
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
