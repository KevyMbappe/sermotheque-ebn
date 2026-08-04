/**
 * Routage par CHEMIN (et non par `#`).
 *
 * Pourquoi ce changement : les gens partagent un sermon en copiant l'URL de leur
 * barre d'adresse. Avec `#/sermon/x`, tout ce qui suit le `#` n'est jamais envoyé au
 * serveur — Facebook, WhatsApp et les moteurs voient donc TOUS les liens comme la même
 * page d'accueil, sans titre ni description. Un chemin réel permet de servir une page
 * pré-rendue par sermon, avec ses propres balises Open Graph (voir scripts/prerender.mjs).
 *
 * GitHub Pages ne sait pas réécrire les URLs : c'est le pré-rendu qui fournit un
 * `index.html` à chaque chemin, plus un `404.html` de repli pour tout le reste.
 */

// Vite injecte la base ('/sermotheque-ebn/' en production, '/' en dev).
export const BASE = import.meta.env.BASE_URL || "/";

/** Chemin applicatif ("/sermon/sc-123") -> URL réelle, base comprise. */
export function href(path) {
  return BASE.replace(/\/$/, "") + (path === "/" ? "/" : path);
}

/** URL absolue et partageable, éventuellement à un instant donné. */
export function shareUrl(path, seconds = null) {
  const url = new URL(href(path), window.location.origin);
  if (seconds != null) url.searchParams.set("t", Math.floor(seconds));
  return url.toString();
}

/** Chemin applicatif courant, déduit de location.pathname (base retirée). */
function currentPath() {
  const base = BASE.replace(/\/$/, "");
  let p = window.location.pathname;
  if (base && p.startsWith(base)) p = p.slice(base.length);
  if (!p.startsWith("/")) p = "/" + p;
  // Les pages pré-rendues sont servies comme /sermon/<id>/ — le slash final n'est pas
  // signifiant pour le routage, on le normalise (sauf pour la racine).
  return p.length > 1 ? p.replace(/\/$/, "") : "/";
}

const listeners = new Set();
const notify = () => listeners.forEach((fn) => fn());

/**
 * Met à jour `?t=` sans ajouter d'entrée d'historique ni re-rendre la page.
 * C'est le cœur du partage horodaté : quand on saute à un chapitre, la barre
 * d'adresse suit, donc l'URL copiée pointe sur le bon instant.
 */
export function setTimeParam(seconds) {
  const url = new URL(window.location.href);
  if (seconds == null) url.searchParams.delete("t");
  else url.searchParams.set("t", Math.floor(seconds));
  window.history.replaceState({}, "", url);
}

/** Lecture de `?t=` à l'arrivée (ignore les valeurs absurdes). */
export function initialTime() {
  const raw = new URLSearchParams(window.location.search).get("t");
  if (raw == null) return null;
  const t = Number(raw);
  return Number.isFinite(t) && t >= 0 ? t : null;
}

/**
 * Lecture de `?q=` — les mots cherchés, transmis d'une page de résultats à une fiche.
 *
 * Arriver sur un sermon à la bonne minute est déjà utile ; y arriver avec le mot déjà
 * surligné dans la transcription dit POURQUOI ce sermon est ressorti, et montre les autres
 * fois où il est prononcé. Sans ça, l'utilisateur atterrit au milieu d'un sermon d'une heure
 * sans rien pour relier ce qu'il entend à ce qu'il avait demandé.
 */
export function initialQuery() {
  return new URLSearchParams(window.location.search).get("q") || "";
}

/**
 * Navigation programmatique — pour les cas où un lien imbriqué serait invalide.
 *
 * Une carte de sermon est déjà un `<a>` ; y placer un second `<a>` (« aller à 12:34 ») produit
 * du HTML illégal que les navigateurs réparent chacun à leur façon. Un `<button>` qui appelle
 * `navigate` fait la même chose, correctement.
 */
export function navigate(path) {
  window.history.pushState({}, "", href(path));
  window.scrollTo(0, 0);
  notify();
}

/**
 * Intercepte les clics sur les liens internes pour garder la navigation instantanée.
 * On laisse passer tout ce qui n'est pas un clic gauche simple (nouvel onglet, etc.),
 * pour ne pas casser les habitudes du navigateur.
 */
function onClick(e) {
  if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
  const a = e.target.closest("a");
  if (!a || a.target === "_blank" || a.hasAttribute("download") || a.origin !== window.location.origin) return;
  const base = BASE.replace(/\/$/, "");
  if (base && !a.pathname.startsWith(base)) return;
  e.preventDefault();
  window.history.pushState({}, "", a.href);
  window.scrollTo(0, 0);
  notify();
}

let started = false;
export function startRouter() {
  if (started) return; // React 18 monte deux fois en dev : ne pas doubler les écouteurs.
  started = true;
  window.addEventListener("click", onClick);
  window.addEventListener("popstate", notify);
}

export function subscribe(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export { currentPath };
