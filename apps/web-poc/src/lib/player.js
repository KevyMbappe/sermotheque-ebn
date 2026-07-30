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
 * Les deux SDK sont chargés à la demande, une seule fois.
 */

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

  await new Promise((res) => widget.bind(SC.Widget.Events.READY, res));

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

async function attachYouTube(iframe, { onTime }) {
  await loadScript("https://www.youtube.com/iframe_api", "YT");
  // L'API n'est utilisable qu'une fois `onYouTubeIframeAPIReady` passé.
  await new Promise((res) => {
    if (window.YT?.Player) return res();
    const prev = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = () => { prev?.(); res(); };
  });

  const player = await new Promise((res) => {
    const p = new window.YT.Player(iframe, { events: { onReady: () => res(p) } });
  });

  // YT n'émet pas de progression : on interroge la position pendant la lecture.
  let timer = null;
  const tick = () => {
    const st = player.getPlayerState?.();
    if (st === window.YT.PlayerState.PLAYING) onTime?.(player.getCurrentTime());
  };
  timer = setInterval(tick, 500);

  return {
    seekTo(sec) {
      player.seekTo(sec, true);
      player.playVideo();
    },
    destroy() {
      clearInterval(timer);
      try { player.destroy?.(); } catch { /* déjà détruit */ }
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
