import { Check, Clock3, CircleX, FileQuestion, Hourglass } from 'lucide-react';
import type { DecisionStatus } from '../api/types';

const styles: Record<string, string> = {
  VERIFIED: 'bg-accent text-white', FAILED: 'bg-surface text-accent', EXPIRED: 'bg-surface text-stone-700',
  NOTICE_RECEIVED: 'bg-surface text-stone-700', NOT_FOUND: 'bg-surface text-stone-700', UNKNOWN: 'bg-surface text-stone-700'
};
const icons: Record<string, typeof Check> = { VERIFIED: Check, FAILED: CircleX, EXPIRED: Hourglass, NOTICE_RECEIVED: Clock3, NOT_FOUND: FileQuestion };
export function StatusPill({ status }: { status?: DecisionStatus | string | null }) {
  const value = status || 'UNKNOWN'; const Icon = icons[value] || FileQuestion;
  return <span className={`status-pill ${styles[value] || styles.UNKNOWN}`}><Icon size={12} strokeWidth={2.5}/>{value.replace('_', ' ')}</span>;
}
