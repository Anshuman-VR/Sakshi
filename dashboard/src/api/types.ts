export type DecisionStatus = 'NOT_FOUND' | 'NOTICE_RECEIVED' | 'VERIFIED' | 'FAILED' | 'EXPIRED';
export interface DecisionRecord {
  decision_id: string; status: DecisionStatus; decision?: number | null; model_commitment?: string | null; policy_id?: string | null;
  verified_at?: string | null; ledger_seq?: number | null; failure_reason?: string | null; sla_deadline?: string | null;
}
export interface DashboardSummary {
  total_decisions: number; verified: number; failed: number; pending: number; expired: number;
  failure_breakdown?: Record<string, number>; recent_decisions: DecisionRecord[];
  proof_latency_p50_ms?: number | null; proof_latency_p95_ms?: number | null; ledger_seq: number; chain_valid: boolean;
  active_models?: Array<Record<string, unknown>>; active_policies?: Array<Record<string, unknown>>;
}
export interface LedgerRecord {
  seq: number; decision_id: string; verification_id?: string; status: string; reason?: string | null;
  policy_id?: string; model_commitment?: string; proof_hash?: string; ts?: string; prev_hash?: string; row_hash?: string;
}
