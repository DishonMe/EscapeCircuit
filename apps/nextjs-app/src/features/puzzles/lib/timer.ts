/**
 * Decide whether to trust a `started_at` timestamp returned by the backend's
 * `start_attempt` response.
 *
 * The backend already closes attempts older than `min(24h, time_limit * 4)`
 * (or 24h for no-limit puzzles) on `start_attempt`, so under normal operation
 * any `started_at` we receive should pass this check. This client-side guard
 * is a belt-and-braces safeguard against unusual races or unexpected backend
 * state — it keeps the visible timer honest even if the server hands back a
 * far-past timestamp.
 *
 * Returns `true` when the implied elapsed time is non-negative and within the
 * configured plausibility bound; `false` otherwise (caller should keep its
 * local mount-time baseline).
 */
export const isPlausibleStartedAt = (
  startedAtMs: number,
  nowMs: number,
  timeLimitSeconds: number | null | undefined,
): boolean => {
  if (!Number.isFinite(startedAtMs) || !Number.isFinite(nowMs)) {
    return false;
  }
  const elapsedSeconds = (nowMs - startedAtMs) / 1000;
  if (elapsedSeconds < 0) {
    return false;
  }
  const day = 24 * 3600;
  const limit =
    typeof timeLimitSeconds === 'number' && timeLimitSeconds > 0
      ? Math.min(day, timeLimitSeconds * 4)
      : day;
  return elapsedSeconds <= limit;
};
