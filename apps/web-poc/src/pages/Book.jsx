import { useState } from "react";
import SermonCard from "../components/SermonCard.jsx";
import SearchBox, { matches } from "../components/SearchBox.jsx";
import { bookLabel } from "../lib/data.js";
import { href } from "../lib/router.js";
import { buildPassageIndex } from "../lib/passages.js";

/**
 * Un livre de la Bible, vu depuis le catalogue : les sermons qui l'exposent, et ceux qui le
 * cite. La seconde liste n'existe que depuis la normalisation OSIS des citations (#56) —
 * c'est elle qui fait passer le catalogue de 28 à 54 livres consultables.
 */
export default function Book({ sermons, book }) {
  const [q, setQ] = useState("");
  const entry = buildPassageIndex(sermons).find((b) => b.book === book);
  const label = bookLabel(book);

  if (!entry) {
    return (
      <>
        <a className="back" href={href("/livres")}>← Tous les livres</a>
        <h1 className="page-title">{label}</h1>
        <p className="state">
          Aucun sermon ne touche encore ce livre. Il apparaîtra ici dès qu'un sermon
          l'expose ou le cite — le site suit le catalogue, qui se remplit à chaque
          enrichissement.
        </p>
      </>
    );
  }

  // Les allusions au livre entier (chapitre 0) sont réelles mais moins précises :
  // on les garde à part plutôt que de les faire passer pour un chapitre.
  const wholeBookRaw = entry.chapters.find((c) => c.chapter === 0);

  // La recherche porte sur TOUT ce que la page liste — la grille, l'index chapitre par
  // chapitre ET les mentions sans chapitre. Oublier une section la laisserait affichée
  // pendant une recherche, et fausserait le compte.
  const keep = (s) => matches(q, s.title, s.description, s.speaker, s.scripture_display);
  const preached = entry.preached.filter(keep);
  const chapters = entry.chapters
    .filter((c) => c.chapter > 0)
    .map((c) => ({ ...c, preached: c.preached.filter(keep), cited: c.cited.filter(keep) }))
    .filter((c) => c.preached.length || c.cited.length);
  const wholeBook = wholeBookRaw
    ? { ...wholeBookRaw, preached: wholeBookRaw.preached.filter(keep), cited: wholeBookRaw.cited.filter(keep) }
    : null;

  // Un sermon peut figurer à la fois dans la grille et dans l'index des chapitres :
  // on compte des SERMONS distincts, pas des lignes affichées.
  const hits = new Set([
    ...preached.map((s) => s.id),
    ...chapters.flatMap((c) => [...c.preached, ...c.cited].map((s) => s.id)),
    ...(wholeBook ? [...wholeBook.preached, ...wholeBook.cited].map((s) => s.id) : []),
  ]).size;

  return (
    <>
      <a className="back" href={href("/livres")}>← Tous les livres</a>
      <h1 className="page-title">{label}</h1>
      <p className="results-count">
        {entry.preached.length > 0 && (
          <><strong>{entry.preached.length}</strong> sermon{entry.preached.length > 1 ? "s" : ""} sur ce livre</>
        )}
        {entry.preached.length > 0 && entry.cited.length > 0 && " · "}
        {entry.cited.length > 0 && (
          <><strong>{entry.cited.length}</strong> autre{entry.cited.length > 1 ? "s" : ""} le cite{entry.cited.length > 1 ? "nt" : ""}</>
        )}
      </p>

      {entry.preached.length + entry.cited.length > 4 && (
        <SearchBox value={q} onChange={setQ} placeholder="Chercher dans ces sermons…"
                   label="Chercher dans ces sermons" count={hits} />
      )}

      {preached.length > 0 && (
        <section className="passage-block">
          <h2>Sermons sur {label}</h2>
          <div className="grid">
            {preached.map((s) => <SermonCard key={s.id} sermon={s} />)}
          </div>
        </section>
      )}

      {chapters.length > 0 && (
        <section className="passage-block">
          <h2>Chapitre par chapitre</h2>
          <ul className="chapter-index">
            {chapters.map((c) => {
              const all = [...c.preached, ...c.cited];
              return (
                <li key={c.chapter}>
                  <span className="chapter-key">{label} {c.chapter}</span>
                  <ul className="chapter-sermons">
                    {all.map((s) => (
                      <li key={s.id}>
                        <a href={href(`/sermon/${encodeURIComponent(s.id)}/`)}>{s.title}</a>
                        {c.preached.includes(s) && <span className="badge-preached">sermon</span>}
                      </li>
                    ))}
                  </ul>
                </li>
              );
            })}
          </ul>
        </section>
      )}

      {wholeBook && (wholeBook.preached.length > 0 || wholeBook.cited.length > 0) && (
        <section className="passage-block">
          <h2>Mentions du livre, sans chapitre précisé</h2>
          <ul className="chapter-sermons">
            {[...wholeBook.preached, ...wholeBook.cited].map((s) => (
              <li key={s.id}>
                <a href={href(`/sermon/${encodeURIComponent(s.id)}/`)}>{s.title}</a>
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}
