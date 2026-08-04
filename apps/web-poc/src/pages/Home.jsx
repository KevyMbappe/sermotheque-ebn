import { useMemo, useState } from "react";
import Filters from "../components/Filters.jsx";
import SermonCard from "../components/SermonCard.jsx";
import { filterSermons } from "../lib/data.js";
import useTranscriptSearch from "../lib/useTranscriptSearch.js";

export default function Home({ sermons }) {
  const [q, setQ] = useState("");
  const [filters, setFilters] = useState({});
  const [limit, setLimit] = useState(24);

  // Deux recherches, deux vitesses. L'éditoriale est en mémoire et répond à la frappe ;
  // celle des transcriptions télécharge quelques shards et arrive après (lib/fulltext.js).
  const editorial = useMemo(() => filterSermons(sermons, { q, ...filters }), [sermons, q, filters]);
  const pool = useMemo(() => filterSermons(sermons, filters), [sermons, filters]);
  const spoken = useTranscriptSearch(q);

  /**
   * Fusion des deux. Règle : **le texte écrit prime sur le texte prononcé.** Un mot dans le
   * titre ou le résumé est une intention éditoriale ; le même mot dans la transcription peut
   * n'être qu'une phrase de passage. Les résultats éditoriaux gardent donc leur ordre, et les
   * sermons trouvés UNIQUEMENT dans ce qui a été dit suivent, classés par pertinence propre.
   *
   * Les sermons présents des deux côtés ne sont pas dupliqués : ils reçoivent les horodatages
   * en plus de leur extrait.
   */
  const { visible, spokenOnly } = useMemo(() => {
    const hits = spoken.hits;
    if (!hits || !hits.size) return { visible: editorial, spokenOnly: 0 };
    const inEditorial = new Set(editorial.map((s) => s.id));
    const withStamps = editorial.map((s) =>
      hits.has(s.id) ? { ...s, _spoken: hits.get(s.id) } : s
    );
    const extra = pool
      .filter((s) => !inEditorial.has(s.id) && hits.has(s.id))
      .map((s) => ({ ...s, _spoken: hits.get(s.id) }))
      .sort((a, b) => b._spoken.score - a._spoken.score);
    return { visible: [...withStamps, ...extra], spokenOnly: extra.length };
  }, [editorial, pool, spoken.hits]);

  const shown = visible.slice(0, limit);

  return (
    <>
      <section className="hero">
        <h1>Les sermons de l'Église Bonne Nouvelle</h1>
        <p>
          Parcourez les sermons par livre biblique, par série ou par prédicateur. Chaque sermon
          est découpé en chapitres pour aller droit au passage
          qui vous intéresse.
        </p>
      </section>

      <Filters
        all={sermons}
        filters={filters}
        onChange={(f) => { setFilters(f); setLimit(24); }}
        q={q}
        onQuery={(v) => { setQ(v); setLimit(24); }}
      />

      <p className="results-count">
        {visible.length} sermon{visible.length > 1 ? "s" : ""}
        {visible.length !== sermons.length && ` sur ${sermons.length}`}
        {/* On dit ce que la recherche des transcriptions a apporté EN PLUS : sans cette
            phrase, des résultats sans rapport visible avec la requête ont l'air d'un bug. */}
        {spokenOnly > 0 && (
          <span className="count-spoken">
            {" "}· dont {spokenOnly} trouvé{spokenOnly > 1 ? "s" : ""} seulement dans ce qui a été dit
          </span>
        )}
        {q && spoken.loading && <span className="count-spoken"> · recherche dans les transcriptions…</span>}
      </p>

      {/* Dire pourquoi un mot ne rapporte rien vaut mieux qu'un silence. « Prière » est
          prononcé dans 76 sermons sur 131 : le proposer comme critère serait un faux service.
          Le mot n'est pas ignoré pour autant — il ne restreint simplement pas la recherche. */}
      {spoken.common?.length > 0 && (
        <p className="results-note">
          {spoken.common.length > 1 ? "Les mots" : "Le mot"}{" "}
          {spoken.common.map((t) => `« ${t} »`).join(", ")}{" "}
          {spoken.common.length > 1 ? "reviennent" : "revient"} dans plus de la moitié des sermons —
          trop courant{spoken.common.length > 1 ? "s" : ""} pour distinguer un sermon d'un autre.
        </p>
      )}

      {visible.length === 0 ? (
        <p className="state">
          {spoken.loading
            ? "Recherche dans les transcriptions…"
            : "Aucun sermon ne correspond à cette recherche."}
        </p>
      ) : (
        <>
          <div className="grid">
            {shown.map((s) => (
              <SermonCard key={s.id} sermon={s} query={q} />
            ))}
          </div>
          {limit < visible.length && (
            <button className="more" onClick={() => setLimit((l) => l + 24)}>
              Afficher plus ({visible.length - limit} restantes)
            </button>
          )}
        </>
      )}
    </>
  );
}
