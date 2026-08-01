import { useCallback, useRef, useState } from "react";
import Player from "../components/Player.jsx";
import Chapters from "../components/Chapters.jsx";
import Transcript from "../components/Transcript.jsx";
import SermonCard from "../components/SermonCard.jsx";
import ShareAt from "../components/ShareAt.jsx";
import { fmtDate, fmtDuration, KIND_FR } from "../lib/data.js";
import { fmtTime } from "../lib/vtt.js";
import { href, initialTime, setTimeParam } from "../lib/router.js";

export default function Sermon({ sermon: s, all }) {
  const ctrlRef = useRef(null);
  const [currentTime, setCurrentTime] = useState(null);
  // `?t=` lu une seule fois, à l'arrivée : ensuite c'est la lecture qui pilote l'URL.
  const startAtRef = useRef(initialTime());

  // Callbacks stables : le lecteur ne doit pas se re-brancher à chaque tick d'horloge.
  const handleReady = useCallback((ctrl) => {
    ctrlRef.current = ctrl;
    // Un lien horodaté doit démarrer au bon endroit dès que le lecteur est prêt.
    const t = startAtRef.current;
    if (t != null) {
      ctrl.seekTo(t);
      setCurrentTime(t);
      startAtRef.current = null;
    }
  }, []);
  const handleTime = useCallback((t) => setCurrentTime(t), []);
  const seek = useCallback((sec) => {
    ctrlRef.current?.seekTo(sec);
    setCurrentTime(sec); // retour visuel immédiat, sans attendre l'horloge du lecteur
    // La barre d'adresse suit le saut : l'URL qu'on copie pointe donc sur cet instant.
    setTimeParam(sec);
  }, []);
  const canSeek = ctrlRef.current ? seek : null;
  const path = `/sermon/${encodeURIComponent(s.id)}/`;

  const sameSeries = s.series_name
    ? all.filter((o) => o.series_name === s.series_name && o.id !== s.id).slice(0, 6)
    : [];

  return (
    <article className="sermon">
      <a className="back" href={href("/")}>← Toutes les prédications</a>

      <header className="sermon-head">
        <div className="sermon-tags">
          {s.scripture_display && <span className="tag tag-scripture">{s.scripture_display}</span>}
          {s.kind && s.kind !== "sermon" && <span className="tag">{KIND_FR[s.kind] || s.kind}</span>}
          {s.language === "en" && <span className="tag tag-lang">EN</span>}
        </div>
        <h1>{s.title}</h1>
        <p className="sermon-meta">
          <strong>{s.speaker || "Prédicateur non identifié"}</strong>
          {s.speaker_provenance === "audio-fingerprint" && (
            <span className="voice-badge" title="Identifié par empreinte vocale">♪</span>
          )}
          {/* Sur la fiche, on a la place de l'écrire en toutes lettres plutôt qu'en badge. */}
          {s.speaker_provenance === "default-rule" && (
            <span
              className="guess-note"
              title="Le prédicateur n'est pas nommé dans le titre et sa voix n'a pas encore été analysée."
            >
              {" "}(attribution par défaut, à confirmer)
            </span>
          )}
          {s.date && <> · {fmtDate(s.date)}</>}
          {s.duration ? <> · {fmtDuration(s.duration)}</> : null}
          {s.series_name && (
            <> · <a href={href("/series")}>{s.series_name}</a>{s.series_part ? ` (partie ${s.series_part})` : ""}</>
          )}
        </p>
        {s.invitation && <p className="invitation">{s.invitation}</p>}
      </header>

      <Player embed={s.embed} title={s.title} onReady={handleReady} onTime={handleTime} />

      <div className="sermon-body">
        <div className="col-main">
          {s.summary && (
            <section className="panel">
              <h2>Résumé</h2>
              <p>{s.summary}</p>
            </section>
          )}

          {s.key_points?.length > 0 && (
            <section className="panel">
              <h2>Points clés</h2>
              <ul className="bullets">
                {s.key_points.map((p, i) => <li key={i}>{p}</li>)}
              </ul>
            </section>
          )}

          {s.key_quotes?.length > 0 && (
            <section className="panel">
              <h2>Citations</h2>
              {s.key_quotes.map((qt, i) => (
                <blockquote key={i} className="quote">
                  <p>« {qt.text} »</p>
                  {qt.t != null && (
                    <span className="quote-actions">
                      {canSeek && (
                        <button className="ghost small" onClick={() => seek(qt.t)}>
                          ▶ Écouter à {fmtTime(qt.t)}
                        </button>
                      )}
                      <ShareAt path={path} seconds={qt.t} title={s.title} label="Partager" />
                    </span>
                  )}
                </blockquote>
              ))}
            </section>
          )}

          <Transcript id={s.id} currentTime={currentTime} onSeek={canSeek} />

          {s.questions?.length > 0 && (
            <section className="panel">
              <h2>Questions pour aller plus loin</h2>
              <ol className="bullets">
                {s.questions.map((q, i) => <li key={i}>{q}</li>)}
              </ol>
            </section>
          )}
        </div>

        <aside className="col-side">
          <Chapters
            chapters={s.chapters}
            currentTime={currentTime}
            onSeek={canSeek}
            path={path}
            title={s.title}
          />

          {s.scripture_refs?.length > 0 && (
            <section className="panel">
              <h2>Passages cités</h2>
              <ul className="chips">
                {s.scripture_refs.map((r, i) => <li key={i} className="chip">{r}</li>)}
              </ul>
            </section>
          )}

          {s.topics?.length > 0 && (
            <section className="panel">
              <h2>Thèmes</h2>
              <ul className="chips">
                {s.topics.map((t, i) => <li key={i} className="chip">{t}</li>)}
              </ul>
            </section>
          )}

          {s.references?.length > 0 && (
            <section className="panel">
              <h2>Références</h2>
              <ul className="bullets small">
                {s.references.map((r, i) => <li key={i}>{r}</li>)}
              </ul>
            </section>
          )}

          {s.embed?.link && (
            <p className="muted">
              <a href={s.embed.link} target="_blank" rel="noreferrer">
                Écouter sur {s.embed.kind === "youtube" ? "YouTube" : "SoundCloud"} ↗
              </a>
            </p>
          )}
        </aside>
      </div>

      {sameSeries.length > 0 && (
        <section className="related">
          <h2>Dans la même série</h2>
          <div className="grid">
            {sameSeries.map((o) => <SermonCard key={o.id} sermon={o} />)}
          </div>
        </section>
      )}
    </article>
  );
}
