/** Shared, browser-independent reference contract for the LSG reader and its build. */
import { BOOK_FR } from './books.js';
import { fold } from './fold.js';

export function parseOsis(value) {
  if (typeof value !== 'string') return null;
  const parts = value.split('-');
  if (parts.length > 2) return null;
  const point = (s) => {
    const m = /^([1-3]?[A-Za-z]+)(?:\.([1-9]\d*))?(?:\.([1-9]\d*))?$/.exec(s);
    return m && BOOK_FR[m[1]] ? { book: m[1], chapter: m[2] ? +m[2] : null, verse: m[3] ? +m[3] : null } : null;
  };
  const start = point(parts[0]), end = point(parts[1] || parts[0]);
  if (!start || !end || start.book !== end.book) return null;
  if ((start.chapter == null) !== (end.chapter == null)) return null;
  if (start.chapter > end.chapter || (start.chapter === end.chapter && (start.verse || 0) > (end.verse || 0))) return null;
  return { start, end, precision: start.chapter == null ? 'book' : start.verse != null && end.verse != null ? 'verse' : 'chapter' };
}

export function validReference(ref, manifest) {
  if (!ref) return false;
  return [ref.start, ref.end].every(p => {
    const chapters = manifest.books[p.book];
    return chapters && (p.chapter == null || (chapters[p.chapter - 1] != null && (p.verse == null || p.verse <= chapters[p.chapter - 1])));
  });
}

export function referenceLabel(value) {
  const ref = parseOsis(value);
  if (!ref) return value;
  const { start: a, end: b } = ref;
  const loc = p => `${p.chapter ?? ''}${p.verse == null ? '' : ':' + p.verse}`;
  const tail = a.chapter === b.chapter && a.verse === b.verse ? '' : `–${a.chapter === b.chapter && b.verse != null ? b.verse : loc(b)}`;
  return `${BOOK_FR[a.book]}${a.chapter == null ? '' : ' ' + loc(a)}${tail}`;
}

export function biblePath(value = 'Gen.1') {
  const ref = parseOsis(value);
  if (!ref) return '/bible/';
  return `/bible/${ref.start.book}/${ref.start.chapter || 1}/${ref.precision === 'book' ? '' : '?ref=' + encodeURIComponent(value)}`;
}

/** Human reference input: French labels or OSIS book names, chapter, optional verse/range. */
export function parseInput(value, manifest) {
  const direct = parseOsis(value.trim());
  if (validReference(direct, manifest)) return value.trim();
  const m = /^(.*?)\s+(\d+)(?:\s*[:.,]\s*(\d+))?(?:\s*[-–]\s*(?:(\d+)\s*[:.,]\s*)?(\d+))?$/.exec(value.trim());
  if (!m) return null;
  const normalize = s => fold(s).replace(/\s+/g, '');
  const book = Object.keys(manifest.books).find(b => [b, BOOK_FR[b]].some(n => normalize(n) === normalize(m[1])));
  if (!book) return null;
  // Single-chapter books: “Jude 24-25” means verses.
  const single = manifest.books[book].length === 1 && !m[3] && !m[4];
  const start = single ? `${book}.1.${m[2]}` : `${book}.${m[2]}${m[3] ? '.' + m[3] : ''}`;
  const end = !m[5] ? '' : single ? `${book}.1.${m[5]}` : m[3] ? `${book}.${m[4] || m[2]}.${m[5]}` : `${book}.${m[5]}`;
  const id = start + (end ? '-' + end : '');
  return validReference(parseOsis(id), manifest) ? id : null;
}

const ordinal = p => p.chapter * 1000 + p.verse;
export function overlaps(ref, selection, manifest) {
  if (!validReference(ref, manifest) || !validReference(selection, manifest) || ref.start.book !== selection.start.book) return false;
  const bounds = r => {
    const chapters = manifest.books[r.start.book];
    const first = r.start.chapter || 1, last = r.end.chapter || chapters.length;
    return [ordinal({chapter:first, verse:r.start.verse || 1}), ordinal({chapter:last, verse:r.end.verse || chapters[last - 1]})];
  };
  const [a,b] = bounds(ref), [c,d] = bounds(selection);
  return a <= d && c <= b;
}

export function buildBibleIndex(sermons, manifest) {
  const index = {}, issues = [];
  for (const s of sermons) {
    const refs = [['preached', s.scripture_osis], ...(s.scripture_refs_osis || []).map(r => ['cited',r])];
    for (const [relation, value] of refs) {
      if (!value) continue;
      const ref = parseOsis(value);
      if (!validReference(ref, manifest)) { issues.push({id:s.id, reference:value, reason:'Invalid or unsupported LSG reference'}); continue; }
      (index[ref.start.book] ||= []).push({id:s.id, relation, reference:value});
    }
  }
  return { index, issues };
}

/** One result per sermon. Exact passage > exact citation > chapter context > book context. */
export function matchSermons(entries, selected, manifest) {
  const selection = parseOsis(selected), winners = new Map();
  for (const entry of entries || []) {
    const ref = parseOsis(entry.reference);
    if (!overlaps(ref, selection, manifest)) continue;
    const group = ref.precision === 'book' ? 'book' : ref.precision === 'chapter' && selection.precision === 'verse' ? 'chapter' : entry.relation;
    const rank = {preached:0, cited:1, chapter:2, book:3}[group];
    const old = winners.get(entry.id);
    if (!old || rank < old.rank) winners.set(entry.id, {...entry, group, rank});
  }
  return [...winners.values()].sort((a,b) => a.rank - b.rank || a.id.localeCompare(b.id));
}
