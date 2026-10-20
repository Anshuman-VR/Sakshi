import { ArrowUpRight } from 'lucide-react';
import { Link } from 'react-router-dom';

export function ModeLinks({ active }: { active: string }) {
  return (
    <nav className="flex flex-wrap items-center justify-end gap-2 text-sm" aria-label="Main navigation">
      <Link className={`nav-link ${active === 'overview' ? 'nav-active' : ''}`} to="/">Overview <ArrowUpRight size={13} /></Link>
      <Link className={`nav-link ${active === 'borrower' ? 'nav-active' : ''}`} to="/borrower">Borrower app <ArrowUpRight size={13} /></Link>
      <Link className={`nav-link ${active === 'ledger' ? 'nav-active' : ''}`} to="/ledger">Audit ledger <ArrowUpRight size={13} /></Link>
      <Link className={`nav-link ${active === 'demo' ? 'nav-active nav-demo' : ''}`} to="/demo">Demo lab <ArrowUpRight size={13} /></Link>
    </nav>
  );
}
