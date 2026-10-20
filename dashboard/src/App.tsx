import { BrowserRouter, Link, Route, Routes, useLocation } from 'react-router-dom';
import { Activity, ArrowUpRight, Github } from 'lucide-react';
import { ModeLinks } from './components/Brand';
import { LenderDashboard } from './pages/LenderDashboard';
import { BorrowerPortal } from './pages/BorrowerPortal';
import { BorrowerReceipt } from './pages/BorrowerReceipt';
import { DemoLab } from './pages/DemoLab';
import { AuditLedger } from './pages/AuditLedger';

function Shell() {
  const location = useLocation();
  const active = location.pathname.startsWith('/borrower') || location.pathname.startsWith('/receipt') ? 'borrower' : location.pathname.startsWith('/ledger') ? 'ledger' : location.pathname.startsWith('/demo') ? 'demo' : 'overview';
  return <div className="min-h-screen bg-paper text-ink">
    <div className="paper-grid fixed inset-0 pointer-events-none opacity-35" aria-hidden="true" />
    <div className="relative z-10">
      <header className="no-print sticky top-0 z-30 border-b-[1.5px] border-line bg-paper/95 backdrop-blur-sm">
        <div className="mx-auto flex w-[calc(100%-32px)] md:w-[calc(100%-48px)] xl:w-[calc(100%-64px)] max-w-[1600px] flex-wrap items-center justify-between gap-4 py-3">
          <Link to="/" aria-label="Sakshi home" className="shrink-0 text-lg font-extrabold lowercase tracking-[-.06em] text-ink">sakshi</Link>
          <div className="flex-1"><ModeLinks active={active}/></div>
        </div>
      </header>
      <Routes>
        <Route path="/" element={<LenderDashboard/>}/>
        <Route path="/lender" element={<LenderDashboard/>}/>
        <Route path="/borrower" element={<BorrowerPortal/>}/>
        <Route path="/receipt/:id" element={<BorrowerReceipt/>}/>
        <Route path="/demo" element={<DemoLab/>}/>
        <Route path="/ledger" element={<AuditLedger/>}/>
        <Route path="*" element={<main className="mx-auto max-w-3xl px-5 py-24"><div className="brutal-card bg-surface p-8"><p className="mono text-xs uppercase tracking-widest">404 / Route not found</p><h1 className="mt-3 text-4xl font-bold">The requested page could not be found.</h1><Link className="brutal-button mt-6 inline-flex bg-accent px-4 py-2 font-bold" to="/">Back to overview</Link></div></main>}/>
      </Routes>
      <footer className="no-print relative mt-12 border-t-[1.5px] border-line bg-surface/70">
        <div className="mx-auto flex w-[calc(100%-32px)] md:w-[calc(100%-48px)] xl:w-[calc(100%-64px)] max-w-[1600px] flex-wrap items-center justify-between gap-4 py-5">
          <div className="flex items-center gap-4 text-xs text-stone-600"><span className="flex items-center gap-1"><Activity size={13}/> Fail-closed by design</span><span>All times shown in IST</span><a href="https://github.com/Anshuman-VR/Sakshi" target="_blank" rel="noreferrer" className="flex items-center gap-1 hover:text-ink">Repository <Github size={13}/><ArrowUpRight size={12}/></a></div>
        </div>
      </footer>
    </div>
  </div>;
}
export function App() { return <BrowserRouter><Shell/></BrowserRouter>; }
