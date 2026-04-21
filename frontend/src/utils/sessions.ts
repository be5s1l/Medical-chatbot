/** Weekly session limiting utility backed by localStorage. */

export type SessionInfo = {
  used: number;
  remaining: number;
  resetDateISO: string;
  blockedMessage: string;
  isBlocked: boolean;
};

const KEY = "triage_sessions";
const MAX_PER_7_DAYS = 4;

function isoNow() {
  return new Date().toISOString();
}

function parseISO(d: string) {
  const dt = new Date(d);
  return Number.isNaN(dt.getTime()) ? null : dt;
}

function daysAgo(date: Date, days: number) {
  const d = new Date(date);
  d.setDate(d.getDate() - days);
  return d;
}

function nextResetDateISO(latestSessionISO: string | null): string {
  const now = new Date();
  const base = latestSessionISO ? parseISO(latestSessionISO) : null;
  const start = base ?? now;
  const reset = new Date(start);
  reset.setDate(reset.getDate() + 7);
  return reset.toISOString();
}

function loadSessions(): string[] {
  try {
    const raw = localStorage.getItem(KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter((x) => typeof x === "string") : [];
  } catch {
    return [];
  }
}

function saveSessions(sessions: string[]) {
  localStorage.setItem(KEY, JSON.stringify(sessions));
}

function pruneSessions(sessions: string[], now: Date): string[] {
  const cutoff = daysAgo(now, 7).getTime();
  return sessions
    .map((s) => ({ s, dt: parseISO(s) }))
    .filter((x) => x.dt && x.dt.getTime() >= cutoff)
    .sort((a, b) => a.dt!.getTime() - b.dt!.getTime())
    .map((x) => x.s);
}

/**
 * Returns current session usage and block messaging. Backend can later replace this with server logic.
 */
export function getSessionInfo(): SessionInfo {
  const now = new Date();
  const pruned = pruneSessions(loadSessions(), now);
  const used = pruned.length;
  const remaining = Math.max(0, MAX_PER_7_DAYS - used);
  const resetDateISO = nextResetDateISO(pruned[0] ?? null);
  const resetDate = new Date(resetDateISO).toLocaleDateString();
  const blockedMessage =
    `You've used all 4 of your weekly sessions. Your sessions will reset on ${resetDate}. ` +
    "If this is an emergency, please call emergency services immediately.";
  return { used, remaining, resetDateISO, blockedMessage, isBlocked: remaining <= 0 };
}

/**
 * Called when the user sends their first message in a new session.
 * Returns updated session info.
 */
export function startSessionIfNeeded(hasStarted: boolean): SessionInfo {
  if (hasStarted) return getSessionInfo();

  const now = new Date();
  const sessions = pruneSessions(loadSessions(), now);
  if (sessions.length >= MAX_PER_7_DAYS) return getSessionInfo();

  sessions.push(isoNow());
  saveSessions(sessions);
  return getSessionInfo();
}

