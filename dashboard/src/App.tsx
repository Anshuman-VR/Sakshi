import { BrowserRouter, Link, Route, Routes, useLocation } from 'react-router-dom';
import { Shield } from 'lucide-react';
import { ModeLinks } from './components/Brand';
import { LenderDashboard } from './pages/LenderDashboard';
import { BorrowerPortal } from './pages/BorrowerPortal';
import { BorrowerReceipt } from './pages/BorrowerReceipt';
import { LspPortal } from './pages/LspPortal';
import { DemoLab } from './pages/DemoLab';
import { AuditLedger } from './pages/AuditLedger';

function Shell() {
  const location = useLocation();
  const path = location.pathname;
  const active = path.startsWith('/borrower') || path.startsWith('/receipt') 
    ? 'borrower' 
    : path.startsWith('/lsp')
    ? 'lsp'
    : path.startsWith('/ledger') 
    ? 'ledger' 
    : path.startsWith('/demo') 
    ? 'demo' 
    : 'overview';

  const isBorrowerZone = active === 'borrower';
  const isLspZone = active === 'lsp';

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans antialiased">
      <header className="no-print sticky top-0 z-30 border-b border-slate-300 bg-white/95 backdrop-blur-md shadow-xs">
        <div className="mx-auto flex w-[calc(100%-32px)] md:w-[calc(100%-48px)] xl:w-[calc(100%-64px)] max-w-[1600px] flex-wrap items-center justify-between gap-4 py-3">
          {isBorrowerZone ? (
            <Link to="/borrower" aria-label="QuickLoan home" className="shrink-0 flex items-center gap-2.5 group">
              <div className="w-9 h-9 rounded-xl bg-emerald-600 text-white flex items-center justify-center font-bold text-base shadow-sm group-hover:bg-emerald-700 transition-colors">
                <Shield size={18} />
              </div>
              <div>
                <span className="text-xl font-black tracking-tight text-slate-950 font-sans">QuickLoan</span>
                <span className="text-[10px] block font-medium text-slate-600 tracking-wide leading-none">by Quick FinCorp Pvt Ltd</span>
              </div>
            </Link>
          ) : isLspZone ? (
            <Link to="/lsp" aria-label="Quick FinCorp home" className="shrink-0 flex items-center gap-2.5 group">
              <div className="w-9 h-9 rounded-xl bg-purple-700 text-white flex items-center justify-center font-bold text-base shadow-sm group-hover:bg-purple-800 transition-colors">
                <Shield size={18} />
              </div>
              <div>
                <span className="text-lg font-black tracking-tight text-slate-950 font-sans">Quick FinCorp Pvt Ltd</span>
                <span className="text-[10px] block font-mono text-purple-700 uppercase tracking-widest leading-none font-bold">LSP Dashboard</span>
              </div>
            </Link>
          ) : (
            <Link to="/" aria-label="Meridian Digital home" className="shrink-0 flex items-center gap-2.5 group">
              <div className="w-9 h-9 rounded-xl bg-indigo-700 text-white flex items-center justify-center font-bold text-base shadow-sm group-hover:bg-indigo-800 transition-colors">
                <Shield size={18} />
              </div>
              <div>
                <span className="text-lg font-black tracking-tight text-slate-950 font-sans">Meridian Digital</span>
                <span className="text-[10px] block font-mono text-slate-600 uppercase tracking-widest leading-none font-semibold">Sakshi ZK Credit Gate</span>
              </div>
            </Link>
          )}

          <div className="flex-1">
            <ModeLinks active={active} />
          </div>
        </div>
      </header>

      <Routes>
        <Route path="/" element={<LenderDashboard />} />
        <Route path="/lender" element={<LenderDashboard />} />
        <Route path="/borrower" element={<BorrowerPortal />} />
        <Route path="/receipt/:id" element={<BorrowerReceipt />} />
        <Route path="/lsp" element={<LspPortal />} />
        <Route path="/demo" element={<DemoLab />} />
        <Route path="/ledger" element={<AuditLedger />} />
        <Route path="*" element={
          <main className="mx-auto max-w-3xl px-5 py-24">
            <div className="bg-white rounded-2xl border border-slate-300 p-8 shadow-sm">
              <p className="font-mono text-xs uppercase tracking-widest text-slate-500 font-bold">404 / Route not found</p>
              <h1 className="mt-3 text-3xl font-extrabold text-slate-950">The requested page could not be found.</h1>
              <Link className="mt-6 inline-flex px-4 py-2 bg-indigo-600 text-white rounded-lg font-bold text-sm hover:bg-indigo-700 transition-colors" to="/">
                Back to overview
              </Link>
            </div>
          </main>
        } />
      </Routes>
    </div>
  );
}

export function App() { 
  return (
    <BrowserRouter>
      <Shell />
    </BrowserRouter>
  ); 
}
