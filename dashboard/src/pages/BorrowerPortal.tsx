import { useState, useMemo } from 'react';
import { 
  ShieldCheck, Banknote, CheckCircle2, XCircle, ArrowRight, 
  Lock, RefreshCw, AlertTriangle, FileText
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { calculateEmi, calculateProposedFoir } from '../lib/loanEstimate';
import { submitLoanApplication, type ApplyLoanResponse } from '../api/client';

const money = (n: number) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n);

interface PersonaPreset {
  id: string;
  name: string;
  role: string;
  bureau: number;
  income: number;
  foir: number;
  amount: number;
  tenure: number;
  expected: 'APPROVED' | 'REJECTED';
  tag: string;
  tagColor: string;
}

const PRESETS: PersonaPreset[] = [
  {
    id: 'priya',
    name: 'Priya Sharma',
    role: 'Senior Software Engineer',
    bureau: 758,
    income: 95000,
    foir: 28,
    amount: 150000,
    tenure: 36,
    expected: 'APPROVED',
    tag: 'Prime Profile',
    tagColor: 'bg-emerald-50 text-emerald-700 border-emerald-200'
  },
  {
    id: 'rahul',
    name: 'Rahul Verma',
    role: 'Contract Gig Worker',
    bureau: 542,
    income: 32000,
    foir: 68,
    amount: 200000,
    tenure: 36,
    expected: 'REJECTED',
    tag: 'High Risk (Policy Hold)',
    tagColor: 'bg-rose-50 text-rose-700 border-rose-200'
  },
  {
    id: 'amit',
    name: 'Amit Patel',
    role: 'Store Manager',
    bureau: 672,
    income: 52000,
    foir: 44,
    amount: 80000,
    tenure: 24,
    expected: 'APPROVED',
    tag: 'Near-Prime Profile',
    tagColor: 'bg-blue-50 text-blue-700 border-blue-200'
  }
];

