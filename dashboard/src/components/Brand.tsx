import { ArrowUpRight, ShieldCheck, User, Cpu, Database, PlayCircle } from 'lucide-react';
import { Link } from 'react-router-dom';

export function ModeLinks({ active }: { active: string }) {
  return (
    <nav className="flex flex-wrap items-center justify-end gap-1.5 sm:gap-2 text-xs sm:text-sm" aria-label="Main navigation">
      <Link 
        className={`nav-link flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition-all ${
          active === 'borrower' 
            ? 'bg-emerald-50 text-emerald-800 border border-emerald-300 shadow-sm font-semibold' 
            : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100 border border-transparent'
        }`} 
        to="/borrower"
      >
        <User size={14} className="text-emerald-600" />
        <span>Borrower DLA</span>
      </Link>

      <Link 
        className={`nav-link flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition-all ${
          active === 'overview' 
            ? 'bg-indigo-50 text-indigo-900 border border-indigo-300 shadow-sm font-semibold' 
            : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100 border border-transparent'
        }`} 
        to="/"
      >
        <ShieldCheck size={14} className="text-indigo-600" />
        <span>Lender Ops</span>
      </Link>

      <Link 
        className={`nav-link flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition-all ${
          active === 'lsp' 
            ? 'bg-purple-50 text-purple-900 border border-purple-300 shadow-sm font-semibold' 
            : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100 border border-transparent'
        }`} 
        to="/lsp"
      >
        <Cpu size={14} className="text-purple-600" />
        <span>LSP Prover Zone</span>
      </Link>

      <Link 
        className={`nav-link flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition-all ${
          active === 'ledger' 
            ? 'bg-blue-50 text-blue-900 border border-blue-300 shadow-sm font-semibold' 
            : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100 border border-transparent'
        }`} 
        to="/ledger"
      >
        <Database size={14} className="text-blue-600" />
        <span>Audit Ledger</span>
      </Link>

      <Link 
        className={`nav-link flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition-all ${
          active === 'demo' 
            ? 'bg-rose-50 text-rose-800 border border-rose-300 shadow-sm font-semibold' 
            : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100 border border-transparent'
        }`} 
        to="/demo"
      >
        <PlayCircle size={14} className="text-rose-600" />
        <span>Demo Lab</span>
        <ArrowUpRight size={12} className="opacity-60" />
      </Link>
    </nav>
  );
}
