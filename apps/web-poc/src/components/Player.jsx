import { useEffect, useRef, useState } from "react";
import { attachPlayer } from "../lib/player.js";

/**
 * Lecteur embarqué + horloge partagée.
 *
 * Expose deux choses au parent via `onReady({ seekTo })` et `onTime(sec)` :
 * les chapitres/citations peuvent commander le saut, la transcription peut suivre.
 * Si le pilotage échoue (SDK bloqué, plateforme inattendue), l'iframe reste lisible :
 * on perd le saut au timestamp, pas l'écoute.
 */
export default function Player({ embed, title, onReady, onTime }) {
  const iframeRef = useRef(null);
  const [controllable, setControllable] = useState(null); // null = en cours, false = dégradé

  useEffect(() => {
    if (!embed || !iframeRef.current) return;
    let ctrl = null;
    let alive = true;

    attachPlayer(iframeRef.current, embed.kind, { onTime })
      .then((c) => {
        if (!alive) return c.destroy?.();
        ctrl = c;
        setControllable(true);
        onReady?.(c);
      })
      .catch(() => alive && setControllable(false));

    return () => {
      alive = false;
      ctrl?.destroy?.();
    };
    // On ne re-branche que si la source change : les callbacks sont stables côté parent.
  }, [embed?.url, embed?.kind]);

  if (!embed) {
    return <p className="state">Aucun média disponible pour ce sermon.</p>;
  }

  return (
    <div className={`player player-${embed.kind}`}>
      <iframe
        ref={iframeRef}
        src={embed.url}
        title={`Lecteur — ${title}`}
        allow="autoplay; encrypted-media; picture-in-picture"
        allowFullScreen
        frameBorder="0"
      />
      {controllable === false && (
        <p className="player-note">
          Lecture disponible, mais le saut aux chapitres n'a pas pu être activé.{" "}
          <a href={embed.link} target="_blank" rel="noreferrer">Ouvrir sur {embed.kind === "youtube" ? "YouTube" : "SoundCloud"}</a>
        </p>
      )}
    </div>
  );
}
