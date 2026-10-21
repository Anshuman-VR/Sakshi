import { useState } from 'react';
import { 
  Play, ShieldAlert, CheckCircle2, XCircle, 
  Copy, Check, AlertTriangle, ShieldCheck, RotateCcw
} from 'lucide-react';
import { 
  submitLoanApplication, 
  resetDatabase, 
  type ApplyLoanResponse, 
  type VerificationStep, 
  type MismatchDetails 
} from '../api/client';

interface ScenarioDef {
  id: string;
  tamper?: string;
  persona: string;
  title: string;
  category: 'HONEST' | 'ATTACK';
  subtitle: string;
  description: string;
}

const SCENARIOS: ScenarioDef[] = [
  {
    id: 'honest-prime',
    persona: 'vikram',
    category: 'HONEST',
    title: '1. Honest Approval',
    subtitle: 'Prime (Vikram Malhotra)',
    description: 'Applicant qualifies under agreed cutoff (CIBIL 765, FOIR 26%). Quick FinCorp proves inference on agreed model. All 9 verifier checks pass, and Meridian Digital authorizes disbursal within 24 hours.',
  },
  {
    id: 'honest-subprime',
    persona: 'suresh',
    category: 'HONEST',
    title: '2. Honest Rejection',
    subtitle: 'Subprime (Suresh Nair)',
    description: 'Scorecard calculates high risk (CIBIL 538, FOIR 71%). Prover generates valid ZK proof of decision=0. Disbursal gate strictly holds funds (fail-closed).',
  },
  {
    id: 'tamper-model',
    persona: 'vikram',
    tamper: 'model',
    category: 'ATTACK',
    title: '3. Model Swap',
    subtitle: 'Unauthorized Model',
    description: 'LSP attempts to evaluate using an unapproved model weights file. Lender verifier checks model commitment C against approved registry and rejects the proof at Step V2.',
  },
  {
    id: 'tamper-threshold',
    persona: 'suresh',
    tamper: 'threshold',
    category: 'ATTACK',
    title: '4. Cutoff Creep',
    subtitle: 'Lowering Threshold',
    description: 'LSP attempts to pass a high-risk applicant by lowering cutoff threshold tau from 0.500 to 0.050. Caught immediately at Step V4 (Exact Decimal Match).',
  },
  {
    id: 'tamper-input',
    persona: 'vikram',
    tamper: 'input',
    category: 'ATTACK',
    title: '5. Feature Tamper',
    subtitle: 'Income / Bureau Spoofing',
    description: 'Features submitted to the verifier do not match the witness proven in ZK (X != X prime). Caught by the Input Binding adapter before fund release.',
  },
  {
    id: 'tamper-replay',
    persona: 'vikram',
    tamper: 'replay',
    category: 'ATTACK',
    title: '6. Replay Attack',
    subtitle: 'Re-submitting Used Proof',
    description: 'Attacker takes a valid proof from an earlier loan and re-submits it for a new application. Caught by SHA-256 uniqueness check at Step V6.',
  },
  {
    id: 'tamper-corrupt-zk',
    persona: 'vikram',
    tamper: 'invalid_zk',
    category: 'ATTACK',
    title: '7. Corrupt SNARK',
    subtitle: 'Forged Proof Bytes',
    description: 'Submitting malformed or invalid cryptographic polynomial bytes. Verifier fails at Step V8 with INVALID_PROOF.',
  },
];

