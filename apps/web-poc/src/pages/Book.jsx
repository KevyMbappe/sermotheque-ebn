import SermonCard from "../components/SermonCard.jsx";
import { bookLabel } from "../lib/data.js";
import { href } from "../lib/router.js";
import { buildPassageIndex } from "../lib/passages.js";

/**
 * Un livre de la Bible, vu depuis le catalogue : ce qui a été prêché dessus, et ce qui le
 * cite. La seconde liste n'existe que depuis la normalisation OSIS des citations (#56) —
 * c'est elle qui fait passer le catalogue de 28 à 54 livres consultables.
 */
export default function Book({ sermons, book }) {
  const entry = buildPassageIndex(sermons).find((b) => b.book === book);
  const label = bookLabel(book);

  if (!entry) {
    return (
      <>
        <a className="back" href={href("/livres")}>← Tous les livres</a>
        <h1 className="page-title">{label}</h1>
        <p className="state">
          Aucune prédication ne touche encore ce livre. Il apparaîtra ici dès qu'un message
          l'expose ou le cite — le site suit le catalogue, qui se remplit à chaque
          enrichissement.
        </p>
      </>
    );
  }

  // Les allusions au livre entier (chapitre 0) sont réelles mais moins précises :
  // on les garde à part plutôt que de les faire passer pour un chapitre.
  const chapters = entry.chapters.filter((c) => c.chapter > 0);
  const wholeBook = entry.chapters.find((c) => c.chapter === 0);

  return (
    <>
      <a className="back" href={href("/livres")}>← Tous les livres</a>
      <h1 className="page-title">{label}</h1>
      <p className="results-count">
        {entry.preached.length > 0 && (
          <><strong>{entry.preached.length}</strong> prédication{entry.preached.length > 1 ? "s" : ""} sur ce livre</>
        )}
        {entry.preached.length > 0 && entry.cited.length > 0 && " · "}
        {entry.cited.length > 0 && (
          <><strong>{entry.cited.length}</strong> autre{entry.cited.length > 1 ? "s" : ""} le cite{entry.cited.length > 1 ? "nt" : ""}</>
        )}
      </p>

      {entry.preached.length > 0 && (
        <section className="passage-block">
          <h2>Prêché sur {label}</h2>
          <div className="grid">
            {entry.preached.map((s) => <SermonCard key={s.id} sermon={s} />)}
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
                        {c.preached.includes(s) && <span className="badge-preached">prédication</span>}
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
