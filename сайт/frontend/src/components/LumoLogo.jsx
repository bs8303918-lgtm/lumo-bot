import { useId } from 'react';

function LumoMarkSvg({ size = 32, className = '' }) {
  const gradId = useId();
  return (
    <svg viewBox="0 0 32 32" fill="none" width={size} height={size} className={className} aria-hidden>
      <defs>
        <linearGradient id={gradId} x1="16" y1="4" x2="26" y2="14" gradientUnits="userSpaceOnUse">
          <stop stopColor="#5eead4" />
          <stop stopColor="#38bdf8" />
          <stop offset="1" stopColor="#2563eb" />
        </linearGradient>
      </defs>
      <rect x="5" y="4" width="6.5" height="22" rx="3.25" fill="currentColor" />
      <rect x="5" y="19.5" width="17" height="6.5" rx="3.25" fill="currentColor" />
      <circle cx="22.5" cy="9.5" r="5.5" fill={`url(#${gradId})`} />
    </svg>
  );
}

export function LumoMark({ size = 32, className = '' }) {
  return <LumoMarkSvg size={size} className={className} />;
}

export default function LumoLogo({ showText = true, className = '', size = 'md', theme = 'auto' }) {
  const gradId = useId();
  const sizes = { sm: 'w-6 h-6', md: 'w-8 h-8', lg: 'w-10 h-10' };
  const markClass =
    theme === 'light'
      ? 'text-[#1e293b]'
      : theme === 'dark'
        ? 'text-white'
        : 'text-[#1e293b] dark:text-white';
  const textClass =
    theme === 'light'
      ? 'text-[#0f172a]'
      : theme === 'dark'
        ? 'text-white'
        : 'text-[#0f172a] dark:text-white';

  return (
    <div className={`flex items-center gap-2.5 shrink-0 ${className}`}>
      <svg
        viewBox="0 0 32 32"
        fill="none"
        className={`${sizes[size] ?? sizes.md} shrink-0`}
        aria-hidden
      >
        <defs>
          <linearGradient id={gradId} x1="16" y1="4" x2="26" y2="14" gradientUnits="userSpaceOnUse">
            <stop stopColor="#5eead4" />
            <stop stopColor="#38bdf8" />
            <stop offset="1" stopColor="#2563eb" />
          </linearGradient>
        </defs>
        <rect x="5" y="4" width="6.5" height="22" rx="3.25" fill="currentColor" className={markClass} />
        <rect x="5" y="19.5" width="17" height="6.5" rx="3.25" fill="currentColor" className={markClass} />
        <circle cx="22.5" cy="9.5" r="5.5" fill={`url(#${gradId})`} />
      </svg>
      {showText && (
        <span className={`text-lg font-bold tracking-tight ${textClass}`}>Lumo</span>
      )}
    </div>
  );
}
