import { useState } from 'react';
import { 
  Play, ShieldAlert, CheckCircle2, XCircle, 
  Copy, Check, Cpu, Terminal
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
    description: 'Applicant qualifies under agreed cutoff (CIBIL 758, FOIR 28%). Quick FinCorp proves inference on agreed model. All 9 verifier checks pass, and Meridian Digital authorizes 24h disbursal.',
  },
  {
    id: 'honest-subprime',
    persona: 'rahul',
    category: 'HONEST',
    title: '2. Honest Loan Rejection',
    subtitle: 'High-Risk Applicant (Rahul Verma)',
    description: 'Scorecard calculates high risk (CIBIL 542, FOIR 68%). Prover generates valid ZK proof of decision=0. Disbursal gate strictly holds funds (fail-closed).',
  },
  {
    id: 'tamper-model',
    persona: 'priya',
    tamper: 'model',
    category: 'ATTACK',
    title: '3. Tamper: Model Weight Swap',
    subtitle: 'LSP Swaps to Unauthorized ML Model',
    description: 'LSP attempts to use an unapproved model weights file. Lender verifier checks model commitment C against approved registry and rejects the proof at Step V2.',
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
    description: 'LSP attempts to pass a rejected loan by lowering threshold tau from 0.500 to 0.050. Caught immediately at Step V4 (Exact Decimal Match).',
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
  const [, setErrorMsg] = useState<string | null>(null);
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
      {/* Clean Header */}
      <div className="mb-8">
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
                  : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-indigo-600/20 shadow-md hover:-translate-y-0.5'
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
                <span className="text-[10px] uppercase font-bold text-slate-400 block">Active Target Scenario</span>
                <h2 className="text-lg font-bold text-slate-900">{selectedScenario.title}</h2>
                <p className="text-xs text-slate-500 mt-0.5">{selectedScenario.subtitle}</p>
              </div>

              {response ? (
                <div className="text-right">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Disbursal Outcome</span>
                  <div className="mt-1">
                    {response.status === 'VERIFIED' && response.decision === 1 ? (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
                        <CheckCircle2 size={14} /> DISBURSAL AUTHORIZED
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-rose-50 text-rose-800 border border-rose-200">
                        <ShieldAlert size={14} /> DISBURSAL BLOCKED
                      </span>
                    )}
                  </div>
                </div>
              ) : (
                <div className="text-right">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Ready to Execute</span>
                  <span className="text-xs text-slate-500 font-mono">Awaiting Trigger</span>
                </div>
              )}
            </div>

            {/* Pipeline Stage Indicators */}
            <div className="mt-5 grid grid-cols-5 gap-2 text-center text-[10px] font-bold">
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
                        ? 'bg-indigo-600 text-white border-indigo-600 animate-pulse'
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

          {/* Verification Engine Evaluation Grid (V1-V9) */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                Verifier Step Breakdown (V1 to V9)
              </h3>
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
                    className={`p-3 rounded-lg border flex items-center justify-between text-xs transition-colors ${
                      st.passed
                        ? 'bg-emerald-50/40 border-emerald-200 text-slate-900'
                        : 'bg-rose-50/60 border-rose-300 text-rose-950 font-semibold'
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      {st.passed ? (
                        <CheckCircle2 size={16} className="text-emerald-600 shrink-0" />
                      ) : (
                        <XCircle size={16} className="text-rose-600 shrink-0" />
                      )}
                      <div>
                        <span className="font-mono font-bold text-slate-900 mr-2">{st.step}:</span>
                        <span>{st.name}</span>
                        {st.detail && (
                          <span className="block text-[11px] text-slate-500 font-mono mt-0.5">{st.detail}</span>
                        )}
                      </div>
                    </div>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                        st.passed
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-rose-100 text-rose-800'
                      }`}
                    >
                      {st.passed ? 'PASSED' : 'FAILED'}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-8 text-center text-slate-400 text-xs">
                Select a scenario and click execute to observe verifier step-by-step evaluations.
              </div>
            )}
          </div>

          {/* Proof & Public Inputs Inspection */}
          {response && (
            <div className="bg-slate-900 text-slate-100 rounded-xl p-6 border border-slate-800 shadow-md">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
                <div className="flex items-center gap-2">
                  <Terminal size={15} className="text-purple-400" />
                  <span className="text-xs font-mono font-bold uppercase tracking-wider text-purple-300">
                    Transmitted Proof Payload & Public Inputs
                  </span>
                </div>
                {response.proof && (
                  <button
                    type="button"
                    onClick={copyProof}
                    className="inline-flex items-center gap-1 text-[11px] font-mono text-indigo-400 hover:text-indigo-300"
                  >
                    {copied ? <Check size={12} /> : <Copy size={12} />}
                    <span>{copied ? 'Copied' : 'Copy Proof Bytes'}</span>
                  </button>
                )}
              </div>

              <div className="space-y-3 text-xs font-mono">
                <div className="flex justify-between py-1 border-b border-slate-800">
                  <span className="text-slate-400">Decision ID:</span>
                  <span className="text-slate-200">{response.decision_id}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-800">
                  <span className="text-slate-400">Policy ID:</span>
                  <span className="text-slate-200">{response.policy_id}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-800">
                  <span className="text-slate-400">Ledger Block Seq:</span>
                  <span className="text-emerald-400">#{response.ledger_seq}</span>
                </div>

                {response.public_inputs && (
                  <div className="pt-2">
                    <span className="text-slate-400 block mb-1">Public Inputs Vector:</span>
                    <pre className="p-3 rounded-lg bg-slate-950 text-[11px] text-slate-300 overflow-x-auto leading-relaxed border border-slate-800">
                      {JSON.stringify(response.public_inputs, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
