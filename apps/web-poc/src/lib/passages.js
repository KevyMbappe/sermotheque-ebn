/**
 * Index inversé des passages : « quels sermons exposent Romains 8, et lesquels le citent ? »
 *
 * Rendu possible par la décision #56 (pipeline) : les passages cités dans le corps des
 * sermons, jusque-là en texte libre français, sont désormais normalisés en ids OSIS
 * (`scripture_refs_osis`). Le catalogue passe ainsi de 28 livres atteignables (par
 * l'Écriture principale seule) à 54.
 *
 * On distingue deux relations, parce qu'elles ne valent pas la même chose pour un lecteur :
 *   • EXPOSÉ — le passage est le texte du sermon (`preached` / `scripture_osis`)
 *   • CITÉ   — le passage est convoqué à l'intérieur du sermon (`scripture_refs_osis`)
 *
 * L'index est calculé côté client : ~1 250 citations aujourd'hui, ~4 600 une fois les 517
 * enrichies. C'est instantané, et surtout ça garde UNE source de vérité (le catalogue
 * projeté) au lieu d'un second fichier à maintenir en cohérence.
 */

/** `Gen.9`, `John.1.1`, `Gen.9-Gen.10`, `Rom` → les couples {book, chapter} couverts. */
export function osisPoints(id) {
  if (!id) return [];
  const [from, to] = String(id).split("-");
  const a = part(from);
  if (!a) return [];
  const b = to ? part(to) : null;

  // Plage à l'intérieur d'un même livre : on indexe TOUS les chapitres traversés, sinon
  // « Genèse 9-10 » resterait introuvable en cherchant Genèse 10.
  if (b && b.book === a.book && a.chapter != null && b.chapter != null && b.chapter > a.chapter) {
    const out = [];
    for (let c = a.chapter; c <= b.chapter; c++) out.push({ book: a.book, chapter: c });
    return out;
  }
  // Plage entre deux livres : on garde les deux extrémités plutôt que d'inventer ce qu'il
  // y a entre les deux (l'ordre du canon ne dit rien du nombre de chapitres).
  if (b && b.book !== a.book) return [a, b];
  return [a];
}

function part(s) {
  if (!s) return null;
  const bits = String(s).trim().split(".");
  const book = bits[0];
  if (!book) return null;
  const chapter = bits.length > 1 ? Number(bits[1]) : null;
  return { book, chapter: Number.isFinite(chapter) ? chapter : null };
}

/** Étiquette lisible d'un id OSIS, ex. `Rom.8` → « Romains 8 ». */
export function osisLabel(id, bookLabel) {
  const p = part(String(id).split("-")[0]);
  if (!p) return id;
  const [, to] = String(id).split("-");
  const end = to ? part(to) : null;
  const base = `${bookLabel(p.book)}${p.chapter != null ? ` ${p.chapter}` : ""}`;
  if (end && end.chapter != null && (end.book !== p.book || end.chapter !== p.chapter)) {
    return `${base}–${end.book !== p.book ? `${bookLabel(end.book)} ` : ""}${end.chapter}`;
  }
  return base;
}

/**
 * Construit l'index. Retourne, par livre :
 *   { book, preached: Sermon[], cited: Sermon[], chapters: [{ chapter, preached, cited }] }
 * Un même sermon n'apparaît qu'une fois par liste, même s'il cite dix fois le même chapitre.
 */
export function buildPassageIndex(sermons) {
  const books = new Map();

  const touch = (book) => {
    if (!books.has(book)) books.set(book, { book, preached: new Map(), cited: new Map(), chapters: new Map() });
    return books.get(book);
  };
  const chapterOf = (entry, chapter) => {
    const key = chapter == null ? 0 : chapter; // 0 = allusion au livre entier
    if (!entry.chapters.has(key)) entry.chapters.set(key, { chapter: key, preached: new Map(), cited: new Map() });
    return entry.chapters.get(key);
  };

  for (const s of sermons) {
    // Exposé : l'Écriture principale, celle qui titre le sermon.
    for (const pt of osisPoints(s.scripture_osis)) {
      const b = touch(pt.book);
      b.preached.set(s.id, s);
      chapterOf(b, pt.chapter).preached.set(s.id, s);
    }
    // Cité : les passages convoqués dans le corps (#56).
    for (const ref of s.scripture_refs_osis || []) {
      for (const pt of osisPoints(ref)) {
        const b = touch(pt.book);
        // Un passage exposé n'est pas re-listé comme cité : la relation la plus forte gagne.
        if (!b.preached.has(s.id)) b.cited.set(s.id, s);
        const ch = chapterOf(b, pt.chapter);
        if (!ch.preached.has(s.id)) ch.cited.set(s.id, s);
      }
    }
  }

  const byDate = (a, b) => (a.date || "").localeCompare(b.date || "");
  return [...books.values()].map((b) => ({
    book: b.book,
    preached: [...b.preached.values()].sort(byDate),
    cited: [...b.cited.values()].sort(byDate),
    chapters: [...b.chapters.values()]
      .sort((x, y) => x.chapter - y.chapter)
      .map((c) => ({
        chapter: c.chapter,
        preached: [...c.preached.values()].sort(byDate),
        cited: [...c.cited.values()].sort(byDate),
      })),
  }));
}
