/**
 * Stale-session recovery helpers.
 *
 * When the backend returns 404 for a session-scoped endpoint (e.g.
 * `/sessions/{id}/chat`, `/generate`, `/audio`, ...), it means the in-memory
 * session has expired or was never created. The frontend should:
 *   1. drop the stored session id (localStorage + provider state)
 *   2. reset any module that holds derived state (window.__reportModuleReset)
 *   3. surface a single explanatory toast to the user
 *
 * This module exposes the building blocks; the wiring into provider state and
 * toasts lives in `handleStaleSession` (SessionProvider).
 *
 * NOTE on type-guard implementation:
 * The companion work introduces an `ApiError` class in `@/lib/api` whose
 * instances carry a numeric `status` field. We avoid a hard runtime
 * dependency on that class (so a temporary loading order or HMR quirk can't
 * break stale-session detection) and instead duck-type any thrown value with
 * a numeric `status` property.
 */

export const SESSION_STORAGE_KEY = "logopaedie_session_id";
export const STALE_SESSION_TOAST = "Sitzung abgelaufen. Bitte neu beginnen.";

interface StatusCarryingError extends Error {
  status: number;
}

/**
 * Type-guard: an Error with `status === 404` (i.e. an `ApiError` raised by
 * `fetchApi` for a session-scoped endpoint where the session id no longer
 * exists server-side).
 */
export function isStaleSessionError(err: unknown): err is StatusCarryingError {
  if (!(err instanceof Error)) return false;
  const status = (err as unknown as { status?: unknown }).status;
  return typeof status === "number" && status === 404;
}

/**
 * Clear the persisted session id and invoke any module reset hook.
 * Safe to call on the server — does nothing if `window` is undefined.
 */
export function clearStoredSession(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(SESSION_STORAGE_KEY);
  } catch {
    // localStorage may throw in private mode; we don't care.
  }
  const resetFn = (window as unknown as Record<string, unknown>).__reportModuleReset;
  if (typeof resetFn === "function") {
    (resetFn as () => void)();
  }
}
