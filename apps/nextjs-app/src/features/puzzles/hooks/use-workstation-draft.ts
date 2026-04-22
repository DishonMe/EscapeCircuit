import Cookies from 'js-cookie';
import { useMemo, useRef, useCallback } from 'react';

import { useUser } from '@/lib/auth';
import {
  setWithTTL,
  getWithTTL,
  removeWithTTL,
  workstationKeyForUser,
  workstationKeyForAnon,
  WORKSTATION_CACHE_VERSION,
  WORKSTATION_TTL_MS,
} from '@/lib/cache-storage';
import type { Wire } from '@/types/api';
import { AUTH_TOKEN_COOKIE_NAME } from '@/utils/auth-constants';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

// Structural shape of a placed component as serialized in a draft. Kept local
// to avoid importing from the app/ route layer (see import/no-restricted-paths).
// Mirrors PlacedGridComponent in workstation-grid.tsx — the hook only needs a
// serializable shape; the consumer applies its own migrations.
type PlacedDraftComponent = {
  id: string;
  componentId: string;
  origin: { row: number; col: number };
  rotation: 0 | 90;
  isLocked?: boolean;
};

export type WorkstationDraft = {
  placed: PlacedDraftComponent[];
  wires: Wire[];
};

type AuthState =
  | { state: 'anonymous' }
  | { state: 'loading' }
  | { state: 'authenticated'; userId: string }
  | { state: 'error' };

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useWorkstationDraft(puzzleId: string): {
  authReady: boolean;
  storageKey: string | null;
  loadDraft: () => WorkstationDraft | null;
  saveDraft: (draft: WorkstationDraft) => void;
  clearDraft: () => void;
  flushNow: () => void;
} {
  const user = useUser();

  // Derive four-state auth. The order of checks matches the spec exactly:
  //
  //   1. No cookie → anonymous (query is disabled; isPending would be a
  //      stale/initial state, not a real loading state — so we check the
  //      cookie first before touching query status at all).
  //   2. Cookie present + isPending → loading.
  //   3. Cookie present + data.id → authenticated.
  //   4. Cookie present + isError (or any other terminal non-data state) → error.
  //
  // Reading the cookie at render time is safe here because this hook only
  // runs in client components (the puzzle workstation is a client-only route).
  const auth = useMemo((): AuthState => {
    const hasCookie =
      typeof window !== 'undefined'
        ? !!Cookies.get(AUTH_TOKEN_COOKIE_NAME)
        : false;

    if (!hasCookie) {
      return { state: 'anonymous' };
    }

    if (user.isPending) {
      return { state: 'loading' };
    }

    if (user.data?.id) {
      return { state: 'authenticated', userId: String(user.data.id) };
    }

    // Cookie present, query settled with error or unexpectedly no data.
    // We do NOT coerce to anonymous — the user may be legitimately logged in
    // and writing under the anon key could overwrite an authenticated draft.
    return { state: 'error' };
  }, [user.isPending, user.data]);

  // Derived stable values from auth + puzzleId.
  const storageKey = useMemo((): string | null => {
    if (auth.state === 'authenticated') {
      return workstationKeyForUser(puzzleId, auth.userId);
    }
    if (auth.state === 'anonymous') {
      return workstationKeyForAnon(puzzleId);
    }
    // loading or error → no I/O
    return null;
  }, [auth, puzzleId]);

  const envelopeUserId = useMemo((): string | null => {
    if (auth.state === 'authenticated') {
      return auth.userId;
    }
    return null;
  }, [auth]);

  const authReady = storageKey !== null;

  // Refs so callbacks can always close over the latest values without
  // needing to be recreated on each render (stable identity for consumers).
  const keyRef = useRef<string | null>(storageKey);
  const envelopeUserIdRef = useRef<string | null>(envelopeUserId);

  // Keep refs in sync on every render.
  keyRef.current = storageKey;
  envelopeUserIdRef.current = envelopeUserId;

  // ---------------------------------------------------------------------------
  // Callbacks — read from refs, never from closed-over values, so they stay
  // stable while always operating on the current scope.
  // ---------------------------------------------------------------------------

  const loadDraft = useCallback((): WorkstationDraft | null => {
    if (keyRef.current === null) return null;
    return getWithTTL<WorkstationDraft>(keyRef.current, {
      version: WORKSTATION_CACHE_VERSION,
      userId: envelopeUserIdRef.current,
    });
  }, []);

  const saveDraft = useCallback((draft: WorkstationDraft): void => {
    if (keyRef.current === null) return;
    setWithTTL(keyRef.current, draft, {
      ttlMs: WORKSTATION_TTL_MS,
      version: WORKSTATION_CACHE_VERSION,
      userId: envelopeUserIdRef.current,
    });
  }, []);

  const clearDraft = useCallback((): void => {
    if (keyRef.current === null) return;
    removeWithTTL(keyRef.current);
  }, []);

  // Placeholder for a future debounced variant. Synchronous writes make this
  // a no-op in v1 — when a debounced saveDraft is introduced, this will flush
  // any pending timer-delayed write immediately (e.g. on pagehide).
  const flushNow = useCallback((): void => {
    // no-op
  }, []);

  return {
    authReady,
    storageKey,
    loadDraft,
    saveDraft,
    clearDraft,
    flushNow,
  };
}
