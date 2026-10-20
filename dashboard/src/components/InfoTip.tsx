import { Info } from 'lucide-react';

/** Compact, keyboard-accessible explanation for domain-specific terms. */
export function InfoTip({ text, label = 'More information' }: { text: string; label?: string }) {
  return (
    <span className="group relative inline-flex align-middle">
      <button
        type="button"
        aria-label={label}
        aria-describedby={`info-${label.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`}
        className="ml-1 inline-flex h-4 w-4 items-center justify-center rounded-full text-stone-500 outline-none transition hover:bg-slate-100 hover:text-accent focus-visible:ring-2 focus-visible:ring-accent"
      >
        <Info size={13} strokeWidth={2} />
      </button>
      <span
        id={`info-${label.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`}
        role="tooltip"
        className="pointer-events-none invisible absolute left-1/2 top-full z-50 mt-2 w-60 -translate-x-1/2 rounded border border-slate-200 bg-white p-3 text-left text-xs font-normal leading-5 normal-case tracking-normal text-slate-700 opacity-0 shadow-lg transition duration-150 group-hover:visible group-hover:opacity-100 group-focus-within:visible group-focus-within:opacity-100"
      >
        {text}
      </span>
    </span>
  );
}
