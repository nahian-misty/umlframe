/** A per-browser UI preference restricted to known values; storage failures fall back silently. */
export function readStoredChoice<T extends string>(
  key: string,
  allowed: readonly T[],
  fallback: T,
): T {
  try {
    const value = localStorage.getItem(key);
    return allowed.includes(value as T) ? (value as T) : fallback;
  } catch {
    return fallback;
  }
}

export function writeStoredChoice(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    // The preference just won't persist; the UI still works for this session.
  }
}

/** Free text kept per browser (e.g. a draft the user would hate to retype). */
export function readStoredText(key: string): string {
  try {
    return localStorage.getItem(key) ?? '';
  } catch {
    return '';
  }
}

export function writeStoredText(key: string, value: string): void {
  writeStoredChoice(key, value);
}
