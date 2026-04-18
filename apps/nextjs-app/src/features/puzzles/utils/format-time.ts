/**
 * Formats a duration in seconds as mm:ss.
 * e.g. 83 → "01:23"
 */
export function formatTime(seconds: number | null | undefined): string {
  if (seconds == null) return '—';
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}
