import { useEffect, useState } from "react";
import { bookLabel, bookRank, countBy, filterSermons, KIND_FR, kindOf, loadTopics } from "../lib/data.js";

/**
 * Filtres croisés.
 *
 * Règle qui gouverne tout ici : **un menu ne se contraint jamais lui-même**. Les compteurs
 * d'un menu sont calculés sur le corpus filtré par TOUS LES AUTRES critères, le sien exclu.
 *
 * Sans cette règle (le bug corrigé le 2026-08-01) : on choisissait « Galates », on rouvrait
 * le menu des livres, et les 53 autres livres affichaient 0 — donc grisés. Le menu semblait
 * cassé alors qu'il décrivait fidèlement une sélection déjà faite. Aucune option n'est plus
 * désactivée non plus : une liste grise inquiète, et un choix sans résultat reste réversible
 * (le compte le dit, « Réinitialiser » est à côté).
 */
export default function Filters({ all, filters, onChange, q, onQuery }) {
  // Corpus vu par un menu donné : tous les filtres actifs SAUF le sien.
  const without = (key) => filterSermons(all, { ...filters, [key]: undefined, q });
  // ATTENTION : la clé de DONNÉES et la clé de FILTRE diffèrent (`scripture_book` vs `book`,
  // `series_name` vs `series`). Les confondre laissait le menu se contraindre lui-même —
  // exactement le bug qu'on corrige ici, en plus discret.
  const counts = (dataKey, filterKey) => {
    const c = new Map(countBy(without(filterKey), dataKey).map((x) => [x.value, x.count]));
    return (v) => c.get(v) || 0;
  };

  const books = countBy(all, "scripture_book", { rank: bookRank });
  const series = countBy(all, "series_name");
  const speakers = countBy(all, "speaker");
  // Les types sont comptés sur le type REGROUPÉ, sinon `teaching` et `teaching_or_qa`
  // produisent deux entrées « Enseignement » que rien ne distingue à l'écran.
  const kinds = [...new Set(all.map(kindOf).filter(Boolean))]
    .sort((a, b) => (KIND_FR[a] || a).localeCompare(KIND_FR[b] || b, "fr"))
    .map((value) => ({ value }));

  // Thèmes : un champ multivalué, donc `countBy` (mono-valeur) ne s'applique pas.
  const [vocab, setVocab] = useState([]);
  useEffect(() => { loadTopics().then(setVocab); }, []);
  const topicCount = (() => {
    const c = new Map();
    for (const s of without("topic")) for (const id of s.topics_canonical || []) c.set(id, (c.get(id) || 0) + 1);
    return (id) => c.get(id) || 0;
  })();
  const topicsUsed = (() => {
    const seen = new Set();
    for (const s of all) for (const id of s.topics_canonical || []) seen.add(id);
    return vocab.filter((v) => seen.has(v.id));
  })();

  // La plateforme vit dans `embed.kind`, pas dans un champ plat : `countBy` ne s'applique pas.
  const SOURCE_FR = { soundcloud: "Audio (SoundCloud)", youtube: "Vidéo (YouTube)" };
  const sources = [...new Set(all.map((s) => s.embed?.kind).filter(Boolean))]
    .sort()
    .map((value) => ({ value, label: SOURCE_FR[value] || value }));
  const sourceCount = (() => {
    const c = new Map();
    for (const s of without("source")) { const k = s.embed?.kind; if (k) c.set(k, (c.get(k) || 0) + 1); }
    return (v) => c.get(v) || 0;
  })();

  const bookCount = counts("scripture_book", "book");
  const seriesCount = counts("series_name", "series");
  const speakerCount = counts("speaker", "speaker");
  const kindCount = (() => {
    const c = new Map();
    for (const s of without("kind")) { const k = kindOf(s); if (k) c.set(k, (c.get(k) || 0) + 1); }
    return (v) => c.get(v) || 0;
  })();

  const set = (key) => (e) => onChange({ ...filters, [key]: e.target.value || undefined });
  const active = Object.values(filters).some(Boolean) || q;

  return (
    <div className="filters">
      <input
        className="search"
        type="search"
        placeholder="Rechercher un thème, un titre, un passage…"
        value={q}
        onChange={(e) => onQuery(e.target.value)}
        aria-label="Rechercher"
      />

      <div className="selects">
        <select value={filters.topic || ""} onChange={set("topic")} aria-label="Thème">
          <option value="">Tous les thèmes</option>
          {topicsUsed.map((v) => (
            <option key={v.id} value={v.id}>
              {v.label} ({topicCount(v.id)})
            </option>
          ))}
        </select>
        <select value={filters.book || ""} onChange={set("book")} aria-label="Livre biblique">
          <option value="">Tous les livres</option>
          {books.map(({ value }) => (
            <option key={value} value={value}>
              {bookLabel(value)} ({bookCount(value)})
            </option>
          ))}
        </select>

        <select value={filters.series || ""} onChange={set("series")} aria-label="Série">
          <option value="">Toutes les séries</option>
          {series.map(({ value }) => (
            <option key={value} value={value}>
              {value} ({seriesCount(value)})
            </option>
          ))}
        </select>

        <select value={filters.speaker || ""} onChange={set("speaker")} aria-label="Prédicateur">
          <option value="">Tous les prédicateurs</option>
          {speakers.map(({ value }) => (
            <option key={value} value={value}>
              {value} ({speakerCount(value)})
            </option>
          ))}
        </select>

        {/* Le compte se calcule comme les autres : sur le corpus filtré par TOUS les autres
            critères, le sien exclu — sinon le menu se contraindrait lui-même. */}
        <select value={filters.source || ""} onChange={set("source")} aria-label="Plateforme">
          <option value="">Audio et vidéo</option>
          {sources.map(({ value, label }) => (
            <option key={value} value={value}>
              {label} ({sourceCount(value)})
            </option>
          ))}
        </select>

        <select value={filters.kind || ""} onChange={set("kind")} aria-label="Type">
          <option value="">Tous les types</option>
          {kinds.map(({ value }) => (
            <option key={value} value={value}>
              {KIND_FR[value] || value} ({kindCount(value)})
            </option>
          ))}
        </select>

        {active && (
          <button className="clear" onClick={() => { onChange({}); onQuery(""); }}>
            Réinitialiser
          </button>
        )}
      </div>
    </div>
  );
}
