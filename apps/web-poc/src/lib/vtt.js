/**
 * Parse WebVTT → cues [{ start, end, text }] en secondes.
 *
 * Port JS de `_vtt_cues` / `_ts_to_sec` (pipeline/build_entry.py) : mêmes fichiers, même
 * découpage, pour que les timestamps affichés ici correspondent exactement à ceux que
 * l'enrichissement a ancrés (chapitres, citations).
 */

/** "01:02.500" ou "01:02:03.500" → secondes. */
export function tsToSec(t) {
  const m = /(?:(\d{1,2}):)?(\d{1,2}):(\d{2})(?:\.(\d+))?/.exec(t);
  if (!m) return null;
  const [, h, mi, s] = m;
  return (h ? +h : 0) * 3600 + +mi * 60 + +s;
}

export function parseVtt(text) {
  const cues = [];
  for (const block of (text || "").trim().split(/\n\s*\n/)) {
    const lines = block.split("\n").filter((l) => l.trim());
    const ti = lines.findIndex((l) => l.includes("-->"));
    if (ti === -1) continue;
    const [from, to] = lines[ti].split("-->").map((s) => s.trim());
    const start = tsToSec(from);
    const body = lines.slice(ti + 1).join(" ").trim();
    if (start !== null && body) cues.push({ start, end: tsToSec(to), text: body });
  }
  return cues;
}

/** 754 → "12:34" (et "1:02:34" au-delà de l'heure). */
export function fmtTime(sec) {
  if (sec == null || Number.isNaN(sec)) return "";
  const s = Math.max(0, Math.floor(sec));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const r = s % 60;
  const pad = (n) => String(n).padStart(2, "0");
  return h ? `${h}:${pad(m)}:${pad(r)}` : `${m}:${pad(r)}`;
}

/** Index de la cue active à l'instant t (dernière cue commencée). -1 si aucune. */
export function activeCueIndex(cues, t) {
  if (!cues.length || t == null) return -1;
  let lo = 0, hi = cues.length - 1, found = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (cues[mid].start <= t) { found = mid; lo = mid + 1; } else hi = mid - 1;
  }
  return found;
}
