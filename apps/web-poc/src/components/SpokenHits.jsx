import { navigate } from "../lib/router.js";
import { fmtTime } from "../lib/vtt.js";

/**
 * « Ce mot est prononcé ici » — le résultat de la recherche dans les transcriptions.
 *
 * C'est le seul endroit du site où une recherche mène à un INSTANT et non à une page. Le
 * pipeline capture les horodatages depuis le début (#42) ; jusqu'ici ils ne servaient qu'aux
 * chapitres, sur un sermon qu'on avait déjà trouvé. Ils répondent maintenant à la question
 * inverse : « où, dans 131 sermons, quelqu'un a-t-il parlé de ça ? »
 *
 * On affiche des minutes, pas des phrases : la phrase demanderait de télécharger la
 * transcription entière (~100 Ko) pour chaque résultat de la liste. Elle se lit sur la fiche,
 * où le VTT est de toute façon chargé — et c'est là qu'on atterrit en cliquant.
 */
export default function SpokenHits({ id, spoken, query }) {
  if (!spoken?.at?.length) return null;
  const { n, at } = spoken;

  return (
    <p className="card-spoken">
      <span className="match-field">prononcé</span>
      <span className="spoken-count">
        {n} fois
      </span>
      {at.map((t) => (
        <button
          key={t}
          type="button"
          className="stamp"
          title="Écouter à partir de ce moment"
          onClick={(e) => {
            // La carte entière est un lien : sans cette interception, le clic partirait
            // sur le sermon depuis le début — en perdant précisément l'instant visé.
            e.preventDefault();
            e.stopPropagation();
            const q = query ? `&q=${encodeURIComponent(query)}` : "";
            navigate(`/sermon/${encodeURIComponent(id)}/?t=${Math.floor(t)}${q}`);
          }}
        >
          {fmtTime(t)}
        </button>
      ))}
    </p>
  );
}
