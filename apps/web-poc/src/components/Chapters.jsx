import { fmtTime } from "../lib/vtt.js";

/**
 * Chapitres horodatés — le différenciateur du pipeline : chaque section a été ancrée sur
 * une phrase verbatim, puis convertie en timestamp réel depuis notre propre VTT.
 * Un chapitre sans timestamp (ancrage non retrouvé) reste affiché, mais non cliquable.
 */
export default function Chapters({ chapters, currentTime, onSeek }) {
  if (!chapters?.length) return null;

  // Le chapitre courant = le dernier commencé avant la position de lecture.
  let activeIdx = -1;
  chapters.forEach((c, i) => {
    if (c.t != null && currentTime != null && c.t <= currentTime) activeIdx = i;
  });

  return (
    <section className="panel">
      <h2>Chapitres</h2>
      <ol className="chapters">
        {chapters.map((c, i) => {
          const seekable = c.t != null && onSeek;
          return (
            <li key={i} className={i === activeIdx ? "chapter active" : "chapter"}>
              {seekable ? (
                <button onClick={() => onSeek(c.t)}>
                  <span className="chapter-time">{fmtTime(c.t)}</span>
                  <span className="chapter-title">{c.title}</span>
                </button>
              ) : (
                <div className="chapter-static">
                  <span className="chapter-time">—</span>
                  <span className="chapter-title">{c.title}</span>
                </div>
              )}
            </li>
          );
        })}
      </ol>
    </section>
  );
}
