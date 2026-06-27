export default function LumoLogo({ showText = true, className = '' }) {
  return (
    <div className={`flex items-center gap-2 shrink-0 ${className}`}>
      <svg viewBox="0 0 28 28" fill="none" className="w-7 h-7 shrink-0" aria-hidden>
        <rect x="4" y="3" width="5" height="22" rx="2.5" fill="currentColor" className="text-[var(--lumo-text)]" />
        <circle cx="20" cy="8" r="5" fill="var(--lumo-accent)" />
      </svg>
      {showText && (
        <span className="text-[17px] font-bold tracking-tight" style={{ color: 'var(--lumo-text)' }}>
          Lumo
        </span>
      )}
    </div>
  );
}
