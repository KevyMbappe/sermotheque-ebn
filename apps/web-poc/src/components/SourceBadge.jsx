/**
 * D'où vient ce sermon — et donc à quoi s'attendre en cliquant.
 *
 * Ce n'est pas une décoration : **278 des 517 sermons du catalogue n'existent que sur
 * YouTube**, contre 239 sur SoundCloud. Aujourd'hui seulement 12 des 131 publiés sont des
 * vidéos, mais la proportion s'inversera à mesure que la capture avance. Sans repère, une
 * carte ne dit pas si l'on va écouter un fichier audio ou regarder une vidéo — et ce n'est
 * pas la même chose selon qu'on est dans le train ou dans son salon.
 *
 * **Aux couleurs du système de design, pas à celles des plateformes.** Le rouge YouTube et
 * l'orange SoundCloud sont des marques commerciales dans une sermothèque d'église : ils
 * attireraient l'œil plus que le titre du sermon. Le glyphe suffit à distinguer, la palette
 * reste la nôtre.
 */

const ICONS = {
  // Rectangle arrondi + triangle : la forme universelle du « lire une vidéo ».
  youtube: (
    <svg viewBox="0 0 24 18" aria-hidden="true" focusable="false">
      <rect x="0.75" y="0.75" width="22.5" height="16.5" rx="4.5" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <path d="M9.6 5.4 L15.6 9 L9.6 12.6 Z" fill="currentColor" />
    </svg>
  ),
  // Barres de niveau : la forme universelle du son.
  soundcloud: (
    <svg viewBox="0 0 24 18" aria-hidden="true" focusable="false">
      <g stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
        <line x1="3" y1="10" x2="3" y2="12" />
        <line x1="7" y1="7" x2="7" y2="15" />
        <line x1="11" y1="4" x2="11" y2="15" />
        <line x1="15" y1="6" x2="15" y2="15" />
        <line x1="19" y1="9" x2="19" y2="13" />
      </g>
    </svg>
  ),
};

const LABELS = {
  youtube: { name: "YouTube", what: "Vidéo" },
  soundcloud: { name: "SoundCloud", what: "Audio" },
};

export default function SourceBadge({ kind, withLabel = false }) {
  const meta = LABELS[kind];
  if (!meta) return null;
  return (
    <span className={`source-badge source-${kind}`} title={`${meta.what} — ${meta.name}`}>
      {ICONS[kind]}
      <span className={withLabel ? "" : "sr-only"}>{withLabel ? meta.name : `${meta.what} — ${meta.name}`}</span>
    </span>
  );
}
