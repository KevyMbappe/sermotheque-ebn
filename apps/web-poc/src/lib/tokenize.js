import { fold } from "./fold.js";

/**
 * Tokenisation FR — partagée par l'INDEXEUR (build) et le CHERCHEUR (navigateur).
 *
 * Le partage n'est pas une élégance, c'est une correction : si les deux découpaient le texte
 * différemment, une requête ne retrouverait pas ce que l'index a rangé, et l'écart serait
 * silencieux — des résultats manquants qu'aucune erreur ne signale.
 *
 * L'apostrophe est un SÉPARATEUR, pas une lettre. « l'Église » donne donc `eglise` (le « l »
 * tombe sous le seuil de 3 lettres), et chercher « église » trouve le passage. Traitée comme
 * une lettre, elle rangeait le mot sous `l'eglise` — introuvable autrement qu'en tapant
 * l'élision, ce que personne ne fait.
 */
export const MIN_TERM = 3;

/** Texte → termes indexables (repliés, sans accents, ≥ 3 lettres). */
export function tokens(text) {
  return fold(text)
    .replace(/['’]/g, " ")
    .split(/[^a-z0-9]+/)
    .filter((t) => t.length >= MIN_TERM);
}

/**
 * Le shard qui contient un terme.
 *
 * L'index est découpé par préfixe : 2 lettres par défaut, 3 quand le shard de 2 devenait
 * trop lourd (les gros voisinages comme `con…`, `pro…`). Le manifeste dit lequel existe, donc
 * le client n'a pas à connaître la règle de découpage — il suit la carte. C'est ce qui permet
 * à l'index de grossir avec le catalogue sans que le poids d'une requête bouge.
 */
export function shardKey(term, shards) {
  const three = term.slice(0, 3);
  if (shards.has(three)) return three;
  const two = term.slice(0, 2);
  return shards.has(two) ? two : null;
}
