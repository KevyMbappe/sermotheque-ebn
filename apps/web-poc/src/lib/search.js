import { fold } from "./fold.js";

/**
 * Recherche plein-texte sur le contenu éditorial des sermons.
 *
 * Ce que faisait l'ancienne version : un `includes` sur cinq champs, résultats rangés par
 * date. On ne trouvait donc pas un mot présent dans une citation, une question de réflexion
 * ou une référence — et rien ne disait POURQUOI un sermon ressortait.
 *
 * Ce qui change ici :
 *   1. **Tout le contenu est indexé**, y compris citations, questions et références.
 *   2. **Les champs ne pèsent pas pareil** — un mot dans le titre vaut plus que le même mot
 *      perdu dans un point clé. Les résultats sont classés par pertinence, plus par date.
 *   3. **On montre où ça correspond** : un extrait avec le terme en évidence, pour qu'un
 *      résultat inattendu s'explique de lui-même au lieu d'avoir l'air d'un bug.
 *
 * Volontairement hors périmètre : les transcriptions (17 Mo pour 131 sermons). Les chercher
 * demande un index pré-calculé au build — c'est un autre chantier.
 */

// Poids par champ. L'écart compte plus que les valeurs : titre et passage biblique
// dominent, le corps ne départage que les ex æquo.
const FIELDS = [
  { key: "title", weight: 10, label: "titre" },
  { key: "scripture", weight: 8, label: "passage" },
  { key: "topics", weight: 5, label: "thème" },
  { key: "speaker", weight: 4, label: "prédicateur" },
  { key: "series", weight: 4, label: "série" },
  { key: "description", weight: 3, label: "accroche" },
  { key: "summary", weight: 3, label: "résumé" },
  { key: "points", weight: 2, label: "points clés" },
  { key: "quotes", weight: 2, label: "citation" },
  { key: "questions", weight: 1, label: "question" },
  { key: "refs", weight: 1, label: "références" },
];

const join = (xs) => (xs || []).filter(Boolean).join(" · ");

// Marqueurs de surlignage : des caractères de contrôle, impossibles dans du texte rédigé.
export const MARK_OPEN = "\u0001";
export const MARK_CLOSE = "\u0002";

/** Découpe un extrait marqué en segments { text, hit } — à rendre en JSX, pas en HTML. */
export function markedParts(snippet) {
  const parts = [];
  for (const chunk of String(snippet || "").split(MARK_OPEN)) {
    const [hit, ...rest] = chunk.split(MARK_CLOSE);
    if (rest.length) { parts.push({ text: hit, hit: true }); if (rest[0]) parts.push({ text: rest[0], hit: false }); }
    else if (hit) parts.push({ text: hit, hit: false });
  }
  return parts;
}

/** Les champs textuels d'un sermon, tels qu'ils seront cherchés et cités en extrait. */
function documentOf(s) {
  return {
    title: [s.title, s.raw_title].filter(Boolean).join(" "),
    scripture: [s.scripture_display, s.scripture_book].filter(Boolean).join(" "),
    topics: join(s.topics),
    speaker: s.speaker || "",
    series: s.series_name || "",
    description: s.description || "",
    summary: s.summary || "",
    points: join(s.key_points),
    quotes: join((s.key_quotes || []).map((q) => q.text)),
    questions: join(s.questions),
    refs: join([...(s.references || []), ...(s.scripture_refs || [])]),
  };
}

// L'index est bâti une fois par jeu de données, pas à chaque frappe.
let cache = { rows: null, index: null };
function indexOf(rows) {
  if (cache.rows === rows) return cache.index;
  const index = rows.map((s) => {
    const doc = documentOf(s);
    const folded = {};
    for (const f of FIELDS) folded[f.key] = fold(doc[f.key]);
    return { s, doc, folded };
  });
  cache = { rows, index };
  return index;
}

/**
 * Extrait autour de la première occurrence. Les termes trouvés sont encadrés par deux
 * caractères de contrôle (MARK_OPEN / MARK_CLOSE) que le composant convertit en <mark> :
 * on ne fabrique JAMAIS de HTML ici, sinon un titre contenant « <b> » serait une injection.
 * (des marqueurs que le rendu convertit en <mark> — on ne fabrique pas de HTML ici).
 *
 * `fold` ne change pas la longueur du texte en français (les accents précomposés se
 * décomposent puis perdent leur diacritique, soit 1 caractère pour 1). On peut donc
 * découper l'ORIGINAL aux positions trouvées dans la version pliée. Le repli sur le texte
 * plié couvre le cas contraire plutôt que d'afficher un extrait décalé.
 */
function snippetOf(original, foldedText, terms, width = 150) {
  const aligned = original.length === foldedText.length ? original : foldedText;
  let at = -1;
  for (const t of terms) {
    const i = foldedText.indexOf(t);
    if (i !== -1 && (at === -1 || i < at)) at = i;
  }
  if (at === -1) return "";
  const start = Math.max(0, at - Math.floor(width / 3));
  const end = Math.min(aligned.length, start + width);
  let text = aligned.slice(start, end);
  let folded = foldedText.slice(start, end);

  // Marquage à rebours pour ne pas décaler les positions suivantes.
  const spans = [];
  for (const t of terms) {
    let i = folded.indexOf(t);
    while (i !== -1) { spans.push([i, i + t.length]); i = folded.indexOf(t, i + t.length); }
  }
  spans.sort((a, b) => b[0] - a[0]);
  for (const [a, b] of spans) {
    text = text.slice(0, a) + MARK_OPEN + text.slice(a, b) + MARK_CLOSE + text.slice(b);
  }

  return (start > 0 ? "…" : "") + text.trim() + (end < aligned.length ? "…" : "");
}

/**
 * Cherche `q` dans `rows`. Retourne les sermons classés par pertinence, chacun avec
 * `_match` = { field, snippet } quand un extrait est disponible.
 * Une requête vide rend la liste inchangée (l'ordre par défaut reste la date).
 */
export function searchSermons(rows, q) {
  const terms = fold(q).trim().split(/\s+/).filter(Boolean);
  if (!terms.length) return rows;

  const scored = [];
  for (const entry of indexOf(rows)) {
    let score = 0;
    let best = null;
    // Tous les termes doivent apparaître quelque part dans le document (ET, pas OU).
    const seen = new Set();
    for (const f of FIELDS) {
      const hay = entry.folded[f.key];
      if (!hay) continue;
      for (const t of terms) {
        if (!hay.includes(t)) continue;
        seen.add(t);
        score += f.weight;
        if (!best) best = f;
      }
    }
    if (seen.size !== terms.length) continue;
    const snippet = best ? snippetOf(entry.doc[best.key], entry.folded[best.key], terms) : "";
    scored.push({ s: entry.s, score, match: best ? { field: best.label, snippet } : null });
  }

  scored.sort((a, b) => b.score - a.score || (b.s.date || "").localeCompare(a.s.date || ""));
  return scored.map(({ s, match }) => (match ? { ...s, _match: match } : s));
}
