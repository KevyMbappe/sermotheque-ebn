import { href } from "../lib/router.js";
import { fmtDate, fmtDuration } from "../lib/data.js";
import { markedParts } from "../lib/search.js";

export default function SermonCard({ sermon: s }) {
  // Slash final : c'est la forme canonique servie par le pré-rendu, donc celle qui doit
  // apparaître dans la barre d'adresse — c'est l'URL que les gens copient pour partager.
  return (
    <a className="card" href={href(`/sermon/${encodeURIComponent(s.id)}/`)}>
      <div className="card-top">
        {s.scripture_display && <span className="tag tag-scripture">{s.scripture_display}</span>}
        {s.language === "en" && <span className="tag tag-lang">EN</span>}
        {s.is_conference && <span className="tag tag-conf">Conférence</span>}
      </div>

      <h3 className="card-title">{s.title}</h3>
      {s.description && <p className="card-desc">{s.description}</p>}

      {/* Quand un sermon ressort d'une recherche, on montre POURQUOI : le champ qui a
          répondu et l'extrait, terme en évidence. Sinon un résultat inattendu a l'air
          d'un bug. Le surlignage passe par des segments JSX, jamais par du HTML injecté. */}
      {s._match?.snippet && (
        <p className="card-match">
          <span className="match-field">{s._match.field}</span>
          {markedParts(s._match.snippet).map((p, i) =>
            p.hit ? <mark key={i}>{p.text}</mark> : <span key={i}>{p.text}</span>
          )}
        </p>
      )}

      <div className="card-meta">
        <span className="speaker">
          {s.speaker || "Prédicateur non identifié"}
          {/* La provenance audio est une vraie garantie : on la montre discrètement. */}
          {s.speaker_provenance === "audio-fingerprint" && (
            <span className="voice-badge" title="Identifié par empreinte vocale">♪</span>
          )}
          {/* À l'inverse, `default-rule` est une SUPPOSITION (« si personne n'est nommé dans le
              titre, c'est le pasteur »). On crédite une personne réelle : il faut le dire. */}
          {s.speaker_provenance === "default-rule" && (
            <span
              className="guess-badge"
              title="Attribution par défaut, non confirmée : le prédicateur n'est pas nommé dans le titre et sa voix n'a pas encore été analysée."
            >
              ?
            </span>
          )}
        </span>
        {s.series_name && <span className="dot">·</span>}
        {s.series_name && <span className="series">{s.series_name}</span>}
      </div>

      <div className="card-foot">
        {s.date && <span>{fmtDate(s.date)}</span>}
        {s.duration ? <span>{fmtDuration(s.duration)}</span> : null}
        {s.chapters?.length ? <span>{s.chapters.length} chapitres</span> : null}
      </div>
    </a>
  );
}
