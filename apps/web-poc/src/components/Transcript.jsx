import { useEffect, useMemo, useRef, useState } from "react";
import { loadVtt } from "../lib/data.js";
import { parseVtt, activeCueIndex, fmtTime } from "../lib/vtt.js";

/**
 * Transcription synchronisée : les cues du VTT, la ligne courante surlignée pendant la
 * lecture, un clic pour sauter au moment exact. Chargée à la demande (les VTT font
 * ~100 Ko chacun — inutile de les payer pour qui ne les ouvre pas).
 */
export default function Transcript({ id, currentTime, onSeek }) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState(null);
  const [error, setError] = useState(null);
  const [follow, setFollow] = useState(true);
  const listRef = useRef(null);

  useEffect(() => {
    if (!open || text || error) return;
    loadVtt(id).then(setText).catch(setError);
  }, [open, id, text, error]);

  const cues = useMemo(() => (text ? parseVtt(text) : []), [text]);
  const active = activeCueIndex(cues, currentTime);

  // Suivi automatique : on garde la ligne courante visible, sauf si l'utilisateur
  // a choisi de lire librement (case décochée) — sinon on lui reprendrait le scroll.
  useEffect(() => {
    if (!follow || active < 0 || !listRef.current) return;
    const el = listRef.current.querySelector(`[data-cue="${active}"]`);
    el?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [active, follow]);

  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Transcription</h2>
        <div className="panel-actions">
          {open && cues.length > 0 && (
            <label className="follow">
              <input type="checkbox" checked={follow} onChange={(e) => setFollow(e.target.checked)} />
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
              Transcription indisponible pour cette prédication.
            </p>
          )}
          {!error && !text && <p className="muted">Chargement de la transcription…</p>}
          {cues.length > 0 && (
            <>
              <p className="muted transcript-note">
                Transcription automatique (non relue) — cliquez une ligne pour y sauter.
              </p>
              <div className="transcript" ref={listRef}>
                {cues.map((c, i) => (
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
