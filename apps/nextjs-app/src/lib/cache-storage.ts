// Generic TTL-localStorage utility.
// SSR-safe, throw-free, no external dependencies.

export type Envelope<T> = {
  value: T;
  expiresAt: number; // epoch ms
  version: string;
  userId: string | null;
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function isStorageAvailable(): boolean {
  return typeof window !== 'undefined';
}

function tryRemove(key: string): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.removeItem(key);
  } catch {
    // quota / private-mode errors — swallow silently
  }
}

// ---------------------------------------------------------------------------
// Core API
// ---------------------------------------------------------------------------

export function setWithTTL<T>(
  key: string,
  value: T,
  opts: { ttlMs: number; version: string; userId: string | null },
): void {
  if (!isStorageAvailable()) return;

  const envelope: Envelope<T> = {
    value,
    expiresAt: Date.now() + opts.ttlMs,
    version: opts.version,
    userId: opts.userId,
  };

  try {
    window.localStorage.setItem(key, JSON.stringify(envelope));
  } catch {
    // Quota exceeded, private-browsing write failures — swallow silently.
  }
}

export function getWithTTL<T>(
  key: string,
  opts: { version: string; userId: string | null },
): T | null {
  if (!isStorageAvailable()) return null;

  let raw: string | null = null;

  try {
    raw = window.localStorage.getItem(key);
  } catch {
    return null;
  }

  if (raw === null) return null;

  let envelope: Envelope<T>;

  try {
    envelope = JSON.parse(raw) as Envelope<T>;
  } catch {
    // Malformed JSON — remove and return null.
    tryRemove(key);
    return null;
  }

  // Basic shape check — if essential fields are missing it is malformed.
  if (
    envelope === null ||
    typeof envelope !== 'object' ||
    typeof envelope.expiresAt !== 'number' ||
    typeof envelope.version !== 'string' ||
    !(
      (envelope as any).userId === null ||
      typeof (envelope as any).userId === 'string'
    )
  ) {
    tryRemove(key);
    return null;
  }

  // Version mismatch — remove and return null.
  if (envelope.version !== opts.version) {
    tryRemove(key);
    return null;
  }

  // Expired — remove and return null.
  if (Date.now() > envelope.expiresAt) {
    tryRemove(key);
    return null;
  }

  // userId mismatch — paranoid cross-user guard. Return null but do NOT remove
  // (another user's entry may be sitting under a recycled key by accident; we
  // do not want to silently delete data that doesn't belong to the caller).
  if (envelope.userId !== opts.userId) {
    return null;
  }

  return envelope.value;
}

export function removeWithTTL(key: string): void {
  if (!isStorageAvailable()) return;
  tryRemove(key);
}

export function sweepExpired(prefix: string, version: string): void {
  if (!isStorageAvailable()) return;

  // Collect keys first, then remove. Mutating localStorage while iterating
  // via index shifts indices and causes entries to be skipped.
  const keysToCheck: string[] = [];

  try {
    for (let i = 0; i < window.localStorage.length; i++) {
      const k = window.localStorage.key(i);
      if (k !== null && k.startsWith(prefix)) {
        keysToCheck.push(k);
      }
    }
  } catch {
    return;
  }

  const now = Date.now();

  for (const key of keysToCheck) {
    let raw: string | null = null;

    try {
      raw = window.localStorage.getItem(key);
    } catch {
      continue;
    }

    if (raw === null) continue;

    let envelope: Envelope<unknown>;

    try {
      envelope = JSON.parse(raw) as Envelope<unknown>;
    } catch {
      // Malformed JSON — remove.
      tryRemove(key);
      continue;
    }

    // Malformed shape — remove.
    if (
      envelope === null ||
      typeof envelope !== 'object' ||
      typeof envelope.expiresAt !== 'number' ||
      typeof envelope.version !== 'string' ||
      !(
        (envelope as any).userId === null ||
        typeof (envelope as any).userId === 'string'
      )
    ) {
      tryRemove(key);
      continue;
    }

    // Version mismatch (e.g. legacy v2 entries) — remove.
    if (envelope.version !== version) {
      tryRemove(key);
      continue;
    }

    // Expired — remove.
    if (now > envelope.expiresAt) {
      tryRemove(key);
      continue;
    }

    // Valid entry, potentially belonging to a different user — leave intact.
    // User-level isolation is already provided by the key (distinct keys per
    // user per puzzle), so no userId check is needed here.
  }
}

// ---------------------------------------------------------------------------
// Workstation-specific constants and key builders
// ---------------------------------------------------------------------------

export const WORKSTATION_KEY_PREFIX = 'escapecircuit.workstation.state.';
export const WORKSTATION_CACHE_VERSION = 'v3';
export const WORKSTATION_TTL_MS = 2 * 60 * 60 * 1000; // 2 hours

export function workstationKeyForUser(
  puzzleId: string,
  userId: string,
): string {
  return `${WORKSTATION_KEY_PREFIX}${WORKSTATION_CACHE_VERSION}:user:${userId}:${puzzleId}`;
}

export function workstationKeyForAnon(puzzleId: string): string {
  return `${WORKSTATION_KEY_PREFIX}${WORKSTATION_CACHE_VERSION}:anon:${puzzleId}`;
}
