import { fmtDate, fmtDuration } from "../lib/data.js";

export default function SermonCard({ sermon: s }) {
  return (
    <a className="card" href={`#/sermon/${encodeURIComponent(s.id)}`}>
      <div className="card-top">
        {s.scripture_display && <span className="tag tag-scripture">{s.scripture_display}</span>}
        {s.language === "en" && <span className="tag tag-lang">EN</span>}
        {s.is_conference && <span className="tag tag-conf">Conférence</span>}
      </div>

      <h3 className="card-title">{s.title}</h3>
      {s.description && <p className="card-desc">{s.description}</p>}

      <div className="card-meta">
        <span className="speaker">
          {s.speaker || "Prédicateur non identifié"}
          {/* La provenance audio est une vraie garantie : on la montre discrètement. */}
          {s.speaker_provenance === "audio-fingerprint" && (
            <span className="voice-badge" title="Identifié par empreinte vocale">♪</span>
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
