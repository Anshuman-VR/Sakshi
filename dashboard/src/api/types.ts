export type DecisionStatus = 'NOT_FOUND' | 'NOTICE_RECEIVED' | 'VERIFIED' | 'FAILED' | 'EXPIRED';

export interface PublicInputsData {
  policy_hash: string;
  C: string;
  X: string;
  decision: number;
  threshold: number;
  epoch: number;
}

export interface DecisionRecord {
  decision_id: string;
  status: DecisionStatus;
  decision?: number | null;
  model_commitment?: string | null;
  policy_id?: string | null;
  verified_at?: string | null;
  ledger_seq?: number | null;
  failure_reason?: string | null;
  sla_deadline?: string | null;
  proof_hash?: string | null;
  proof_size_bytes?: number | null;
  proof_snippet?: string | null;
  public_inputs?: PublicInputsData | null;
  application_id_hash?: string | null;
}

export interface DashboardSummary {
  total_decisions: number;
  verified: number;
  failed: number;
  pending: number;
  expired: number;
  failure_breakdown?: Record<string, number>;
  recent_decisions: DecisionRecord[];
  proof_latency_p50_ms?: number | null;
  proof_latency_p95_ms?: number | null;
  ledger_seq: number;
  chain_valid: boolean;
  active_models?: Array<Record<string, unknown>>;
  active_policies?: Array<Record<string, unknown>>;
}

export interface LedgerRecord {
  seq: number;
  decision_id: string;
  verification_id?: string;
  status: string;
  reason?: string | null;
  policy_id?: string;
  model_commitment?: string;
  proof_hash?: string;
  ts?: string;
  prev_hash?: string;
  row_hash?: string;
}

export interface VerificationStep {
  step: string;
  name: string;
  description: string;
  passed: boolean;
  expected?: string | number;
  actual?: string | number;
  binding_status?: string;
}

export interface ApplyLoanRequest {
  application_id?: string;
  policy_id?: string;
  persona?: string;
  features?: Record<string, number>;
  tamper?: string;
}

export interface ApplyLoanResponse {
  decision_id: string;
  application_id: string;
  status: 'VERIFIED' | 'FAILED' | 'NOTICE_RECEIVED' | 'EXPIRED';
  decision: number;
  decision_label: 'APPROVED' | 'REJECTED';
  policy_id: string;
  model_commitment: string;
  ledger_seq: number;
  verified_at: string | null;
  failure_reason: string | null;
  failed_at_step?: string;
  proof?: string;
  proof_hash?: string;
  proof_size_bytes?: number;
  public_inputs?: PublicInputsData;
  steps_evaluated?: VerificationStep[];
}
