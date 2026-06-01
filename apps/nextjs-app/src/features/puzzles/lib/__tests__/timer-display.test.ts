import { describe, expect, it } from 'vitest';

import { formatCountdown, timerVisualState } from '../timer-display';

/**
 * ADD 7.4 — "Usability: Timer Visual Cues": the timer must transition
 * green → amber at the final 10% → red at zero, then show a "+" stopwatch that
 * counts up. This pins that pure logic.
 */
describe('timerVisualState', () => {
  it('is "no-limit" (slate, counting up) when there is no time limit', () => {
    expect(timerVisualState(42, null).state).toBe('no-limit');
    expect(timerVisualState(42, 0).state).toBe('no-limit');
    expect(timerVisualState(42, null).label).toBe('0:42');
  });

  it('is "normal" (green) while more than 10% of the limit remains', () => {
    // 100s limit, 50s elapsed → 50% remaining
    const r = timerVisualState(50, 100);
    expect(r.state).toBe('normal');
    expect(r.label).toBe('0:50');
  });

  it('is "warning" (amber) at exactly 10% remaining and below', () => {
    // 100s limit, 90s elapsed → exactly 10% remaining
    expect(timerVisualState(90, 100).state).toBe('warning');
    // 100s limit, 95s elapsed → 5% remaining
    expect(timerVisualState(95, 100).state).toBe('warning');
  });

  it('is "expired" (red) at zero and below, with a "+" stopwatch label', () => {
    expect(timerVisualState(100, 100).state).toBe('expired');
    const over = timerVisualState(125, 100); // 25s over
    expect(over.state).toBe('expired');
    expect(over.label).toBe('+0:25');
  });
});

describe('formatCountdown', () => {
  it('formats seconds as M:SS with zero-padding', () => {
    expect(formatCountdown(5)).toBe('0:05');
    expect(formatCountdown(65)).toBe('1:05');
    expect(formatCountdown(600)).toBe('10:00');
  });

  it('uses the absolute value (sign is handled by the caller)', () => {
    expect(formatCountdown(-25)).toBe('0:25');
  });
});
