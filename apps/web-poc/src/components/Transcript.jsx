import { useEffect, useMemo, useRef, useState } from "react";
import { fold, loadVtt } from "../lib/data.js";
import SearchBox from "./SearchBox.jsx";
import { parseVtt, activeCueIndex, fmtTime } from "../lib/vtt.js";

/**
 * Transcription synchronisée : les cues du VTT, la ligne courante surlignée pendant la
 * lecture, un clic pour sauter au moment exact. Chargée à la demande (les VTT font
 * ~100 Ko chacun — inutile de les payer pour qui ne les ouvre pas).
 */
export default function Transcript({ id, currentTime, onSeek, initialQuery = "" }) {
  // `initialQuery` : on arrive d'une recherche plein-texte (lib/fulltext.js). La transcription
  // s'ouvre alors d'elle-même sur le mot cherché — l'utilisateur atterrit au bon instant ET
  // voit toutes les autres fois où il est prononcé, au lieu d'un mur de texte muet.
  const [open, setOpen] = useState(Boolean(initialQuery));
  const [text, setText] = useState(null);
  const [error, setError] = useState(null);
  const [follow, setFollow] = useState(true);
  const [q, setQ] = useState(initialQuery);
  const listRef = useRef(null);

  useEffect(() => {
    if (!open || text || error) return;
    loadVtt(id).then(setText).catch(setError);
  }, [open, id, text, error]);

  const cues = useMemo(() => (text ? parseVtt(text) : []), [text]);
  const active = activeCueIndex(cues, currentTime);

  // Recherche dans la transcription : c'est le « chercher où il dit X » que le minutage
  // rendait possible depuis le début (#42). On garde l'index d'origine de chaque cue,
  // sinon le surlignage de la ligne courante et le saut viseraient la mauvaise ligne.
  const hits = useMemo(() => {
    const needle = fold(q).trim();
    if (!needle) return null;
    return cues.map((c, i) => ({ c, i })).filter(({ c }) => fold(c.text).includes(needle));
  }, [cues, q]);
  const shown = hits || cues.map((c, i) => ({ c, i }));

  // Suivi automatique : on garde la ligne courante visible, sauf si l'utilisateur
  // a choisi de lire librement (case décochée) — sinon on lui reprendrait le scroll.
  useEffect(() => {
    if (q || !follow || active < 0 || !listRef.current) return;
    const el = listRef.current.querySelector(`[data-cue="${active}"]`);
    el?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [active, follow, q]);

  return (
    <section className="panel no-print">
      <div className="panel-head">
        <h2>Transcription</h2>
        <div className="panel-actions">
          {open && cues.length > 0 && (
            <label className="follow" title={q ? "Suspendu pendant une recherche" : undefined}>
              <input type="checkbox" checked={follow && !q} disabled={Boolean(q)}
                     onChange={(e) => setFollow(e.target.checked)} />
              Suivre la lecture
            </label>
          )}
          <button className="ghost" onClick={() => setOpen((o) => !o)}>
            {open ? "Masquer" : "Afficher"}
          </button>
        </div>
      </div>

      {open && (
        <>
          {error && (
            <p className="muted">
              Transcription indisponible pour ce sermon.
            </p>
          )}
          {!error && !text && <p className="muted">Chargement de la transcription…</p>}
          {cues.length > 0 && (
            <>
              <p className="muted transcript-note">
                Transcription automatique (non relue) — cliquez une ligne pour y sauter.
              </p>
              <SearchBox value={q} onChange={setQ}
                         placeholder="Chercher un mot dans la transcription…"
                         label="Chercher dans la transcription"
                         count={hits ? hits.length : null} />
              {hits?.length === 0 && (
                <p className="muted">Aucun passage ne contient ce mot.</p>
              )}
              <div className="transcript" ref={listRef}>
                {shown.map(({ c, i }) => (
                  <p
                    key={i}
                    data-cue={i}
                    className={i === active ? "cue active" : "cue"}
                    onClick={() => onSeek?.(c.start)}
                    role={onSeek ? "button" : undefined}
                  >
                    <span className="cue-time">{fmtTime(c.start)}</span>
                    <span>{c.text}</span>
                  </p>
                ))}
              </div>
            </>
          )}
        </>
      )}
    </section>
  );
}
