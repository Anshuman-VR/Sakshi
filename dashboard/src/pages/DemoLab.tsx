import { useState } from 'react';
import { 
  Play, ShieldCheck, ShieldAlert, CheckCircle2, XCircle, 
  Copy, Check, Cpu, Key, Terminal, Lock
} from 'lucide-react';
import { submitLoanApplication, type ApplyLoanResponse, type VerificationStep } from '../api/client';

interface ScenarioDef {
  id: string;
  tamper?: string;
  persona: string;
  title: string;
  category: 'HONEST' | 'ATTACK';
  subtitle: string;
  description: string;
  expectedStepFail?: string;
  expectedReason?: string;
}

const SCENARIOS: ScenarioDef[] = [
  {
    id: 'honest-prime',
    persona: 'priya',
    category: 'HONEST',
    title: '1. Honest Loan Approval',
    subtitle: 'Prime Applicant (Priya Sharma)',
    description: 'Applicant qualifies under agreed criteria (CIBIL 758, FOIR 28%). LSP proves inference on approved model. All 9 verifier checks pass, and funds disbursal is authorized.',
  },
  {
    id: 'honest-subprime',
    persona: 'rahul',
    category: 'HONEST',
    title: '2. Honest Loan Rejection',
    subtitle: 'High-Risk Applicant (Rahul Verma)',
    description: 'Model calculates high risk (CIBIL 542, FOIR 68%). Prover generates valid ZK proof of decision=0. Disbursal gate strictly holds funds.',
  },
  {
    id: 'tamper-model',
    persona: 'priya',
    tamper: 'model',
    category: 'ATTACK',
    title: '3. Tamper: Model Weight Swap',
    subtitle: 'LSP Swaps to Unauthorized ML Model',
    description: 'LSP attempts to use a modified or unapproved model weights file. Lender verifier checks model commitment C against approved registry and rejects the proof.',
    expectedStepFail: 'V2_MODEL_APPROVED',
    expectedReason: 'MODEL_MISMATCH',
  },
  {
    id: 'tamper-threshold',
    persona: 'rahul',
    tamper: 'threshold',
    category: 'ATTACK',
    title: '4. Tamper: Threshold Creep',
    subtitle: 'LSP Lowers Underwriting Cutoff',
    description: 'LSP attempts to pass a risky loan by lowering the threshold parameter tau from 0.200 to 0.050. Caught at Step V4 (Exact Decimal Match).',
    expectedStepFail: 'V4_THRESHOLD_MATCH',
    expectedReason: 'THRESHOLD_MISMATCH',
  },
  {
    id: 'tamper-input',
    persona: 'priya',
    tamper: 'input',
    category: 'ATTACK',
    title: '5. Tamper: Feature Alteration',
    subtitle: 'Credit Bureau / Feature Spoofing',
    description: 'Features submitted to the verifier do not match the witness proven in ZK (X != X prime). Caught by the Input Binding adapter before fund release.',
    expectedStepFail: 'V7_DECISION_MATCH',
    expectedReason: 'BINDING_MISMATCH',
  },
  {
    id: 'tamper-replay',
    persona: 'priya',
    tamper: 'replay',
    category: 'ATTACK',
    title: '6. Tamper: Proof Replay Attack',
    subtitle: 'Re-submitting Previously Used Proof',
    description: 'Attacker takes a valid proof from an earlier loan and re-submits it for a new application. Caught by SHA-256 uniqueness check at Step V6.',
    expectedStepFail: 'V6_UNIQUENESS',
    expectedReason: 'REPLAY',
  },
  {
    id: 'tamper-corrupt-zk',
    persona: 'priya',
    tamper: 'invalid_zk',
    category: 'ATTACK',
    title: '7. Tamper: Corrupted ZK Proof',
    subtitle: 'Forged or Malformed SNARK Bytes',
    description: 'Submitting invalid cryptographic proof polynomial bytes. Verifier fails at Step V8 with INVALID_PROOF.',
    expectedStepFail: 'V8_ZK_VERIFY',
    expectedReason: 'INVALID_PROOF',
  },
];

