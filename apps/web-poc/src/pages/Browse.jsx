import { useState } from "react";
import SermonCard from "../components/SermonCard.jsx";
import { bookLabel, bookRank, countBy } from "../lib/data.js";
import { href } from "../lib/router.js";
import SearchBox, { matches } from "../components/SearchBox.jsx";
import { buildPassageIndex } from "../lib/passages.js";

/**
 * Vue d'agrégats : on entre dans le catalogue par une porte (livre, thème, série),
 * puis on déplie le groupe choisi. Les livres suivent l'ordre du canon, pas la fréquence.
 */
const MODES = {
  series: { key: "series_name", title: "Parcourir par série", label: (v) => v },
};

/**
 * Les livres ont leur propre vue : depuis #56 un livre peut être PRÊCHÉ ou seulement CITÉ,
 * et un simple regroupement sur `scripture_book` raterait les seconds — soit 27 livres
 * qui n'apparaissaient nulle part.
 */
function BrowseBooks({ sermons }) {
  const [q, setQ] = useState("");
  const all = buildPassageIndex(sermons).sort((a, b) => bookRank(a.book) - bookRank(b.book));
  const index = all.filter((b) => matches(q, bookLabel(b.book), b.book));
  const preachedCount = all.filter((b) => b.preached.length > 0).length;

  return (
    <>
      <h1 className="page-title">Parcourir par livre biblique</h1>
      <p className="results-count">
        <strong>{all.length}</strong> livres touchés — {preachedCount} exposés dans un sermon,
        les autres cités à l'intérieur des sermons.
      </p>
      <SearchBox value={q} onChange={setQ} placeholder="Chercher un livre biblique…"
                 label="Chercher un livre" count={index.length} />
      <ul className="book-grid">
        {index.map((b) => (
          <li key={b.book}>
            <a className="book-tile" href={href(`/livres/${b.book}/`)}>
              <span className="book-name">{bookLabel(b.book)}</span>
              <span className="book-counts">
                {b.preached.length > 0 && <span className="count-preached">{b.preached.length} sermon{b.preached.length > 1 ? "s" : ""}</span>}
                {b.cited.length > 0 && <span className="count-cited">{b.cited.length} citation{b.cited.length > 1 ? "s" : ""}</span>}
              </span>
            </a>
          </li>
        ))}
      </ul>
    </>
  );
}

export default function Browse({ sermons, mode }) {
  if (mode === "book") return <BrowseBooks sermons={sermons} />;
  return <BrowseGroups sermons={sermons} cfg={MODES[mode]} />;
}

function BrowseGroups({ sermons, cfg }) {
  const [open, setOpen] = useState(null);
  const [q, setQ] = useState("");
  const all = countBy(sermons, cfg.key, cfg.rank ? { rank: cfg.rank } : undefined);
  const groups = all.filter((g) => matches(q, cfg.label(g.value)));

  return (
    <>
      <h1 className="page-title">{cfg.title}</h1>
      <p className="results-count">{all.length} entrées</p>
      <SearchBox value={q} onChange={setQ} placeholder="Chercher une série…"
                 label="Chercher une série" count={groups.length} />

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
