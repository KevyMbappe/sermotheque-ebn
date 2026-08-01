import { useEffect, useState } from "react";
import { bookLabel, bookRank, countBy, KIND_FR, loadTopics } from "../lib/data.js";

/**
 * Filtres croisés. Chaque menu se construit sur le corpus COMPLET (`all`) pour que les
 * options ne disparaissent pas au fil des sélections, mais les compteurs reflètent le
 * sous-ensemble courant (`visible`) — on voit donc l'effet d'un filtre avant de le poser.
 */
export default function Filters({ all, visible, filters, onChange, q, onQuery }) {
  const counts = (key) => {
    const c = new Map(countBy(visible, key).map((x) => [x.value, x.count]));
    return (v) => c.get(v) || 0;
  };

  const books = countBy(all, "scripture_book", { rank: bookRank });
  const series = countBy(all, "series_name");
  const speakers = countBy(all, "speaker");
  const kinds = countBy(all, "kind");

  // Thèmes : un champ multivalué, donc `countBy` (mono-valeur) ne s'applique pas.
  const [vocab, setVocab] = useState([]);
  useEffect(() => { loadTopics().then(setVocab); }, []);
  const topicCount = (() => {
    const c = new Map();
    for (const s of visible) for (const id of s.topics_canonical || []) c.set(id, (c.get(id) || 0) + 1);
    return (id) => c.get(id) || 0;
  })();
  const topicsUsed = (() => {
    const seen = new Set();
    for (const s of all) for (const id of s.topics_canonical || []) seen.add(id);
    return vocab.filter((v) => seen.has(v.id));
  })();

  const bookCount = counts("scripture_book");
  const seriesCount = counts("series_name");
  const speakerCount = counts("speaker");
  const kindCount = counts("kind");

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
            <option key={v.id} value={v.id} disabled={!topicCount(v.id)}>
              {v.label} ({topicCount(v.id)})
            </option>
          ))}
        </select>
        <select value={filters.book || ""} onChange={set("book")} aria-label="Livre biblique">
          <option value="">Tous les livres</option>
          {books.map(({ value }) => (
            <option key={value} value={value} disabled={!bookCount(value)}>
              {bookLabel(value)} ({bookCount(value)})
            </option>
          ))}
        </select>

        <select value={filters.series || ""} onChange={set("series")} aria-label="Série">
          <option value="">Toutes les séries</option>
          {series.map(({ value }) => (
            <option key={value} value={value} disabled={!seriesCount(value)}>
              {value} ({seriesCount(value)})
            </option>
          ))}
        </select>

        <select value={filters.speaker || ""} onChange={set("speaker")} aria-label="Prédicateur">
          <option value="">Tous les prédicateurs</option>
          {speakers.map(({ value }) => (
            <option key={value} value={value} disabled={!speakerCount(value)}>
              {value} ({speakerCount(value)})
            </option>
          ))}
        </select>

        <select value={filters.kind || ""} onChange={set("kind")} aria-label="Type">
          <option value="">Tous les types</option>
          {kinds.map(({ value }) => (
            <option key={value} value={value} disabled={!kindCount(value)}>
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
