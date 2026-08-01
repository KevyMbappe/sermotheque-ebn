import { useCallback, useEffect, useRef, useState } from "react";
import Player from "../components/Player.jsx";
import Chapters from "../components/Chapters.jsx";
import Transcript from "../components/Transcript.jsx";
import SermonCard from "../components/SermonCard.jsx";
import ShareAt from "../components/ShareAt.jsx";
import StickyPlayer from "../components/StickyPlayer.jsx";
import Section from "../components/Section.jsx";
import { bookLabel, bookRank, fmtDate, fmtDuration, KIND_FR } from "../lib/data.js";
import { fmtTime } from "../lib/vtt.js";
import { href, initialTime, setTimeParam } from "../lib/router.js";
import { osisPoints } from "../lib/passages.js";
import { loadTopics } from "../lib/data.js";

export default function Sermon({ sermon: s, all }) {
  const ctrlRef = useRef(null);
  const playerRef = useRef(null);
  const [ctrl, setCtrl] = useState(null);      // déclenche le rendu de la barre collante
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(null);
  // `?t=` lu une seule fois, à l'arrivée : ensuite c'est la lecture qui pilote l'URL.
  const startAtRef = useRef(initialTime());

  // Callbacks stables : le lecteur ne doit pas se re-brancher à chaque tick d'horloge.
  const handleReady = useCallback((ctrl) => {
    ctrlRef.current = ctrl;
    setCtrl(ctrl);
    // Un lien horodaté doit démarrer au bon endroit dès que le lecteur est prêt.
    const t = startAtRef.current;
    if (t != null) {
      ctrl.seekTo(t);
      setCurrentTime(t);
      startAtRef.current = null;
    }
  }, []);
  const handleTime = useCallback((t) => setCurrentTime(t), []);
  const handlePlaying = useCallback((p) => setPlaying(p), []);
  const seek = useCallback((sec) => {
    ctrlRef.current?.seekTo(sec);
    setCurrentTime(sec); // retour visuel immédiat, sans attendre l'horloge du lecteur
    // La barre d'adresse suit le saut : l'URL qu'on copie pointe donc sur cet instant.
    setTimeParam(sec);
  }, []);
  const canSeek = ctrlRef.current ? seek : null;
  const path = `/sermon/${encodeURIComponent(s.id)}/`;

  // Passages cités, ramenés à des couples livre+chapitre uniques et rangés dans l'ordre
  // du canon — une puce par passage réel, pas une par occurrence.
  const citedPoints = (() => {
    const seen = new Map();
    for (const ref of s.scripture_refs_osis || []) {
      for (const pt of osisPoints(ref)) {
        const key = `${pt.book}.${pt.chapter ?? 0}`;
        if (!seen.has(key)) {
          seen.set(key, {
            key,
            book: pt.book,
            label: `${bookLabel(pt.book)}${pt.chapter != null ? ` ${pt.chapter}` : ""}`,
          });
        }
      }
    }
    return [...seen.values()].sort(
      (a, b) => bookRank(a.book) - bookRank(b.book) || a.key.localeCompare(b.key, "fr", { numeric: true })
    );
  })();

  // Libellés du vocabulaire curé, chargés à la demande (petit fichier, mis en cache).
  const [topicLabels, setTopicLabels] = useState(new Map());
  useEffect(() => {
    loadTopics().then((v) => setTopicLabels(new Map(v.map((x) => [x.id, x.label]))));
  }, []);

  const sameSeries = s.series_name
    ? all.filter((o) => o.series_name === s.series_name && o.id !== s.id).slice(0, 6)
    : [];

  return (
    <article className="sermon">
      <a className="back" href={href("/")}>← Tous les sermons</a>

      {/* En-tête visible seulement sur le papier : qui, quoi, et où retrouver le sermon. */}
      <div className="print-only print-head">
        <strong>Église Bonne Nouvelle — Poissy</strong>
        <span>Fiche de groupe de maison · {typeof window !== "undefined" ? window.location.origin + window.location.pathname : ""}</span>
      </div>

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
        {/* Fiche de groupe de maison : tout le matériel est déjà là (résumé, points clés,
            chapitres, questions de réflexion). Il ne manquait qu'une mise en page papier. */}
        {/* Replier les chapitres a rendu leurs boutons « Partager » invisibles : on garde
            donc un partage du sermon entier ici, à portée. Le partage HORODATÉ reste dans
            les chapitres et les citations, là où l'instant a un sens. */}
        <p className="sermon-actions no-print">
          <ShareAt path={path} seconds={null} title={s.title} label="Partager ce sermon" />
          <button className="ghost small" onClick={() => window.print()}>
            🖨 Imprimer la fiche de groupe
          </button>
        </p>
      </header>


      <div ref={playerRef}>
        <Player embed={s.embed} title={s.title} onReady={handleReady}
                onTime={handleTime} onPlaying={handlePlaying} />
      </div>

      <div className="sermon-body">
        {/* Colonne « écouter » : le lecteur, ce qui permet d'y naviguer, et le texte qui le
            suit. Les chapitres et la transcription sont désormais COLLÉS au lecteur — ils
            en font partie ; les avoir rangés avec les blocs de lecture obligeait à remonter
            toute la page pour changer de moment. */}
        <div className="col-main">
          <Section title="Chapitres" count={s.chapters?.length || null}>
            <Chapters
              chapters={s.chapters}
              currentTime={currentTime}
              onSeek={canSeek}
              path={path}
              title={s.title}
              bare
            />
          </Section>

          <Transcript id={s.id} currentTime={currentTime} onSeek={canSeek} />

          {/* Le résumé reste OUVERT : c'est la seule chose qu'on veut lire d'emblée. */}
          {/* L'invitation ouvre le résumé au lieu de séparer le titre du lecteur : c'est un
              texte d'accueil, pas un obstacle à franchir avant d'écouter. */}
          {(s.summary || s.invitation) && (
            <Section title="Résumé" defaultOpen>
              {s.invitation && <p className="invitation">{s.invitation}</p>}
              {s.summary && <p>{s.summary}</p>}
            </Section>
          )}

          {s.key_points?.length > 0 && (
            <Section title="Points clés" count={s.key_points.length}>
              <ul className="bullets">
                {s.key_points.map((p, i) => <li key={i}>{p}</li>)}
              </ul>
            </Section>
          )}

          {s.key_quotes?.length > 0 && (
            <Section title="Citations" count={s.key_quotes.length}>
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
            </Section>
          )}

          {s.questions?.length > 0 && (
            <Section title="Questions pour aller plus loin" count={s.questions.length}>
              <ol className="bullets">
                {s.questions.map((q, i) => <li key={i}>{q}</li>)}
              </ol>
            </Section>
          )}
        </div>

        <aside className="col-side">
          {s.scripture_refs?.length > 0 && (
            <Section title="Passages cités" count={citedPoints.length || s.scripture_refs.length}>
              {/* Les puces sont construites depuis les ids OSIS, PAS depuis le texte libre :
                  les deux listes ne sont pas alignées index par index. */}
              {citedPoints.length > 0 && (
                <ul className="chips">
                  {citedPoints.map((p) => (
                    <li key={p.key}>
                      <a className="chip chip-link" href={href(`/livres/${p.book}/`)}>{p.label}</a>
                    </li>
                  ))}
                </ul>
              )}
              <p className="muted refs-verbatim">{s.scripture_refs.join(" · ")}</p>
            </Section>
          )}

          {s.topics_canonical?.length > 0 && (
            <Section title="Thèmes" count={s.topics_canonical.length}>
              <ul className="chips">
                {s.topics_canonical.map((id) => (
                  <li key={id}>
                    <a className="chip chip-link" href={href(`/themes/${id}/`)}>
                      {topicLabels.get(id) || id}
                    </a>
                  </li>
                ))}
              </ul>
              <p className="muted refs-verbatim">{(s.topics || []).join(" · ")}</p>
            </Section>
          )}

          {s.references?.length > 0 && (
            <Section title="Références" count={s.references.length}>
              <ul className="bullets small">
                {s.references.map((r, i) => <li key={i}>{r}</li>)}
              </ul>
            </Section>
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

      <StickyPlayer
        anchorRef={playerRef}
        ctrl={ctrl}
        playing={playing}
        currentTime={currentTime}
        title={s.title}
        scripture={s.scripture_display}
      />
    </article>
  );
}
