/**
 * Abstraction lecteur : une seule interface pour SoundCloud et YouTube.
 *
 * Les chapitres horodatés sont le différenciateur du pipeline — il faut donc pouvoir dire
 * "saute à 12:34" et "où en es-tu ?" quelle que soit la plateforme. Les deux APIs sont
 * asymétriques (SC = postMessage asynchrone en ms ; YT = objet JS en secondes), d'où ce
 * contrat commun :
 *
 *   attach(iframe, { onTime })  ->  { seekTo(sec), destroy() }
 *
 * `onTime(sec)` est appelé régulièrement pendant la lecture (pour surligner la transcription).
 * Les commandes lecture/pause restent celles du lecteur natif : il est simplement rendu
 * collant au défilement, donc toujours atteignable, avec sa propre barre de progression.
 * Les deux SDK sont chargés à la demande, une seule fois.
 *
 * RÈGLE QUI GOUVERNE LES DEUX PILOTES : **aucun d'eux ne retire du DOM un nœud rendu par
 * React.** L'API YouTube documente que `player.destroy()` supprime l'iframe ; appelée depuis
 * un effet, elle laissait React avec une référence sur un nœud détaché — le lecteur
 * disparaissait en passant d'un sermon YouTube à un autre (mesuré : 0 iframe après
 * navigation). Le cycle de vie appartient à React, via une `key` sur le composant ; les
 * pilotes ne font qu'arrêter ce qu'ils ont démarré.
 */

/**
 * Au-delà, on considère le pilotage perdu.
 *
 * Sans cette limite, un SDK qui charge mais ne signale jamais « prêt » — vidéo privée,
 * intégration refusée par le propriétaire, réseau qui traîne — laissait la promesse en
 * suspens POUR TOUJOURS : pas d'erreur, pas de repli, juste des chapitres qui ne répondent
 * pas et rien à l'écran pour le dire. Un échec franc vaut mieux qu'une attente muette.
 */
const READY_TIMEOUT = 8000;

const withTimeout = (promise, what) =>
  new Promise((res, rej) => {
    const timer = setTimeout(() => rej(new Error(`${what} : pas de signal « prêt » après ${READY_TIMEOUT} ms`)), READY_TIMEOUT);
    promise.then(
      (v) => { clearTimeout(timer); res(v); },
      (e) => { clearTimeout(timer); rej(e); }
    );
  });

const loadScript = (src, globalKey) =>
  new Promise((res, rej) => {
    if (window[globalKey]) return res(window[globalKey]);
    const existing = document.querySelector(`script[src="${src}"]`);
    const done = () => (window[globalKey] ? res(window[globalKey]) : rej(new Error(`${globalKey} absent`)));
    if (existing) return existing.addEventListener("load", done), existing.addEventListener("error", rej);
    const s = document.createElement("script");
    s.src = src;
    s.async = true;
    s.onload = done;
    s.onerror = rej;
    document.head.appendChild(s);
  });

/* ---------------------------------- SoundCloud ---------------------------------- */

async function attachSoundCloud(iframe, { onTime }) {
  const SC = await loadScript("https://w.soundcloud.com/player/api.js", "SC");
  const widget = SC.Widget(iframe);

  await withTimeout(new Promise((res) => widget.bind(SC.Widget.Events.READY, res)), "SoundCloud");

  // PLAY_PROGRESS remonte la position en ms pendant la lecture : notre horloge.
  widget.bind(SC.Widget.Events.PLAY_PROGRESS, (e) => {
    if (e && typeof e.currentPosition === "number") onTime?.(e.currentPosition / 1000);
  });

  return {
    seekTo(sec) {
      widget.seekTo(sec * 1000); // SC parle en millisecondes
      widget.play();
    },
    destroy() {
      try { widget.unbind(SC.Widget.Events.PLAY_PROGRESS); } catch { /* iframe déjà démontée */ }
    },
  };
}

/* ----------------------------------- YouTube ------------------------------------ */

/**
 * Codes d'erreur de l'API IFrame. Les deux derniers sont les seuls VRAIMENT probables sur une
 * chaîne d'église — et sans ce message, la fiche affiche un rectangle noir sans explication.
 */
const YT_ERRORS = {
  2: "identifiant de vidéo invalide",
  5: "lecteur HTML5 indisponible",
  100: "vidéo introuvable (supprimée ou privée)",
  101: "le propriétaire n'autorise pas la lecture intégrée",
  150: "le propriétaire n'autorise pas la lecture intégrée",
};

async function attachYouTube(iframe, { onTime, onError }) {
  await loadScript("https://www.youtube.com/iframe_api", "YT");
  // L'API n'est utilisable qu'une fois `onYouTubeIframeAPIReady` passé.
  await withTimeout(
    new Promise((res) => {
      if (window.YT?.Player) return res();
      const prev = window.onYouTubeIframeAPIReady;
      window.onYouTubeIframeAPIReady = () => { prev?.(); res(); };
    }),
    "API YouTube"
  );

  const player = await withTimeout(
    new Promise((res) => {
      // `event.target` et non la variable de retour : le constructeur peut appeler onReady
      // avant que l'affectation ait eu lieu, et on résoudrait alors avec `undefined`.
      new window.YT.Player(iframe, {
        events: {
          onReady: (e) => res(e.target),
          onError: (e) => onError?.(YT_ERRORS[e?.data] || `erreur ${e?.data}`),
        },
      });
    }),
    "lecteur YouTube"
  );

  // YT n'émet pas de progression : on interroge la position pendant la lecture.
  const timer = setInterval(() => {
    const st = player.getPlayerState?.();
    if (st === window.YT.PlayerState.PLAYING) onTime?.(player.getCurrentTime());
  }, 500);

  return {
    seekTo(sec) {
      player.seekTo(sec, true);
      player.playVideo();
    },
    destroy() {
      // On n'appelle PAS `player.destroy()` : il retirerait l'iframe que React possède
      // (voir l'en-tête). On arrête seulement notre horloge ; l'iframe part avec le
      // composant, que sa `key` fait remonter à chaque sermon.
      clearInterval(timer);
    },
  };
}

/**
 * Branche le bon pilote selon la source. Rejette si la plateforme est inconnue ;
 * l'appelant dégrade alors proprement (lecteur visible, chapitres non cliquables).
 */
export function attachPlayer(iframe, kind, opts = {}) {
  if (kind === "soundcloud") return attachSoundCloud(iframe, opts);
  if (kind === "youtube") return attachYouTube(iframe, opts);
  return Promise.reject(new Error(`plateforme inconnue: ${kind}`));
}
