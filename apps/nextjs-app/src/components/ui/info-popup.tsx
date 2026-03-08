'use client';

import { useEffect, useRef, useState } from 'react';

interface InfoPopupProps {
  children: React.ReactNode;
  className?: string;
}

export const InfoPopup = ({ children, className = '' }: InfoPopupProps) => {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [open]);

  return (
    <div ref={ref} className={`relative inline-flex items-center ${className}`}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="inline-flex items-center justify-center rounded-full text-muted-foreground/60 hover:text-muted-foreground transition-colors"
        aria-label="More info"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className="size-4"
        >
          <path
            fillRule="evenodd"
            d="M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Zm-7-4a1 1 0 1 1-2 0 1 1 0 0 1 2 0ZM9 9a.75.75 0 0 0 0 1.5h.253a.25.25 0 0 1 .244.304l-.459 2.066A1.75 1.75 0 0 0 10.747 15H11a.75.75 0 0 0 0-1.5h-.253a.25.25 0 0 1-.244-.304l.459-2.066A1.75 1.75 0 0 0 9.253 9H9Z"
            clipRule="evenodd"
          />
        </svg>
      </button>
      {open && (
        <div className="absolute left-1/2 top-full z-50 mt-1.5 w-64 -translate-x-1/2 rounded-lg border border-border/60 bg-card p-3 text-xs leading-relaxed text-muted-foreground shadow-lg backdrop-blur-sm">
          <div className="absolute -top-1.5 left-1/2 -translate-x-1/2 size-3 rotate-45 border-l border-t border-border/60 bg-card" />
          {children}
        </div>
      )}
    </div>
  );
};
