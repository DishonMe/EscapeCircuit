'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

interface InfoPopupProps {
  children: React.ReactNode;
  className?: string;
}

export const InfoPopup = ({ children, className = '' }: InfoPopupProps) => {
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const popupRef = useRef<HTMLDivElement>(null);

  const updatePosition = useCallback(() => {
    if (!triggerRef.current) return;
    const rect = triggerRef.current.getBoundingClientRect();
    const popupWidth = 256; // w-64 = 16rem = 256px
    let left = rect.left + rect.width / 2 - popupWidth / 2;
    const top = rect.bottom + 6; // 6px gap below trigger

    // Keep within viewport horizontally
    if (left < 8) left = 8;
    if (left + popupWidth > window.innerWidth - 8) {
      left = window.innerWidth - popupWidth - 8;
    }

    setPos({ top, left });
  }, []);

  useEffect(() => {
    if (!open) return;
    updatePosition();

    const handleClick = (e: MouseEvent) => {
      const target = e.target as Node;
      if (
        triggerRef.current?.contains(target) ||
        popupRef.current?.contains(target)
      )
        return;
      setOpen(false);
    };

    const handleScrollOrResize = () => updatePosition();

    document.addEventListener('mousedown', handleClick);
    window.addEventListener('scroll', handleScrollOrResize, true);
    window.addEventListener('resize', handleScrollOrResize);
    return () => {
      document.removeEventListener('mousedown', handleClick);
      window.removeEventListener('scroll', handleScrollOrResize, true);
      window.removeEventListener('resize', handleScrollOrResize);
    };
  }, [open, updatePosition]);

  return (
    <span className={`inline-flex items-center ${className}`}>
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setOpen(!open)}
        className="inline-flex items-center justify-center rounded-full text-muted-foreground/60 transition-colors hover:text-muted-foreground"
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
      {open &&
        pos &&
        createPortal(
          <div
            ref={popupRef}
            className="fixed z-[9999] w-64 rounded-lg border border-border/60 bg-card p-3 text-xs leading-relaxed text-muted-foreground shadow-lg backdrop-blur-sm"
            style={{ top: pos.top, left: pos.left }}
          >
            <div
              className="absolute -top-1.5 size-3 rotate-45 border-l border-t border-border/60 bg-card"
              style={{
                left: triggerRef.current
                  ? triggerRef.current.getBoundingClientRect().left +
                    triggerRef.current.getBoundingClientRect().width / 2 -
                    pos.left -
                    6
                  : '50%',
              }}
            />
            {children}
          </div>,
          document.body,
        )}
    </span>
  );
};