export function BorrowerPortal() {
  const [selectedPersona, setSelectedPersona] = useState<string>('priya');
  const [amount, setAmount] = useState<number>(150000);
  const [tenure, setTenure] = useState<number>(36);
  const [income, setIncome] = useState<number>(95000);
  const [foir, setFoir] = useState<number>(28);
  const [bureauScore, setBureauScore] = useState<number>(758);
  const [consent, setConsent] = useState<boolean>(true);

  // Submission & Pipeline state
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [result, setResult] = useState<ApplyLoanResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const emi = useMemo(() => calculateEmi(amount, tenure), [amount, tenure]);
  const proposedFoir = calculateProposedFoir(income, foir, emi);

  const handleSelectPreset = (p: PersonaPreset) => {
    setSelectedPersona(p.id);
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
    setCurrentStep(1);

    try {
      // Step 1: Feature commit
      await new Promise(r => setTimeout(r, 450));
      setCurrentStep(2);

      // Step 2: Prover sidecar invocation
      await new Promise(r => setTimeout(r, 650));
      setCurrentStep(3);

      // Step 3: Lender node verification
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

      setCurrentStep(4);
      await new Promise(r => setTimeout(r, 400));
      setResult(resp);
    } catch (err: any) {
      console.error('Submission failed', err);
      setErrorMsg(err?.response?.data?.detail || err?.message || 'Could not reach the lender application gateway.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="mx-auto w-[calc(100%-32px)] md:w-[calc(100%-48px)] xl:w-[calc(100%-64px)] max-w-[1600px] py-8 sm:py-10">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200 mb-2">
            <ShieldCheck size={14} /> RBI Digital Lending Directions 2025 Compliant
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
            Borrower Digital Lending Portal
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Submit your loan application. Underwriting policy is mathematically verified in zero knowledge before funds release.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-600 bg-white px-3 py-2 rounded-lg border border-slate-200 shadow-sm">
          <Lock size={14} className="text-emerald-600" />
          <span>DPDP Act: PII & Features stay in LSP Zone</span>
        </div>
      </div>

      {/* Preset Personas Picker */}
      <div className="mb-8">
        <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
          Select Demo Applicant Persona:
        </label>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {PRESETS.map((p) => {
            const isSelected = selectedPersona === p.id;
            return (
              <button
                key={p.id}
                type="button"
                onClick={() => handleSelectPreset(p)}
                className={`text-left p-4 rounded-xl border-2 transition-all flex flex-col justify-between ${
                  isSelected 
                    ? 'border-indigo-600 bg-indigo-50/40 shadow-sm' 
                    : 'border-slate-200 bg-white hover:border-slate-300'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-slate-900 text-sm">{p.name}</span>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${p.tagColor}`}>
                      {p.tag}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mb-3">{p.role}</p>
                </div>
                <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-600 border-t border-slate-100 pt-2 font-mono">
                  <span>CIBIL: <strong>{p.bureau}</strong></span>
                  <span>Salary: <strong>₹{p.income.toLocaleString('en-IN')}</strong></span>
                  <span>FOIR: <strong>{p.foir}%</strong></span>
                  <span className={p.expected === 'APPROVED' ? 'text-emerald-700 font-bold' : 'text-rose-700 font-bold'}>
                    Will {p.expected}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Grid: Application Form & Snapshot */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Form: Configure Application */}
        <section className="lg:col-span-7 bg-white rounded-2xl border border-slate-200 shadow-sm p-6 sm:p-8">
          <div className="flex items-center justify-between pb-5 border-b border-slate-100 mb-6">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Configure Loan Parameters</h2>
              <p className="text-xs text-slate-500 mt-0.5">Adjust inputs or test custom applicant scenarios</p>
            </div>
            <div className="h-10 w-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold">
              <Banknote size={20} />
            </div>
          </div>

          {/* Amount Slider */}
          <div className="mb-6">
            <div className="flex justify-between items-baseline mb-2">
              <label htmlFor="amount" className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Loan Amount Requested
              </label>
              <span className="text-2xl font-extrabold text-slate-900">{money(amount)}</span>
            </div>
            <input 
              id="amount"
              type="range"
              min={25000}
              max={500000}
              step={5000}
              value={amount}
              onChange={(e) => { setAmount(Number(e.target.value)); setSelectedPersona('custom'); }}
              className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
            />
            <div className="flex justify-between text-[11px] text-slate-400 font-mono mt-1">
              <span>₹25,000</span>
              <span>₹5,00,000</span>
            </div>
          </div>

          {/* Tenure Buttons */}
          <div className="mb-6">
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
              Repayment Tenure
            </label>
            <div className="grid grid-cols-4 gap-2">
              {[12, 24, 36, 48].map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => { setTenure(t); setSelectedPersona('custom'); }}
                  className={`py-2.5 rounded-lg text-xs font-bold border transition-colors ${
                    tenure === t 
                      ? 'bg-slate-900 text-white border-slate-900' 
                      : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  {t} Months
                </button>
              ))}
            </div>
          </div>

          {/* Income & Obligations */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
            <div>
              <label htmlFor="income" className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-1.5">
                Monthly Net Salary
              </label>
              <div className="relative">
                <span className="absolute left-3 top-2.5 text-slate-400 font-bold text-sm">₹</span>
                <input 
                  id="income"
                  type="number"
                  min={10000}
                  step={1000}
                  value={income}
                  onChange={(e) => { setIncome(Math.max(0, Number(e.target.value))); setSelectedPersona('custom'); }}
                  className="w-full pl-8 pr-3 py-2 text-sm font-semibold rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>

            <div>
              <label htmlFor="bureau" className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-1.5">
                CIBIL / Bureau Score
              </label>
              <input 
                id="bureau"
                type="number"
                min={300}
                max={900}
                value={bureauScore}
                onChange={(e) => { setBureauScore(Math.min(900, Math.max(300, Number(e.target.value)))); setSelectedPersona('custom'); }}
                className="w-full px-3 py-2 text-sm font-semibold rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>

          {/* Affordability Preview */}
          <div className="bg-slate-50 rounded-xl p-4 border border-slate-100 mb-6">
            <div className="flex justify-between items-center mb-1 text-xs">
              <span className="font-semibold text-slate-600">Affordability FOIR (Existing + New EMI)</span>
              <strong className="font-mono text-slate-900">{proposedFoir ? `${proposedFoir.toFixed(1)}%` : '--'}</strong>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden mt-2">
              <div 
                className={`h-full transition-all ${
                  (proposedFoir || 0) > 65 ? 'bg-rose-500' : 'bg-emerald-500'
                }`}
                style={{ width: `${Math.min(100, proposedFoir || 0)}%` }}
              />
            </div>
            <div className="flex justify-between text-[10px] text-slate-400 mt-1">
              <span>Policy Maximum: 65.0%</span>
              <span>{(proposedFoir || 0) > 65 ? '⚠️ Exceeds policy ceiling' : '✓ Within policy ceiling'}</span>
            </div>
          </div>

          {/* Consent Checkbox */}
          <div className="p-4 rounded-xl border border-slate-200 bg-white mb-6">
            <label className="flex items-start gap-3 cursor-pointer">
              <input 
                type="checkbox"
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
                className="mt-1 h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
              />
              <span className="text-xs text-slate-600 leading-relaxed">
                <strong className="text-slate-900 block font-semibold mb-0.5">
                  DPDP Act 2023 Digital Lending Consent
                </strong>
                I authorize computational contract conformance verification of my credit parameters against NBFC-42 Capital's approved underwriting policy. My unmasked financial features stay within the secure LSP enclave.
              </span>
            </label>
          </div>

          {/* Submit Action */}
          <button
            type="button"
            disabled={!consent || submitting}
            onClick={handleSubmitApplication}
            className={`w-full py-4 rounded-xl font-bold text-sm flex items-center justify-center gap-2 shadow-sm transition-all ${
              submitting 
                ? 'bg-slate-300 text-slate-500 cursor-not-allowed'
                : 'bg-indigo-600 text-white hover:bg-indigo-700 active:scale-[0.99]'
            }`}
          >
            {submitting ? (
              <>
                <RefreshCw size={16} className="animate-spin" />
                Executing Cryptographic Underwriting Pipeline...
              </>
            ) : (
              <>
                Verify Conformance & Submit Loan <ArrowRight size={16} />
              </>
            )}
          </button>
        </section>

        {/* Right Aside: Snapshot & Live Tracker */}
        <aside className="lg:col-span-5 space-y-6">
          {/* EMI Card */}
          <div className="bg-slate-900 text-white rounded-2xl p-6 sm:p-7 shadow-md">
            <span className="text-[11px] font-mono uppercase tracking-wider text-indigo-400 font-semibold block mb-1">
              Repayment Snapshot
            </span>
            <div className="text-4xl font-extrabold tracking-tight mt-2">
              {money(emi)}
              <span className="text-sm font-normal text-slate-400 ml-1.5">/ month</span>
            </div>
            <div className="grid grid-cols-2 gap-4 border-t border-slate-800 pt-4 mt-6 text-xs">
              <div>
                <span className="text-slate-400 block mb-0.5">Principal Loan</span>
                <strong className="text-sm font-bold">{money(amount)}</strong>
              </div>
              <div>
                <span className="text-slate-400 block mb-0.5">Tenure</span>
                <strong className="text-sm font-bold">{tenure} Months</strong>
              </div>
            </div>
            <p className="text-[10px] text-slate-400 mt-4 leading-relaxed">
              Standard 12.5% p.a. fixed rate illustration. Verified by Sakshi zero-knowledge gate before disbursement.
            </p>
          </div>

          {/* Stepper Progress when submitting */}
          {submitting && (
            <div className="bg-white rounded-2xl border border-indigo-200 shadow-sm p-6 animate-pulse">
              <h3 className="text-sm font-bold text-slate-900 mb-4 flex items-center gap-2">
                <RefreshCw size={15} className="animate-spin text-indigo-600" />
                Live Conformance Verification in Progress
              </h3>
              <div className="space-y-3.5 text-xs">
                <div className={`flex items-center gap-3 ${currentStep >= 1 ? 'text-emerald-700 font-bold' : 'text-slate-400'}`}>
                  <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] ${currentStep >= 1 ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100'}`}>1</div>
                  <span>DPDP Consent logged & Features Committed ($X$)</span>
                </div>
                <div className={`flex items-center gap-3 ${currentStep >= 2 ? 'text-indigo-700 font-bold' : 'text-slate-400'}`}>
                  <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] ${currentStep >= 2 ? 'bg-indigo-100 text-indigo-800' : 'bg-slate-100'}`}>2</div>
                  <span>LSP Prover sidecar generates inference proof</span>
                </div>
                <div className={`flex items-center gap-3 ${currentStep >= 3 ? 'text-purple-700 font-bold' : 'text-slate-400'}`}>
                  <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] ${currentStep >= 3 ? 'bg-purple-100 text-purple-800' : 'bg-slate-100'}`}>3</div>
                  <span>Lender Verifier Engine checks $V1$–$V9$ against policy</span>
                </div>
                <div className={`flex items-center gap-3 ${currentStep >= 4 ? 'text-blue-700 font-bold' : 'text-slate-400'}`}>
                  <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] ${currentStep >= 4 ? 'bg-blue-100 text-blue-800' : 'bg-slate-100'}`}>4</div>
                  <span>Immutable Hash-Chain Ledger appended</span>
                </div>
              </div>
            </div>
          )}

          {/* Result Card */}
          {result && (
            <div className={`rounded-2xl border p-6 shadow-md ${
              result.status === 'VERIFIED' && result.decision === 1
                ? 'bg-emerald-50/70 border-emerald-300'
                : 'bg-rose-50/70 border-rose-300'
            }`}>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  {result.status === 'VERIFIED' && result.decision === 1 ? (
                    <CheckCircle2 className="text-emerald-600" size={24} />
                  ) : (
                    <XCircle className="text-rose-600" size={24} />
                  )}
                  <div>
                    <h3 className="text-base font-extrabold text-slate-900">
                      {result.status === 'VERIFIED' && result.decision === 1
                        ? 'Loan Approved & Conformance Verified'
                        : result.status === 'VERIFIED'
                        ? 'Loan Rejected & Conformance Proven'
                        : 'Verification Failed (Disbursal Blocked)'}
                    </h3>
                    <p className="text-xs text-slate-500 font-mono">
                      Ref: {result.decision_id}
                    </p>
                  </div>
                </div>
              </div>

              <div className="space-y-2 text-xs bg-white/80 rounded-xl p-4 border border-slate-200/60 mb-5 font-mono">
                <div className="flex justify-between">
                  <span className="text-slate-500">Status:</span>
                  <strong className={result.status === 'VERIFIED' ? 'text-emerald-700' : 'text-rose-700'}>
                    {result.status} ({result.decision_label})
                  </strong>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Ledger Block:</span>
                  <span className="text-slate-800">Seq #{result.ledger_seq}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Policy ID:</span>
                  <span className="text-slate-800 truncate max-w-[180px]">{result.policy_id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Disbursal Action:</span>
                  <span className={result.status === 'VERIFIED' && result.decision === 1 ? 'text-emerald-600 font-bold' : 'text-slate-600'}>
                    {result.status === 'VERIFIED' && result.decision === 1 ? 'SIM-NEFT Transfer Permitted' : 'Disbursal Held (Fail-Closed)'}
                  </span>
                </div>
              </div>

              {/* Action Buttons to view receipt, lender, and ledger */}
              <div className="space-y-2">
                <Link
                  to={`/receipt/${result.decision_id}`}
                  className="w-full py-2.5 px-4 rounded-lg bg-slate-900 text-white font-bold text-xs flex items-center justify-center gap-1.5 hover:bg-slate-800 transition-colors"
                >
                  <FileText size={14} /> View Cryptographic Receipt
                </Link>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <Link
                    to="/"
                    className="py-2 px-3 rounded-lg bg-white border border-slate-200 font-semibold text-slate-700 hover:bg-slate-50 flex items-center justify-center gap-1"
                  >
                    Lender Portal <ArrowRight size={12} />
                  </Link>
                  <Link
                    to="/ledger"
                    className="py-2 px-3 rounded-lg bg-white border border-slate-200 font-semibold text-slate-700 hover:bg-slate-50 flex items-center justify-center gap-1"
                  >
                    Audit Ledger <ArrowRight size={12} />
                  </Link>
                </div>
              </div>
            </div>
          )}

          {errorMsg && (
            <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 text-xs text-rose-800 flex items-start gap-2">
              <AlertTriangle size={16} className="text-rose-600 shrink-0 mt-0.5" />
              <div>
                <strong className="block font-semibold mb-0.5">Submission Error</strong>
                <span>{errorMsg}</span>
              </div>
            </div>
          )}
        </aside>
      </div>
    </main>
  );
}
