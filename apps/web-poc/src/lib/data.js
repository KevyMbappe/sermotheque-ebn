/**
 * Accès aux données publiées (public/data/catalog.json) + recherche/filtres côté client.
 * À 131 fiches, tout tient en mémoire et un filtre naïf est instantané — pas d'index à bâtir.
 */

const BASE = import.meta.env.BASE_URL;

let cache = null;
export async function loadCatalog() {
  if (cache) return cache;
  const res = await fetch(`${BASE}data/catalog.json`);
  if (!res.ok) throw new Error(`catalogue introuvable (${res.status})`);
  cache = await res.json();
  return cache;
}

/** Le vocabulaire curé des thèmes (#57) : id → libellé, dans l'ordre du vocabulaire. */
let topicsCache = null;
export async function loadTopics() {
  if (topicsCache) return topicsCache;
  const res = await fetch(`${BASE}data/topics.json`);
  topicsCache = res.ok ? await res.json() : [];
  return topicsCache;
}

export async function loadVtt(id) {
  const res = await fetch(`${BASE}data/vtt/${id}.vtt`);
  if (!res.ok) throw new Error("transcription indisponible");
  return res.text();
}

/** Normalise pour comparer sans accents ni casse (recherche FR). */
export const fold = (s) =>
  (s || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "");

import { BOOK_ORDER, BOOK_FR } from "./books.js";

export const bookLabel = (osis) => BOOK_FR[osis] || osis;
export const bookRank = (osis) => {
  const i = BOOK_ORDER.indexOf(osis);
  return i === -1 ? 999 : i;
};

export const KIND_FR = {
  sermon: "Sermon",
  teaching: "Enseignement",
  qa: "Questions/Réponses",
  teaching_or_qa: "Enseignement",
};

/** Applique recherche + filtres. `filters` : { book, series, speaker, language, kind }. */
export function filterSermons(all, { q = "", ...filters } = {}) {
  const needle = fold(q).trim();
  return all.filter((s) => {
    if (filters.book && s.scripture_book !== filters.book) return false;
    if (filters.topic && !(s.topics_canonical || []).includes(filters.topic)) return false;
    if (filters.series && s.series_name !== filters.series) return false;
    if (filters.speaker && s.speaker !== filters.speaker) return false;
    if (filters.language && s.language !== filters.language) return false;
    if (filters.kind && s.kind !== filters.kind) return false;
    if (!needle) return true;
    // Le champ de recherche balaie tout ce que l'enrichissement a produit.
    const hay = fold(
      [s.title, s.description, s.summary, s.speaker, s.series_name, s.scripture_display,
       (s.topics || []).join(" "), (s.key_points || []).join(" ")].join(" ")
    );
    return needle.split(/\s+/).every((w) => hay.includes(w));
  });
}

/** Compte les occurrences d'une clé, trié — sert aux menus de filtres et aux vues d'agrégats. */
export function countBy(items, key, { rank } = {}) {
  const m = new Map();
  for (const it of items) {
    const v = it[key];
    if (v) m.set(v, (m.get(v) || 0) + 1);
  }
  const out = [...m.entries()].map(([value, count]) => ({ value, count }));
  out.sort(rank ? (a, b) => rank(a.value) - rank(b.value) : (a, b) => b.count - a.count);
  return out;
}

export const fmtDate = (d) =>
  d ? new Date(d + "T00:00:00").toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" }) : "";

export const fmtDuration = (sec) => {
  if (!sec) return "";
  const m = Math.round(sec / 60);
  return m >= 60 ? `${Math.floor(m / 60)} h ${String(m % 60).padStart(2, "0")}` : `${m} min`;
};
