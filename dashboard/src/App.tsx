import { BrowserRouter, Link, Route, Routes, useLocation } from 'react-router-dom';
import { Activity, ArrowUpRight, Github, Shield } from 'lucide-react';
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

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans antialiased">
      <header className="no-print sticky top-0 z-30 border-b border-slate-200 bg-white/90 backdrop-blur-md">
        <div className="mx-auto flex w-[calc(100%-32px)] md:w-[calc(100%-48px)] xl:w-[calc(100%-64px)] max-w-[1600px] flex-wrap items-center justify-between gap-4 py-3">
          <Link to="/" aria-label="Sakshi home" className="shrink-0 flex items-center gap-2 group">
            <div className="w-8 h-8 rounded-lg bg-indigo-600 text-white flex items-center justify-center font-bold text-base shadow-sm group-hover:bg-indigo-700 transition-colors">
              <Shield size={18} />
            </div>
            <div>
              <span className="text-xl font-black tracking-tight text-slate-950 font-mono">SAKSHI</span>
              <span className="text-[10px] block font-mono text-slate-500 uppercase tracking-widest leading-none">ZK-Credit Gate</span>
            </div>
          </Link>
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
            <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-sm">
              <p className="font-mono text-xs uppercase tracking-widest text-slate-500">404 / Route not found</p>
              <h1 className="mt-3 text-3xl font-bold text-slate-900">The requested page could not be found.</h1>
              <Link className="mt-6 inline-flex px-4 py-2 bg-indigo-600 text-white rounded-lg font-semibold text-sm hover:bg-indigo-700 transition-colors" to="/">
                Back to overview
              </Link>
            </div>
          </main>
        } />
      </Routes>

      <footer className="no-print relative mt-16 border-t border-slate-200 bg-white">
        <div className="mx-auto flex w-[calc(100%-32px)] md:w-[calc(100%-48px)] xl:w-[calc(100%-64px)] max-w-[1600px] flex-wrap items-center justify-between gap-4 py-5 text-xs text-slate-500">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5 font-medium text-slate-700">
              <Activity size={14} className="text-emerald-600" /> Fail-closed by cryptographic design
            </span>
            <span>•</span>
            <span>All times shown in IST (UTC+5:30)</span>
            <span>•</span>
            <span className="font-mono">RBI Digital Lending Directions 2025</span>
          </div>
          <div>
            <a 
              href="https://github.com/Anshuman-VR/Sakshi" 
              target="_blank" 
              rel="noreferrer" 
              className="flex items-center gap-1.5 hover:text-slate-900 transition-colors"
            >
              Repository <Github size={13} /> <ArrowUpRight size={12} />
            </a>
          </div>
        </div>
      </footer>
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