export function DemoLab() {
  const [selectedId, setSelectedId] = useState<string>('honest-prime');
  const [executing, setExecuting] = useState<boolean>(false);
  const [activeStepIndex, setActiveStepIndex] = useState<number>(-1);
  const [response, setResponse] = useState<ApplyLoanResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  const selectedScenario = SCENARIOS.find((s) => s.id === selectedId) || SCENARIOS[0];

  const handleRunScenario = async () => {
    setExecuting(true);
    setResponse(null);
    setErrorMsg(null);
    setActiveStepIndex(0);

    try {
      // Step 1: Model & Policy
      await new Promise((r) => setTimeout(r, 250));
      setActiveStepIndex(1);

      // Step 2: Prover sidecar
      await new Promise((r) => setTimeout(r, 350));
      setActiveStepIndex(2);

      // Step 3: Lender verifier
      const res = await submitLoanApplication({
        persona: selectedScenario.persona,
        tamper: selectedScenario.tamper,
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

  return (
    <main className="mx-auto w-[calc(100%-32px)] md:w-[calc(100%-48px)] xl:w-[calc(100%-64px)] max-w-[1600px] py-8 sm:py-10">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200 mb-2">
            <Cpu size={14} /> Interactive Cryptographic Verifier Sandbox
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
            Zero-Knowledge Conformance & Tamper Lab
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Execute real end-to-end loan applications against the live verifier engine. Inspect Halo2 proofs, mathematical step assertions, and fail-closed disbursal gates.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3.5 py-2 bg-emerald-50 rounded-lg border border-emerald-200 text-xs font-semibold text-emerald-800">
            <Lock size={13} /> Live Backend Connected (:8000)
          </div>
        </div>
      </div>

      {/* Main Grid: Left Scenario Selector, Right Step Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left Column: Scenarios (5 cols) */}
        <div className="lg:col-span-5 space-y-3">
          <div className="flex items-center justify-between px-1">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Select Test Scenario:
            </span>
            <span className="text-[11px] text-slate-400">7 Scenarios Available</span>
          </div>

          <div className="space-y-2.5">
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
                  className={`w-full text-left p-4 rounded-xl border transition-all ${
                    isSelected
                      ? 'border-indigo-600 bg-white shadow-md ring-2 ring-indigo-600/20'
                      : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/50'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-slate-900 text-sm">{sc.title}</span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                        isAttack
                          ? 'bg-rose-50 text-rose-700 border-rose-200'
                          : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                      }`}
                    >
                      {sc.category}
                    </span>
                  </div>
                  <div className="text-xs font-medium text-slate-600 mb-1.5">{sc.subtitle}</div>
                  <p className="text-[11px] text-slate-500 line-clamp-2 leading-relaxed">
                    {sc.description}
                  </p>
                </button>
              );
            })}
          </div>

          {/* Run Action Button */}
          <div className="pt-2">
            <button
              type="button"
              disabled={executing}
              onClick={handleRunScenario}
              className={`w-full py-3.5 px-6 rounded-xl font-bold text-sm shadow-sm flex items-center justify-center gap-2 transition-all ${
                executing
                  ? 'bg-slate-200 text-slate-400 cursor-not-allowed'
                  : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-indigo-600/20 shadow-md'
              }`}
            >
              {executing ? (
                <>
                  <span className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin"></span>
                  <span>Executing Pipeline...</span>
                </>
              ) : (
                <>
                  <Play size={15} />
                  <span>Execute {selectedScenario.title}</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Right Column: Execution Visualizer & ZK Proof Inspector (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          
          {/* Top Panel: Scenario Overview & Disbursal Outcome */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                  Active Simulation Target
                </span>
                <h2 className="text-xl font-bold text-slate-900">{selectedScenario.title}</h2>
                <p className="text-xs text-slate-500 mt-0.5">{selectedScenario.subtitle}</p>
              </div>

              {response && (
                <div className="text-left sm:text-right">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                    Disbursal Gate Decision
                  </span>
                  {response.status === 'VERIFIED' && response.decision === 1 ? (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
                      <ShieldCheck size={14} className="text-emerald-600" />
                      DISBURSAL PERMITTED
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-rose-50 text-rose-800 border border-rose-200">
                      <ShieldAlert size={14} className="text-rose-600" />
                      DISBURSAL BLOCKED
                    </span>
                  )}
                </div>
              )}
            </div>

            {/* Pipeline Stage Visualizer */}
            <div className="mt-4 pt-2">
              <span className="text-[11px] font-bold text-slate-600 uppercase tracking-wider block mb-3">
                Execution Pipeline:
              </span>
              <div className="grid grid-cols-4 gap-2 text-center text-xs">
                {[
                  { step: '1. Policy', desc: 'Ed25519 terms' },
                  { step: '2. Prover', desc: 'Halo2 witness' },
                  { step: '3. Verifier', desc: 'V1-V9 Engine' },
                  { step: '4. Ledger', desc: 'Hash-chain' },
                ].map((s, idx) => {
                  const isDone = activeStepIndex > idx || (response !== null);
                  const isCurrent = activeStepIndex === idx && executing;
                  return (
                    <div
                      key={s.step}
                      className={`p-2.5 rounded-lg border transition-all ${
                        isCurrent
                          ? 'bg-indigo-50 border-indigo-500 ring-2 ring-indigo-500/20'
                          : isDone
                          ? 'bg-slate-50 border-slate-200'
                          : 'bg-white border-slate-100 opacity-50'
                      }`}
                    >
                      <strong className="block text-slate-900 text-xs">{s.step}</strong>
                      <span className="text-[10px] text-slate-500">{s.desc}</span>
                    </div>
                  );
                })}
              </div>
            </div>

            {errorMsg && (
              <div className="mt-4 p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-800">
                {errorMsg}
              </div>
            )}
          </div>

          {/* Step-by-Step V1 to V9 Conformance Breakdown */}
          {stepsList.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="px-6 py-4 border-b border-slate-200 bg-slate-50/50 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Terminal size={16} className="text-indigo-600" />
                  <h3 className="text-sm font-bold text-slate-900">
                    Lender Verifier Engine Breakdown (9 Sequential Checks)
                  </h3>
                </div>
                <span className="text-xs font-mono text-slate-500">
                  Status:{' '}
                  <strong className={response?.status === 'VERIFIED' ? 'text-emerald-700' : 'text-rose-700'}>
                    {response?.status}
                  </strong>
                </span>
              </div>

              <div className="divide-y divide-slate-100">
                {stepsList.map((st) => {
                  return (
                    <div
                      key={st.step}
                      className={`p-4 flex items-start justify-between gap-4 transition-colors ${
                        st.passed ? 'hover:bg-slate-50/50' : 'bg-rose-50/40 border-l-4 border-l-rose-500'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <div className="mt-0.5">
                          {st.passed ? (
                            <CheckCircle2 size={18} className="text-emerald-600" />
                          ) : (
                            <XCircle size={18} className="text-rose-600" />
                          )}
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-xs font-bold text-slate-900">{st.step}</span>
                            <span className="text-xs font-semibold text-slate-700">· {st.name}</span>
                          </div>
                          <p className="text-xs text-slate-500 mt-0.5">{st.description}</p>

                          {/* Failure Diagnostic Details */}
                          {!st.passed && (
                            <div className="mt-2 p-2.5 rounded-lg bg-white border border-rose-200 text-xs font-mono text-slate-800 space-y-1">
                              {st.expected !== undefined && (
                                <div>
                                  <span className="text-slate-400">Expected:</span>{' '}
                                  <span className="text-emerald-700 font-bold">{String(st.expected)}</span>
                                </div>
                              )}
                              {st.actual !== undefined && (
                                <div>
                                  <span className="text-slate-400">Claimed by LSP:</span>{' '}
                                  <span className="text-rose-700 font-bold">{String(st.actual)}</span>
                                </div>
                              )}
                              {st.binding_status && (
                                <div>
                                  <span className="text-slate-400">Input Binding Status:</span>{' '}
                                  <span className="text-rose-700 font-bold">{st.binding_status}</span>
                                </div>
                              )}
                              <div className="text-[11px] text-rose-800 pt-1 font-sans">
                                🛑 Fail-Closed Action: Disbursal halted. Failure logged to audit ledger.
                              </div>
                            </div>
                          )}
                        </div>
                      </div>

                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded font-mono shrink-0 ${
                          st.passed
                            ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                            : 'bg-rose-50 text-rose-800 border border-rose-200'
                        }`}
                      >
                        {st.passed ? 'PASS' : 'FAILED'}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Zero-Knowledge Proof Object Inspector */}
          {response && (
            <div className="bg-slate-950 text-slate-100 rounded-xl border border-slate-800 shadow-md p-6">
              <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-4">
                <div className="flex items-center gap-2">
                  <Key size={16} className="text-purple-400" />
                  <h3 className="text-sm font-bold text-white">
                    Halo2 Zero-Knowledge Proof & Public Inputs
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={copyProof}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs font-mono text-slate-300 transition-colors"
                >
                  {copied ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
                  <span>{copied ? 'Copied' : 'Copy Proof'}</span>
                </button>
              </div>

              {/* Proof Properties */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono mb-4">
                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
                  <span className="text-slate-500 block text-[10px] uppercase">Proof Size</span>
                  <span className="text-white font-bold">{response.proof_size_bytes || 2496} bytes</span>
                </div>
                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
                  <span className="text-slate-500 block text-[10px] uppercase">Proof Digest (SHA-256)</span>
                  <span className="text-purple-300 truncate block text-[11px]" title={response.proof_hash}>
                    {response.proof_hash ? `${response.proof_hash.slice(0, 18)}…` : '—'}
                  </span>
                </div>
              </div>

              {/* Public Inputs Vector */}
              {response.public_inputs && (
                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono space-y-1.5">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                    Public Inputs Vector Checked by Circuit:
                  </span>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
                    <div>
                      <span className="text-slate-500">Model Commitment (C):</span>
                      <span className="text-slate-200 block truncate" title={response.public_inputs.C}>
                        {response.public_inputs.C}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500">Input Commitment (X):</span>
                      <span className="text-slate-200 block truncate" title={response.public_inputs.X}>
                        {response.public_inputs.X}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500">Decision Output:</span>
                      <span className="text-emerald-400 font-bold block">
                        {response.public_inputs.decision === 1 ? '1 (APPROVED)' : '0 (REJECTED)'}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500">Threshold (tau):</span>
                      <span className="text-indigo-300 font-bold block">
                        {response.public_inputs.threshold.toFixed(3)}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Proof Base64 Snippet */}
              {response.proof && (
                <div className="mt-4">
                  <span className="text-[10px] uppercase font-bold text-slate-500 block mb-1">
                    Proof Payload Transcript (Truncated Base64):
                  </span>
                  <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-[10px] font-mono text-slate-400 break-all leading-relaxed">
                    {response.proof.slice(0, 200)}... [+{response.proof.length - 200} characters]
                  </div>
                </div>
              )}
            </div>
          )}

          {!response && !executing && (
            <div className="p-12 text-center rounded-xl border border-dashed border-slate-200 bg-white">
              <Play size={24} className="mx-auto text-slate-400 mb-2" />
              <h3 className="font-bold text-slate-800 text-sm">Ready to Test</h3>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                Select any test scenario on the left and click execute to watch the live cryptographic verifier validate or block the loan in real time.
              </p>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
