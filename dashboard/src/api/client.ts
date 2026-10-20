import axios from 'axios';
import type { DashboardSummary, DecisionRecord, LedgerRecord } from './types';

export const api = axios.create({ baseURL: '', timeout: 4500, headers: { 'Content-Type': 'application/json' } });
export const fetchHealth = async (): Promise<boolean> => {
  try { const response = await api.get('/healthz'); return response.status === 200; } catch { return false; }
};
export const fetchSummary = async (): Promise<DashboardSummary> => (await api.get<DashboardSummary>('/v1/dashboard/summary')).data;
export const fetchDecision = async (id: string): Promise<DecisionRecord> => (await api.get<DecisionRecord>(`/v1/decisions/${encodeURIComponent(id)}/status`)).data;
export const fetchLedger = async (): Promise<LedgerRecord[]> => {
  const response = await api.get('/v1/dashboard/ledger?limit=50');
  const body = response.data;
  if (Array.isArray(body)) return body as LedgerRecord[];
  if (Array.isArray(body.entries)) return body.entries as LedgerRecord[];
  if (Array.isArray(body.items)) return body.items as LedgerRecord[];
  return [];
};
