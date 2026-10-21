import { useState } from 'react';
import { 
  Play, ShieldAlert, CheckCircle2, XCircle, 
  Copy, Check, Cpu, Terminal, AlertTriangle, ShieldCheck
} from 'lucide-react';
import { submitLoanApplication, type ApplyLoanResponse, type VerificationStep, type MismatchDetails } from '../api/client';

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
    persona: 'priya',
    category: 'HONEST',
    title: '1. Honest Approval',
    subtitle: 'Prime (Priya Sharma)',
    description: 'Applicant qualifies under agreed cutoff (CIBIL 758, FOIR 28%). Quick FinCorp proves inference on agreed model. All 9 verifier checks pass, and Meridian Digital authorizes disbursal within 24 hours.',
  },
  {
    id: 'honest-subprime',
    persona: 'rahul',
    category: 'HONEST',
    title: '2. Honest Rejection',
    subtitle: 'Subprime (Rahul Verma)',
    description: 'Scorecard calculates high risk (CIBIL 542, FOIR 68%). Prover generates valid ZK proof of decision=0. Disbursal gate strictly holds funds (fail-closed).',
  },
  {
    id: 'tamper-model',
    persona: 'priya',
    tamper: 'model',
    category: 'ATTACK',
    title: '3. Model Swap',
    subtitle: 'Unauthorized Model',
    description: 'LSP attempts to evaluate using an unapproved model weights file. Lender verifier checks model commitment C against approved registry and rejects the proof at Step V2.',
  },
  {
    id: 'tamper-threshold',
    persona: 'rahul',
    tamper: 'threshold',
    category: 'ATTACK',
    title: '4. Cutoff Creep',
    subtitle: 'Lowering Threshold',
    description: 'LSP attempts to pass a high-risk applicant by lowering cutoff threshold tau from 0.500 to 0.050. Caught immediately at Step V4 (Exact Decimal Match).',
  },
  {
    id: 'tamper-input',
    persona: 'priya',
    tamper: 'input',
    category: 'ATTACK',
    title: '5. Feature Tamper',
    subtitle: 'Income / Bureau Spoofing',
    description: 'Features submitted to the verifier do not match the witness proven in ZK (X != X prime). Caught by the Input Binding adapter before fund release.',
  },
  {
    id: 'tamper-replay',
    persona: 'priya',
    tamper: 'replay',
    category: 'ATTACK',
    title: '6. Replay Attack',
    subtitle: 'Re-submitting Used Proof',
    description: 'Attacker takes a valid proof from an earlier loan and re-submits it for a new application. Caught by SHA-256 uniqueness check at Step V6.',
  },
  {
    id: 'tamper-corrupt-zk',
    persona: 'priya',
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
      <div className="mb-6">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200 mb-2">
          <Cpu size={14} /> Interactive Cryptographic Verifier Sandbox
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
          Zero-Knowledge Conformance & Tamper Lab
        </h1>
        <p className="mt-1 text-sm text-slate-500 max-w-3xl">
          Test real underwriting loan applications against the live verifier engine. Inspect Halo2 proofs, mathematical step assertions, and fail-closed disbursal gates for Meridian Digital and Quick FinCorp Pvt Ltd.
        </p>
      </div>

      {/* HORIZONTAL CARDS ROW FOR THE 7 SCENARIOS */}
      <div className="mb-7">
        <div className="flex items-center justify-between mb-3 px-1">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
            Select Test Scenario (7 Test Cases):
          </span>
          <span className="text-[11px] text-slate-400">Click any card to inspect and run scenario workflow below</span>
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
                    ? 'border-indigo-600 bg-white shadow-md ring-2 ring-indigo-600/20'
                    : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/50'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between gap-1 mb-1.5">
                    <span
                      className={`text-[9px] font-extrabold px-1.5 py-0.5 rounded border uppercase tracking-wider ${
                        isAttack
                          ? 'bg-rose-50 text-rose-700 border-rose-200'
                          : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                      }`}
                    >
                      {sc.category}
                    </span>
                    <span className="text-[10px] text-slate-400 font-mono capitalize">
                      {sc.persona}
                    </span>
                  </div>
                  <h3 className="font-bold text-slate-900 text-xs line-clamp-1 leading-snug">
                    {sc.title}
                  </h3>
                  <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-1">
                    {sc.subtitle}
                  </p>
                </div>
                
                <div className="mt-2.5 pt-2 border-t border-slate-100 flex items-center justify-between text-[10px]">
                  <span className={`font-semibold ${isSelected ? 'text-indigo-600 font-bold' : 'text-slate-400'}`}>
                    {isSelected ? 'Active' : 'Select'}
                  </span>
                  <span className="text-slate-300">→</span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* FULL-WIDTH WORKFLOW CONTAINER BELOW */}
      <div className="space-y-6">
        
        {/* Scenario Action & Control Bar */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 sm:p-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="max-w-3xl">
              <div className="flex items-center gap-2">
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${
                  selectedScenario.category === 'ATTACK' 
                    ? 'bg-rose-50 text-rose-700 border-rose-200' 
                    : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                }`}>
                  {selectedScenario.category} SCENARIO
                </span>
                <span className="text-xs text-slate-400">•</span>
                <span className="text-xs text-slate-500 font-medium">{selectedScenario.subtitle}</span>
              </div>
              <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 mt-1">
                {selectedScenario.title}
              </h2>
              <p className="mt-1 text-xs sm:text-sm text-slate-600 leading-relaxed">
                {selectedScenario.description}
              </p>
            </div>

            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 shrink-0">
              {response && (
                <div className="flex items-center">
                  {response.status === 'VERIFIED' && response.decision === 1 ? (
                    <span className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-bold bg-emerald-50 text-emerald-800 border border-emerald-200 shadow-xs">
                      <CheckCircle2 size={16} /> DISBURSAL AUTHORIZED
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-bold bg-rose-50 text-rose-800 border border-rose-200 shadow-xs">
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
                    ? 'bg-slate-200 text-slate-400 cursor-not-allowed'
                    : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-indigo-600/20 shadow-md hover:-translate-y-0.5'
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
          <div className="mt-6 pt-5 border-t border-slate-100">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-2">
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
                        ? 'bg-slate-100 text-slate-800 border-slate-200'
                        : 'bg-slate-50 text-slate-400 border-slate-100'
                    }`}
                  >
                    {label}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* PROMINENT MISMATCH INSPECTOR CARD (REQUIREMENT 2) */}
        {response && (
          <div className="animate-in fade-in duration-300">
            {response.status === 'FAILED' && mismatch ? (
              /* TAMPER / MISMATCH HIGHLIGHT CARD */
              <div className="rounded-2xl border-2 border-rose-500 bg-gradient-to-b from-rose-50/70 to-white p-6 shadow-md">
                <div className="flex items-start gap-3.5 mb-4">
                  <div className="w-10 h-10 rounded-xl bg-rose-600 text-white flex items-center justify-center shrink-0 shadow-sm">
                    <AlertTriangle size={22} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-bold uppercase tracking-widest text-rose-800 bg-rose-100 px-2 py-0.5 rounded-full inline-block">
                        Cryptographic Mismatch Detected
                      </span>
                      <span className="text-xs font-mono font-bold text-rose-700">
                        {mismatch.step} · {response.failure_reason}
                      </span>
                    </div>
                    <h3 className="text-xl font-extrabold text-slate-900 mt-1">
                      {mismatch.label}
                    </h3>
                    <p className="mt-1 text-xs sm:text-sm text-slate-700 leading-relaxed max-w-3xl">
                      {mismatch.reason}
                    </p>
                  </div>
                </div>

                {/* EXACT VALUE MISMATCH COMPARISON BOX */}
                <div className="mt-5 grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
                  {/* Expected Value Box */}
                  <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-2xs">
                    <div className="flex items-center justify-between pb-2 border-b border-slate-100 mb-2">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 font-sans">
                        Contract Policy (Expected)
                      </span>
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                        MUTUAL AGREEMENT
                      </span>
                    </div>
                    <span className="text-xs text-slate-400 font-sans block mb-1">
                      {mismatch.expected_label}:
                    </span>
                    <div className="p-2.5 rounded bg-slate-50 border border-slate-200 text-slate-900 font-bold break-all">
                      {mismatch.expected}
                    </div>
                  </div>

                  {/* Actual Tampered Value Box */}
                  <div className="p-4 rounded-xl bg-rose-50/60 border-2 border-rose-300 shadow-2xs">
                    <div className="flex items-center justify-between pb-2 border-b border-rose-200 mb-2">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-rose-800 font-sans">
                        Claimed in Proof (Actual Mismatch)
                      </span>
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-rose-100 text-rose-800 border border-rose-300">
                        REJECTED BY VERIFIER
                      </span>
                    </div>
                    <span className="text-xs text-rose-700 font-sans block mb-1">
                      {mismatch.actual_label}:
                    </span>
                    <div className="p-2.5 rounded bg-white border border-rose-300 text-rose-700 font-bold break-all">
                      {mismatch.actual}
                    </div>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-rose-200/80 flex items-center justify-between text-xs text-rose-800 font-sans">
                  <span className="font-semibold">
                    Disbursal Gate Response: <strong>STRICT FAIL-CLOSED</strong>. No funds disbursed.
                  </span>
                  <span className="font-mono text-[11px] text-slate-500">
                    Logged to Audit Block #{response.ledger_seq}
                  </span>
                </div>
              </div>
            ) : response.status === 'VERIFIED' ? (
              /* HONEST FLOW CONFIRMATION CARD */
              <div className="rounded-2xl border-2 border-emerald-500 bg-gradient-to-b from-emerald-50/60 to-white p-6 shadow-md">
                <div className="flex items-start gap-3.5">
                  <div className="w-10 h-10 rounded-xl bg-emerald-600 text-white flex items-center justify-center shrink-0 shadow-sm">
                    <ShieldCheck size={22} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-bold uppercase tracking-widest text-emerald-800 bg-emerald-100 px-2 py-0.5 rounded-full inline-block">
                        Cryptographic Verification Complete
                      </span>
                      <span className="text-xs font-mono font-bold text-emerald-700">
                        ALL 9 STEPS VERIFIED (V1-V9)
                      </span>
                    </div>
                    <h3 className="text-xl font-extrabold text-slate-900 mt-1">
                      {response.decision === 1 ? 'Loan Disbursal Authorized' : 'Policy Rejection Conformed'}
                    </h3>
                    <p className="mt-1 text-xs sm:text-sm text-slate-700 leading-relaxed max-w-3xl">
                      {response.decision === 1
                        ? 'Applicant qualified under the agreed 0.500 cutoff. Halo2 zero-knowledge proof verified against policy pol_meridian_quickfin_v1. Disbursal gate authorized for 24-hour bank release.'
                        : 'Subprime applicant correctly rejected by scorecard inference (decision=0). Disbursal gate strictly holds loan release without disclosing proprietary weights or borrower PII across boundaries.'}
                    </p>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-emerald-200/80 flex items-center justify-between text-xs text-emerald-800 font-sans">
                  <span>
                    Model Commitment C, Input Commitment X, and Threshold 0.500 strictly agree with contract policy.
                  </span>
                  <span className="font-mono text-[11px] text-slate-500">
                    Anchored in Ledger Block #{response.ledger_seq}
                  </span>
                </div>
              </div>
            ) : null}
          </div>
        )}

        {/* 2-COLUMN SECTION: VERIFIER 9 STEPS (LEFT) + PROOF PAYLOAD (RIGHT) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* Left: 9-Step Verification Breakdown (7 cols) */}
          <div className="lg:col-span-7 bg-white rounded-xl border border-slate-200 shadow-sm p-6">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                  Verifier Step Breakdown (V1 to V9)
                </h3>
                <p className="text-[11px] text-slate-500 mt-0.5">Sequential cryptographic conformance validation</p>
              </div>
              {response?.status && (
                <span className={`text-[11px] font-mono font-bold px-2 py-0.5 rounded ${
                  response.status === 'VERIFIED' ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
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
                        ? 'bg-emerald-50/40 border-emerald-200 text-slate-900'
                        : 'bg-rose-50/80 border-2 border-rose-500 text-rose-950 font-semibold'
                    }`}
                  >
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        {st.passed ? (
                          <CheckCircle2 size={16} className="text-emerald-600 shrink-0" />
                        ) : (
                          <XCircle size={16} className="text-rose-600 shrink-0" />
                        )}
                        <span className="font-mono font-bold text-slate-900">{st.step}:</span>
                        <span>{st.name}</span>
                      </div>
                      <span
                        className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase ${
                          st.passed
                            ? 'bg-emerald-100 text-emerald-800'
                            : 'bg-rose-600 text-white shadow-xs'
                        }`}
                      >
                        {st.passed ? 'PASSED' : 'FAILED HERE'}
                      </span>
                    </div>

                    <p className="text-[11px] text-slate-500 pl-6 leading-relaxed">
                      {st.description}
                    </p>

                    {/* Step mismatch callout if this step failed */}
                    {!st.passed && (
                      <div className="ml-6 mt-1 p-2 rounded bg-white border border-rose-200 text-[11px] font-mono text-rose-800">
                        {st.expected && <div>Expected: <strong>{String(st.expected)}</strong></div>}
                        {st.actual && <div>Actual Mismatch: <strong className="text-rose-600">{String(st.actual)}</strong></div>}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-12 text-center text-slate-400 text-xs">
                Select any of the 7 horizontal test cases above and click execute to observe the verifier step evaluations.
              </div>
            )}
          </div>

          {/* Right: Transmitted Proof Payload & Public Inputs Vector (5 cols) */}
          <div className="lg:col-span-5 bg-slate-900 text-slate-100 rounded-xl p-6 border border-slate-800 shadow-md flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
                <div className="flex items-center gap-2">
                  <Terminal size={15} className="text-purple-400" />
                  <span className="text-xs font-mono font-bold uppercase tracking-wider text-purple-300">
                    Transmitted Proof Payload
                  </span>
                </div>
                {response?.proof && (
                  <button
                    type="button"
                    onClick={copyProof}
                    className="inline-flex items-center gap-1 text-[11px] font-mono text-indigo-400 hover:text-indigo-300"
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
                    <span className="text-slate-200">{response.decision_id}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-800">
                    <span className="text-slate-400">Policy Contract:</span>
                    <span className="text-slate-200">{response.policy_id}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-800">
                    <span className="text-slate-400">Ledger Block Height:</span>
                    <span className="text-emerald-400">#{response.ledger_seq}</span>
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
                      <pre className="p-3 rounded-lg bg-slate-950 text-[11px] text-slate-300 overflow-x-auto leading-relaxed border border-slate-800 max-h-64">
                        {JSON.stringify(response.public_inputs, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              ) : (
                <div className="py-20 text-center text-slate-500 text-xs font-mono">
                  Transmitted public inputs and proof hashes will render here after execution.
                </div>
              )}
            </div>

            <div className="pt-4 mt-4 border-t border-slate-800 text-[11px] text-slate-500 font-mono flex items-center justify-between">
              <span>Halo2 KZG SNARK Prover</span>
              <span>Fixed Scale 1024</span>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
