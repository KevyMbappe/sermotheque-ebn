import { useState } from "react";
import { shareUrl } from "../lib/router.js";
import { fmtTime } from "../lib/vtt.js";

/**
 * « Copier le lien à cet instant » — le geste qui rend un chapitre ou une citation
 * partageable tel quel (WhatsApp, SMS, feuille de groupe de maison).
 *
 * `navigator.share` d'abord quand il existe (mobile : ouvre la feuille de partage native),
 * presse-papier ensuite, et en dernier recours on affiche l'URL pour copie manuelle —
 * le presse-papier est refusé hors HTTPS et dans certains navigateurs embarqués.
 */
export default function ShareAt({ path, seconds, title, label = "Partager cet instant" }) {
  const [state, setState] = useState(null); // null | "copié" | l'URL en repli

  async function onShare() {
    const url = shareUrl(path, seconds);
    try {
      if (navigator.share) {
        await navigator.share({ title, url });
        return;
      }
      await navigator.clipboard.writeText(url);
      setState("copié");
      setTimeout(() => setState(null), 2000);
    } catch (err) {
      // AbortError = l'utilisateur a fermé la feuille de partage : ce n'est pas un échec.
      if (err?.name === "AbortError") return;
      setState(url);
    }
  }

  return (
    <>
      <button
        className="ghost small"
        onClick={onShare}
        title={`Copier un lien qui démarre à ${fmtTime(seconds)}`}
      >
        {state === "copié" ? "✓ Lien copié" : `🔗 ${label}`}
      </button>
      {state && state !== "copié" && (
        <input className="share-fallback" readOnly value={state} onFocus={(e) => e.target.select()} />
      )}
    </>
  );
}
