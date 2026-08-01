/**
 * Normalisation de texte pour la comparaison — module séparé À DESSEIN.
 *
 * `fold` est utilisé par data.js ET par search.js, or data.js importe search.js : le
 * laisser dans data.js créait un cycle d'imports. Les cycles ES fonctionnent tant que
 * l'usage est différé, mais c'est un pari sur l'ordre d'évaluation — un module isolé
 * coûte trois lignes et supprime la question.
 */
/** Normalise pour comparer sans accents ni casse (recherche FR). */
export const fold = (s) =>
  (s || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "");
