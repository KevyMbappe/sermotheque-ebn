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

/** Ordre canonique des livres — un catalogue biblique se parcourt dans l'ordre du canon. */
const BOOK_ORDER = [
  "Gen","Exod","Lev","Num","Deut","Josh","Judg","Ruth","1Sam","2Sam","1Kgs","2Kgs","1Chr","2Chr",
  "Ezra","Neh","Esth","Job","Ps","Prov","Eccl","Song","Isa","Jer","Lam","Ezek","Dan","Hos","Joel",
  "Amos","Obad","Jonah","Mic","Nah","Hab","Zeph","Hag","Zech","Mal",
  "Matt","Mark","Luke","John","Acts","Rom","1Cor","2Cor","Gal","Eph","Phil","Col","1Thess",
  "2Thess","1Tim","2Tim","Titus","Phlm","Heb","Jas","1Pet","2Pet","1John","2John","3John","Jude","Rev",
];
const BOOK_FR = {
  Gen:"Genèse",Exod:"Exode",Lev:"Lévitique",Num:"Nombres",Deut:"Deutéronome",Josh:"Josué",
  Judg:"Juges",Ruth:"Ruth","1Sam":"1 Samuel","2Sam":"2 Samuel","1Kgs":"1 Rois","2Kgs":"2 Rois",
  "1Chr":"1 Chroniques","2Chr":"2 Chroniques",Ezra:"Esdras",Neh:"Néhémie",Esth:"Esther",Job:"Job",
  Ps:"Psaumes",Prov:"Proverbes",Eccl:"Ecclésiaste",Song:"Cantique",Isa:"Ésaïe",Jer:"Jérémie",
  Lam:"Lamentations",Ezek:"Ézéchiel",Dan:"Daniel",Hos:"Osée",Joel:"Joël",Amos:"Amos",Obad:"Abdias",
  Jonah:"Jonas",Mic:"Michée",Nah:"Nahum",Hab:"Habacuc",Zeph:"Sophonie",Hag:"Aggée",Zech:"Zacharie",
  Mal:"Malachie",Matt:"Matthieu",Mark:"Marc",Luke:"Luc",John:"Jean",Acts:"Actes",Rom:"Romains",
  "1Cor":"1 Corinthiens","2Cor":"2 Corinthiens",Gal:"Galates",Eph:"Éphésiens",Phil:"Philippiens",
  Col:"Colossiens","1Thess":"1 Thessaloniciens","2Thess":"2 Thessaloniciens","1Tim":"1 Timothée",
  "2Tim":"2 Timothée",Titus:"Tite",Phlm:"Philémon",Heb:"Hébreux",Jas:"Jacques","1Pet":"1 Pierre",
  "2Pet":"2 Pierre","1John":"1 Jean","2John":"2 Jean","3John":"3 Jean",Jude:"Jude",Rev:"Apocalypse",
};
export const bookLabel = (osis) => BOOK_FR[osis] || osis;
export const bookRank = (osis) => {
  const i = BOOK_ORDER.indexOf(osis);
  return i === -1 ? 999 : i;
};

export const KIND_FR = {
  sermon: "Prédication",
  teaching: "Enseignement",
  qa: "Questions/Réponses",
  teaching_or_qa: "Enseignement",
};

/** Applique recherche + filtres. `filters` : { book, series, speaker, language, kind }. */
export function filterSermons(all, { q = "", ...filters } = {}) {
  const needle = fold(q).trim();
  return all.filter((s) => {
    if (filters.book && s.scripture_book !== filters.book) return false;
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
