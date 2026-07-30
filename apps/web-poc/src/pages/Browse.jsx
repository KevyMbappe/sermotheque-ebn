import { useState } from "react";
import SermonCard from "../components/SermonCard.jsx";
import { bookLabel, bookRank, countBy } from "../lib/data.js";

/**
 * Vue d'agrégats : on entre dans le catalogue par une porte (livre, série, prédicateur),
 * puis on déplie le groupe choisi. Les livres suivent l'ordre du canon, pas la fréquence.
 */
const MODES = {
  book: { key: "scripture_book", title: "Parcourir par livre biblique", label: bookLabel, rank: bookRank },
  series: { key: "series_name", title: "Parcourir par série", label: (v) => v },
  speaker: { key: "speaker", title: "Parcourir par prédicateur", label: (v) => v },
};

export default function Browse({ sermons, mode }) {
  const cfg = MODES[mode];
  const [open, setOpen] = useState(null);
  const groups = countBy(sermons, cfg.key, cfg.rank ? { rank: cfg.rank } : undefined);

  return (
    <>
      <h1 className="page-title">{cfg.title}</h1>
      <p className="results-count">{groups.length} entrées</p>

      <ul className="groups">
        {groups.map(({ value, count }) => {
          const isOpen = open === value;
          const items = isOpen
            ? sermons
                .filter((s) => s[cfg.key] === value)
                .sort((a, b) => (a.date || "").localeCompare(b.date || ""))
            : [];
          return (
            <li key={value} className={isOpen ? "group open" : "group"}>
              <button className="group-head" onClick={() => setOpen(isOpen ? null : value)}>
                <span className="group-name">{cfg.label(value)}</span>
                <span className="group-count">{count}</span>
                <span className="group-chevron">{isOpen ? "−" : "+"}</span>
              </button>
              {isOpen && (
                <div className="grid group-grid">
                  {items.map((s) => <SermonCard key={s.id} sermon={s} />)}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </>
  );
}