export function DemoLab() {
  const [selectedId, setSelectedId] = useState<string>('honest-prime');
  const [executing, setExecuting] = useState<boolean>(false);
  const [activeStepIndex, setActiveStepIndex] = useState<number>(-1);
  const [response, setResponse] = useState<ApplyLoanResponse | null>(null);
  const [, setErrorMsg] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);
  const [resetting, setResetting] = useState<boolean>(false);

  const selectedScenario = SCENARIOS.find((s) => s.id === selectedId) || SCENARIOS[0];

  const handleRunScenario = async (scenarioToRun?: ScenarioDef) => {
    const sc = scenarioToRun || selectedScenario;
    setExecuting(true);
    setResponse(null);
    setErrorMsg(null);
    setActiveStepIndex(0);

    try {
      await new Promise((r) => setTimeout(r, 200));
      setActiveStepIndex(1);

      await new Promise((r) => setTimeout(r, 300));
      setActiveStepIndex(2);

      const res = await submitLoanApplication({
        persona: sc.persona,
        tamper: sc.tamper,
      });

      setActiveStepIndex(3);
      await new Promise((r) => setTimeout(r, 200));
      setActiveStepIndex(4);
      setResponse(res);
    } catch (err: any) {
      console.error(err);
      setErrorMsg(err?.response?.data?.detail || err?.message || 'Execution failed.');
    } finally {
      setExecuting(false);
    }
  };

  const handleResetDb = async () => {
    if (!window.confirm('Are you sure you want to clear current database records and re-seed baseline test data?')) {
      return;
    }
    setResetting(true);
    try {
      await resetDatabase();
      setResponse(null);
      setErrorMsg(null);
      setActiveStepIndex(-1);
    } catch (err) {
      console.error('Failed to reset DB:', err);
    } finally {
      setResetting(false);
    }
  };

  const copyProof = () => {
    if (!response?.proof) return;
    navigator.clipboard.writeText(response.proof);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const stepsList: VerificationStep[] = response?.steps_evaluated || [];
  const mismatch: MismatchDetails | null | undefined = response?.mismatch_details;

  return (
    <main className="mx-auto w-[calc(100%-32px)] md:w-[calc(100%-48px)] xl:w-[calc(100%-64px)] max-w-[1600px] py-7 sm:py-9">
      {/* Page Header */}
      <div className="mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold bg-indigo-50 text-indigo-800 border border-indigo-300 mb-2">
            Interactive Cryptographic Verifier Sandbox
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
            Zero-Knowledge Conformance & Tamper Lab
          </h1>
          <p className="mt-1 text-sm text-slate-600 max-w-3xl">
            Test real underwriting loan applications against the live verifier engine. Inspect Halo2 proofs, mathematical step assertions, and fail-closed disbursal gates for Meridian Digital and Quick FinCorp Pvt Ltd.
          </p>
        </div>

        <button
          type="button"
          onClick={handleResetDb}
          disabled={resetting}
          className="inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-bold text-slate-700 bg-white border border-slate-300 hover:bg-slate-100 hover:text-slate-900 transition-colors shadow-xs shrink-0 self-start md:self-center"
        >
          <RotateCcw size={14} className={resetting ? 'animate-spin text-indigo-600' : 'text-slate-500'} />
          <span>{resetting ? 'Resetting DB...' : 'Reset & Seed DB'}</span>
        </button>
      </div>

      {/* HORIZONTAL CARDS ROW FOR THE 7 SCENARIOS */}
      <div className="mb-7">
        <div className="flex items-center justify-between mb-3 px-1">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
            Select Test Scenario (7 Test Cases):
          </span>
          <span className="text-[11px] text-slate-500 font-medium">Click any card to inspect and run scenario workflow below</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 xl:grid-cols-7 gap-3">
          {SCENARIOS.map((sc) => {
            const isSelected = selectedId === sc.id;
            const isAttack = sc.category === 'ATTACK';
            return (
              <button
                key={sc.id}
                type="button"
                onClick={() => {
                  setSelectedId(sc.id);
                  setResponse(null);
                  setErrorMsg(null);
                }}
                className={`p-3.5 rounded-xl border text-left transition-all flex flex-col justify-between ${
                  isSelected
                    ? 'border-indigo-600 bg-white shadow-md ring-2 ring-indigo-600/30'
                    : 'border-slate-300 bg-white hover:border-slate-400 hover:bg-slate-50/70 shadow-2xs'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between gap-1 mb-1.5">
                    <span
                      className={`text-[9px] font-extrabold px-1.5 py-0.5 rounded border uppercase tracking-wider ${
                        isAttack
                          ? 'bg-rose-100 text-rose-800 border-rose-300'
                          : 'bg-emerald-100 text-emerald-800 border-emerald-300'
                      }`}
                    >
                      {sc.category}
                    </span>
                    <span className="text-[10px] text-slate-600 font-mono font-semibold capitalize">
                      {sc.persona}
                    </span>
                  </div>
                  <h3 className="font-extrabold text-slate-900 text-xs line-clamp-1 leading-snug">
                    {sc.title}
                  </h3>
                  <p className="text-[11px] text-slate-600 font-medium mt-0.5 line-clamp-1">
                    {sc.subtitle}
                  </p>
                </div>
                
                <div className="mt-2.5 pt-2 border-t border-slate-200 flex items-center justify-between text-[10px]">
                  <span className={`font-bold ${isSelected ? 'text-indigo-600' : 'text-slate-500'}`}>
                    {isSelected ? 'Active' : 'Select'}
                  </span>
                  <span className="text-slate-400">→</span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* FULL-WIDTH WORKFLOW CONTAINER BELOW */}
      <div className="space-y-6">
        
        {/* Scenario Action & Control Bar */}
        <div className="bg-white rounded-xl border border-slate-300 shadow-sm p-5 sm:p-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="max-w-3xl">
              <div className="flex items-center gap-2">
                <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded border uppercase ${
                  selectedScenario.category === 'ATTACK' 
                    ? 'bg-rose-100 text-rose-800 border-rose-300' 
                    : 'bg-emerald-100 text-emerald-800 border-emerald-300'
                }`}>
                  {selectedScenario.category} SCENARIO
                </span>
                <span className="text-xs text-slate-300">•</span>
                <span className="text-xs text-slate-700 font-bold">{selectedScenario.subtitle}</span>
              </div>
              <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 mt-1">
                {selectedScenario.title}
              </h2>
              <p className="mt-1 text-xs sm:text-sm text-slate-700 leading-relaxed font-normal">
                {selectedScenario.description}
              </p>
            </div>

            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 shrink-0">
              {response && (
                <div className="flex items-center">
                  {response.status === 'VERIFIED' && response.decision === 1 ? (
                    <span className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-bold bg-emerald-100 text-emerald-900 border border-emerald-300 shadow-2xs">
                      <CheckCircle2 size={16} /> DISBURSAL AUTHORIZED
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-bold bg-rose-100 text-rose-900 border border-rose-300 shadow-2xs">
                      <ShieldAlert size={16} /> DISBURSAL BLOCKED (FAIL-CLOSED)
                    </span>
                  )}
                </div>
              )}

              <button
                type="button"
                disabled={executing}
                onClick={() => handleRunScenario()}
                className={`py-3 px-6 rounded-xl font-bold text-xs sm:text-sm shadow-sm flex items-center justify-center gap-2 transition-all ${
                  executing
                    ? 'bg-slate-200 text-slate-500 cursor-not-allowed'
                    : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-indigo-600/30 shadow-md hover:-translate-y-0.5'
                }`}
              >
                {executing ? (
                  <>
                    <span className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin"></span>
                    <span>Evaluating ZK Pipeline...</span>
                  </>
                ) : (
                  <>
                    <Play size={15} />
                    <span>Run {selectedScenario.title}</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* 5-Step Pipeline Flow */}
          <div className="mt-6 pt-5 border-t border-slate-200">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-600 block mb-2">
              End-to-End Cryptographic Execution Flow:
            </span>
            <div className="grid grid-cols-5 gap-2 text-center text-[10px] font-bold">
              {[
                '1. Ingest Features',
                '2. Scorecard Eval',
                '3. Halo2 Prover',
                '4. Lender Verifier',
                '5. Disbursal Gate',
              ].map((label, idx) => {
                const isActive = activeStepIndex === idx;
                const isDone = activeStepIndex > idx || (response && !executing);
                return (
                  <div
                    key={label}
                    className={`py-2 px-1 rounded-lg border transition-all ${
                      isActive
                        ? 'bg-indigo-600 text-white border-indigo-600 animate-pulse shadow-sm'
                        : isDone
                        ? 'bg-slate-100 text-slate-900 border-slate-300'
                        : 'bg-slate-50 text-slate-500 border-slate-200'
                    }`}
                  >
                    {label}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* PROMINENT MISMATCH INSPECTOR CARD */}
        {response && (
          <div className="animate-in fade-in duration-300">
            {response.status === 'FAILED' && mismatch ? (
              /* TAMPER / MISMATCH HIGHLIGHT CARD */
              <div className="rounded-2xl border-2 border-rose-500 bg-gradient-to-b from-rose-50/80 to-white p-6 shadow-md">
                <div className="flex items-start gap-3.5 mb-4">
                  <div className="w-10 h-10 rounded-xl bg-rose-600 text-white flex items-center justify-center shrink-0 shadow-sm">
                    <AlertTriangle size={22} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-extrabold uppercase tracking-widest text-rose-900 bg-rose-200 px-2.5 py-0.5 rounded-full inline-block border border-rose-300">
                        Cryptographic Mismatch Detected
                      </span>
                      <span className="text-xs font-mono font-bold text-rose-800">
                        {mismatch.step} · {response.failure_reason}
                      </span>
                    </div>
                    <h3 className="text-xl font-extrabold text-slate-900 mt-1">
                      {mismatch.label}
                    </h3>
                    <p className="mt-1 text-xs sm:text-sm text-slate-800 leading-relaxed max-w-3xl font-medium">
                      {mismatch.reason}
                    </p>
                  </div>
                </div>

                {/* EXACT VALUE MISMATCH COMPARISON BOX */}
                <div className="mt-5 grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
                  {/* Expected Value Box */}
                  <div className="p-4 rounded-xl bg-white border-2 border-slate-300 shadow-2xs">
                    <div className="flex items-center justify-between pb-2 border-b border-slate-200 mb-2">
                      <span className="text-[10px] font-extrabold uppercase tracking-wider text-slate-700 font-sans">
                        Contract Policy (Expected)
                      </span>
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 border border-emerald-300">
                        MUTUAL AGREEMENT
                      </span>
                    </div>
                    <span className="text-xs text-slate-600 font-sans font-bold block mb-1">
                      {mismatch.expected_label}:
                    </span>
                    <div className="p-2.5 rounded bg-slate-100 border border-slate-300 text-slate-900 font-bold break-all">
                      {mismatch.expected}
                    </div>
                  </div>

                  {/* Actual Tampered Value Box */}
                  <div className="p-4 rounded-xl bg-rose-50 border-2 border-rose-400 shadow-2xs">
                    <div className="flex items-center justify-between pb-2 border-b border-rose-300 mb-2">
                      <span className="text-[10px] font-extrabold uppercase tracking-wider text-rose-900 font-sans">
                        Claimed in Proof (Actual Mismatch)
                      </span>
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-rose-200 text-rose-900 border border-rose-400">
                        REJECTED BY VERIFIER
                      </span>
                    </div>
                    <span className="text-xs text-rose-900 font-sans font-bold block mb-1">
                      {mismatch.actual_label}:
                    </span>
                    <div className="p-2.5 rounded bg-white border-2 border-rose-400 text-rose-800 font-bold break-all">
                      {mismatch.actual}
                    </div>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-rose-300 flex items-center justify-between text-xs text-rose-900 font-sans">
                  <span className="font-bold">
                    Disbursal Gate Response: STRICT FAIL-CLOSED. No funds disbursed.
                  </span>
                  <span className="font-mono text-[11px] text-slate-700 font-semibold">
                    Logged to Audit Block #{response.ledger_seq}
                  </span>
                </div>
              </div>
            ) : response.status === 'VERIFIED' ? (
              /* HONEST FLOW CONFIRMATION CARD */
              <div className="rounded-2xl border-2 border-emerald-500 bg-gradient-to-b from-emerald-50/70 to-white p-6 shadow-md">
                <div className="flex items-start gap-3.5">
                  <div className="w-10 h-10 rounded-xl bg-emerald-600 text-white flex items-center justify-center shrink-0 shadow-sm">
                    <ShieldCheck size={22} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-extrabold uppercase tracking-widest text-emerald-900 bg-emerald-200 px-2.5 py-0.5 rounded-full inline-block border border-emerald-300">
                        Cryptographic Verification Complete
                      </span>
                      <span className="text-xs font-mono font-bold text-emerald-800">
                        ALL 9 STEPS VERIFIED (V1-V9)
                      </span>
                    </div>
                    <h3 className="text-xl font-extrabold text-slate-900 mt-1">
                      {response.decision === 1 ? 'Loan Disbursal Authorized' : 'Policy Rejection Conformed'}
                    </h3>
                    <p className="mt-1 text-xs sm:text-sm text-slate-800 leading-relaxed max-w-3xl font-medium">
                      {response.decision === 1
                        ? 'Applicant qualified under the agreed 0.500 cutoff. Halo2 zero-knowledge proof verified against policy pol_meridian_quickfin_v1. Disbursal gate authorized for 24-hour bank release.'
                        : 'Subprime applicant correctly rejected by scorecard inference (decision=0). Disbursal gate strictly holds loan release without disclosing proprietary weights or borrower PII across boundaries.'}
                    </p>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-emerald-300 flex items-center justify-between text-xs text-emerald-900 font-sans font-medium">
                  <span>
                    Model Commitment C, Input Commitment X, and Threshold 0.500 strictly agree with contract policy.
                  </span>
                  <span className="font-mono text-[11px] text-slate-700 font-semibold">
                    Anchored in Ledger Block #{response.ledger_seq}
                  </span>
                </div>
              </div>
            ) : null}
          </div>
        )}

        {/* 2-COLUMN SECTION: VERIFIER 9 STEPS (LEFT) + PROOF PAYLOAD (RIGHT) */}
        {/* Notice items-start prevents child columns from stretching to match each other's height */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          
          {/* Left: 9-Step Verification Breakdown (7 cols) */}
          <div className="lg:col-span-7 bg-white rounded-xl border border-slate-300 shadow-sm p-6">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200 mb-4">
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800">
                  Verifier Step Breakdown (V1 to V9)
                </h3>
                <p className="text-[11px] text-slate-600 mt-0.5">Sequential cryptographic conformance validation</p>
              </div>
              {response?.status && (
                <span className={`text-[11px] font-mono font-bold px-2.5 py-0.5 rounded border ${
                  response.status === 'VERIFIED' ? 'bg-emerald-100 text-emerald-800 border-emerald-300' : 'bg-rose-100 text-rose-800 border-rose-300'
                }`}>
                  Status: {response.status}
                </span>
              )}
            </div>

            {stepsList.length > 0 ? (
              <div className="space-y-2">
                {stepsList.map((st) => (
                  <div
                    key={st.step}
                    className={`p-3 rounded-lg border flex flex-col gap-1.5 transition-colors ${
                      st.passed
                        ? 'bg-emerald-50/50 border-emerald-300 text-slate-900'
                        : 'bg-rose-50 border-2 border-rose-500 text-rose-950 font-semibold'
                    }`}
                  >
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        {st.passed ? (
                          <CheckCircle2 size={16} className="text-emerald-700 shrink-0" />
                        ) : (
                          <XCircle size={16} className="text-rose-700 shrink-0" />
                        )}
                        <span className="font-mono font-bold text-slate-900">{st.step}:</span>
                        <span className="font-semibold text-slate-900">{st.name}</span>
                      </div>
                      <span
                        className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase ${
                          st.passed
                            ? 'bg-emerald-200 text-emerald-900'
                            : 'bg-rose-600 text-white shadow-xs'
                        }`}
                      >
                        {st.passed ? 'PASSED' : 'FAILED HERE'}
                      </span>
                    </div>

                    <p className="text-[11px] text-slate-600 pl-6 leading-relaxed">
                      {st.description}
                    </p>

                    {/* Step mismatch callout if this step failed */}
                    {!st.passed && (
                      <div className="ml-6 mt-1 p-2 rounded bg-white border border-rose-300 text-[11px] font-mono text-rose-900">
                        {st.expected && <div>Expected: <strong className="text-slate-900">{String(st.expected)}</strong></div>}
                        {st.actual && <div>Actual Mismatch: <strong className="text-rose-700">{String(st.actual)}</strong></div>}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-12 text-center text-slate-500 text-xs font-medium">
                Select any of the 7 horizontal test cases above and click execute to observe the verifier step evaluations.
              </div>
            )}
          </div>

          {/* Right: Transmitted Proof Payload & Public Inputs Vector (5 cols) */}
          {/* h-fit ensures the container only extends as far as its content */}
          <div className="lg:col-span-5 bg-slate-900 text-slate-100 rounded-xl p-6 border border-slate-700 shadow-md h-fit">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
              <div>
                <span className="text-xs font-mono font-bold uppercase tracking-wider text-purple-300 block">
                  Transmitted Proof Payload
                </span>
                <span className="text-[10px] text-slate-400 font-mono">Zero-Knowledge Witness & Public Inputs</span>
              </div>
              {response?.proof && (
                <button
                  type="button"
                  onClick={copyProof}
                  className="inline-flex items-center gap-1 text-[11px] font-mono font-bold text-indigo-400 hover:text-indigo-300 bg-slate-800 px-2 py-1 rounded border border-slate-700"
                >
                  {copied ? <Check size={12} /> : <Copy size={12} />}
                  <span>{copied ? 'Copied' : 'Copy Proof'}</span>
                </button>
              )}
            </div>

            {response ? (
              <div className="space-y-3 text-xs font-mono">
                <div className="flex justify-between py-1 border-b border-slate-800">
                  <span className="text-slate-400">Decision ID:</span>
                  <span className="text-slate-200 font-bold">{response.decision_id}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-800">
                  <span className="text-slate-400">Policy Contract:</span>
                  <span className="text-slate-200">{response.policy_id}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-800">
                  <span className="text-slate-400">Ledger Block Height:</span>
                  <span className="text-emerald-400 font-bold">#{response.ledger_seq}</span>
                </div>

                {response.public_inputs && (
                  <div className="pt-2">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-slate-400 block text-[11px]">Public Inputs Vector:</span>
                      {mismatch?.field && (
                        <span className="text-[10px] text-rose-400 font-bold">
                          ⚠️ Mismatched Field: {mismatch.field}
                        </span>
                      )}
                    </div>
                    <pre className="p-3 rounded-lg bg-slate-950 text-[11px] text-slate-200 overflow-x-auto leading-relaxed border border-slate-800 max-h-64">
                      {JSON.stringify(response.public_inputs, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            ) : (
              <div className="py-12 text-center text-slate-500 text-xs font-mono">
                Transmitted public inputs and proof hashes will render here after execution.
              </div>
            )}

            <div className="pt-4 mt-4 border-t border-slate-800 text-[11px] text-slate-400 font-mono flex items-center justify-between">
              <span>Halo2 KZG SNARK Prover</span>
              <span>Fixed Scale 1024</span>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
