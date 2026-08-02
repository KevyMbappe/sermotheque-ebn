import { fmtTime } from "../lib/vtt.js";
import ShareAt from "./ShareAt.jsx";

/**
 * Chapitres horodatés — le différenciateur du pipeline : chaque section a été ancrée sur
 * une phrase verbatim, puis convertie en timestamp réel depuis notre propre VTT.
 * Un chapitre sans timestamp (ancrage non retrouvé) reste affiché, mais non cliquable.
 */
export default function Chapters({ chapters, currentTime, onSeek, path, title, bare = false }) {
  if (!chapters?.length) return null;

  // Le chapitre courant = le dernier commencé avant la position de lecture.
  let activeIdx = -1;
  chapters.forEach((c, i) => {
    if (c.t != null && currentTime != null && c.t <= currentTime) activeIdx = i;
  });

  const list = (
    <ol className="chapters">
        {chapters.map((c, i) => {
          const timed = c.t != null;
          return (
            <li key={i} className={i === activeIdx ? "chapter active" : "chapter"}>
              {timed && onSeek ? (
                <button onClick={() => onSeek(c.t)}>
                  <span className="chapter-time">{fmtTime(c.t)}</span>
                  <span className="chapter-title">{c.title}</span>
                </button>
              ) : (
                <div className="chapter-static">
                  <span className="chapter-time">{timed ? fmtTime(c.t) : "—"}</span>
                  <span className="chapter-title">{c.title}</span>
                </div>
              )}
              {/* Le partage ne dépend PAS du lecteur : l'horodatage vient des données, donc
                  un lien reste copiable même si le SDK SoundCloud/YouTube n'a pas chargé. */}
              {timed && path && (
                <span className="chapter-share">
                  <ShareAt path={path} seconds={c.t} title={title} label="Partager" />
                </span>
              )}
            </li>
          );
        })}
    </ol>
  );
  // `bare` : le composant est déjà enveloppé dans un bloc repliable qui porte le titre.
  return bare ? list : (
    <section className="panel">
      <h2>Chapitres</h2>
      {list}
    </section>
  );
}
