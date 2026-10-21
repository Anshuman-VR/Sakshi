import { Link } from 'react-router-dom';

export function ModeLinks({ active }: { active: string }) {
  return (
    <nav className="flex flex-wrap items-center justify-end gap-1.5 sm:gap-2 text-xs sm:text-sm font-semibold" aria-label="Main navigation">
      <Link 
        className={`px-3.5 py-1.5 rounded-lg transition-all ${
          active === 'borrower' 
            ? 'bg-emerald-600 text-white shadow-sm font-bold' 
            : 'text-slate-700 hover:text-slate-950 hover:bg-slate-100 border border-transparent'
        }`} 
        to="/borrower"
      >
        <span>Borrower Portal</span>
      </Link>

      <Link 
        className={`px-3.5 py-1.5 rounded-lg transition-all ${
          active === 'overview' 
            ? 'bg-indigo-600 text-white shadow-sm font-bold' 
            : 'text-slate-700 hover:text-slate-950 hover:bg-slate-100 border border-transparent'
        }`} 
        to="/"
      >
        <span>Lender Dashboard</span>
      </Link>

      <Link 
        className={`px-3.5 py-1.5 rounded-lg transition-all ${
          active === 'lsp' 
            ? 'bg-purple-700 text-white shadow-sm font-bold' 
            : 'text-slate-700 hover:text-slate-950 hover:bg-slate-100 border border-transparent'
        }`} 
        to="/lsp"
      >
        <span>LSP Dashboard</span>
      </Link>

      <Link 
        className={`px-3.5 py-1.5 rounded-lg transition-all ${
          active === 'ledger' 
            ? 'bg-slate-800 text-white shadow-sm font-bold' 
            : 'text-slate-700 hover:text-slate-950 hover:bg-slate-100 border border-transparent'
        }`} 
        to="/ledger"
      >
        <span>Audit Ledger</span>
      </Link>

      <Link 
        className={`px-3.5 py-1.5 rounded-lg transition-all ${
          active === 'demo' 
            ? 'bg-rose-600 text-white shadow-sm font-bold' 
            : 'text-slate-700 hover:text-slate-950 hover:bg-slate-100 border border-transparent'
        }`} 
        to="/demo"
      >
        <span>Demo Lab</span>
      </Link>
    </nav>
  );
}
