import { useMemo, useState } from "react";
import Filters from "../components/Filters.jsx";
import SermonCard from "../components/SermonCard.jsx";
import { filterSermons } from "../lib/data.js";

export default function Home({ sermons }) {
  const [q, setQ] = useState("");
  const [filters, setFilters] = useState({});
  const [limit, setLimit] = useState(24);

  const visible = useMemo(() => filterSermons(sermons, { q, ...filters }), [sermons, q, filters]);
  const shown = visible.slice(0, limit);

  return (
    <>
      <section className="hero">
        <h1>Écouter la prédication de la Parole</h1>
        <p>
          Parcourez les prédications de l'Église Bonne Nouvelle : par livre biblique, par série
          ou par prédicateur. Chaque message est découpé en chapitres pour aller droit au passage
          qui vous intéresse.
        </p>
      </section>

      <Filters
        all={sermons}
        visible={visible}
        filters={filters}
        onChange={(f) => { setFilters(f); setLimit(24); }}
        q={q}
        onQuery={(v) => { setQ(v); setLimit(24); }}
      />

      <p className="results-count">
        {visible.length} prédication{visible.length > 1 ? "s" : ""}
        {visible.length !== sermons.length && ` sur ${sermons.length}`}
      </p>

      {visible.length === 0 ? (
        <p className="state">Aucune prédication ne correspond à cette recherche.</p>
      ) : (
        <>
          <div className="grid">
            {shown.map((s) => (
              <SermonCard key={s.id} sermon={s} />
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
