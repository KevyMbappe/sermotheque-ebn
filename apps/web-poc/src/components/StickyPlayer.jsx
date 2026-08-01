import { useEffect, useRef, useState } from "react";
import { fmtTime } from "../lib/vtt.js";

/**
 * Barre de lecture collante — apparaît quand le lecteur sort de l'écran.
 *
 * Le problème réel : on écoute, on décroche, on veut revenir dix secondes en arrière — et il
 * faut remonter toute la page pour atteindre le lecteur. Sur un sermon d'une heure avec sa
 * transcription, ça fait beaucoup de défilement pour un geste qui devrait être immédiat.
 *
 * Choix de conception :
 *   • On ne duplique PAS le lecteur. Un second iframe voudrait dire deux flux audio à
 *     synchroniser ; la barre pilote celui qui joue déjà, via l'abstraction `lib/player.js`.
 *   • Elle est ancrée EN BAS, pas sous l'en-tête : c'est là que le pouce arrive sur un
 *     téléphone, et ça n'empile pas deux bandeaux collants en haut.
 *   • Elle n'apparaît que lorsque le lecteur n'est plus visible (IntersectionObserver) : tant
 *     qu'on le voit, une barre de plus serait du bruit.
 *   • Elle ne s'affiche jamais si le pilote n'a pas pu se brancher (SDK bloqué) — un bouton
 *     pause qui ne met rien en pause serait pire que pas de bouton.
 */
export default function StickyPlayer({ anchorRef, ctrl, playing, currentTime, title, scripture }) {
  const [hidden, setHidden] = useState(true);
  const barRef = useRef(null);

  useEffect(() => {
    const el = anchorRef.current;
    if (!el || !ctrl) return;
    const io = new IntersectionObserver(
      ([e]) => setHidden(e.isIntersecting),
      // -80px en bas : la barre se montre juste avant que le lecteur ne disparaisse tout à
      // fait, pour que la transition ne soit pas ressentie comme un sursaut.
      { rootMargin: "0px 0px -80px 0px", threshold: 0 }
    );
    io.observe(el);
    return () => io.disconnect();
  }, [anchorRef, ctrl]);

  // Le padding du corps évite que la barre masque la fin de la page.
  useEffect(() => {
    document.body.classList.toggle("has-sticky-player", !hidden);
    return () => document.body.classList.remove("has-sticky-player");
  }, [hidden]);

  if (!ctrl || hidden) return null;

  const back = () => ctrl.nudge(-10);
  const forward = () => ctrl.nudge(15);

  return (
    <div className="sticky-player no-print" ref={barRef} role="region" aria-label="Lecture en cours">
      <div className="sticky-inner">
        <button className="sp-btn" onClick={back} title="Revenir 10 secondes en arrière" aria-label="Revenir 10 secondes en arrière">
          <span aria-hidden="true">↺</span><span className="sp-btn-num">10</span>
        </button>
        <button className="sp-btn sp-play" onClick={() => ctrl.toggle()}
                title={playing ? "Mettre en pause" : "Reprendre la lecture"}
                aria-label={playing ? "Mettre en pause" : "Reprendre la lecture"}>
          <span aria-hidden="true">{playing ? "❚❚" : "▶"}</span>
        </button>
        <button className="sp-btn" onClick={forward} title="Avancer de 15 secondes" aria-label="Avancer de 15 secondes">
          <span aria-hidden="true">↻</span><span className="sp-btn-num">15</span>
        </button>

        <div className="sp-meta">
          <span className="sp-title">{title}</span>
          {scripture && <span className="sp-scripture">{scripture}</span>}
        </div>

        <span className="sp-time" aria-live="off">{currentTime != null ? fmtTime(currentTime) : "—"}</span>

        <button
          className="sp-btn sp-up"
          onClick={() => anchorRef.current?.scrollIntoView({ behavior: "smooth", block: "center" })}
          title="Revenir au lecteur"
          aria-label="Revenir au lecteur"
        >
          <span aria-hidden="true">↑</span>
        </button>
      </div>
    </div>
  );
}
