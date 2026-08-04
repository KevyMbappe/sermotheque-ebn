import { useEffect, useState } from "react";
import { searchTranscripts } from "./fulltext.js";

/**
 * La recherche dans les transcriptions est ASYNCHRONE (elle télécharge des shards), là où la
 * recherche éditoriale est instantanée. Ce hook assume l'écart plutôt que de le masquer :
 * les résultats éditoriaux s'affichent tout de suite, ceux des transcriptions arrivent
 * ensuite et complètent la liste. Faire attendre les deux pour qu'ils apparaissent ensemble
 * rendrait chaque frappe lente pour aligner le rapide sur le lent.
 *
 * Deux protections :
 *   • **anti-rebond** — on ne part pas chercher à chaque touche ; 220 ms après la dernière.
 *   • **garde d'obsolescence** — une réponse qui revient après que la requête a changé est
 *     jetée. Sans elle, taper vite affiche par intermittence les résultats d'un mot à moitié
 *     écrit : le bug classique, invisible en local et visible sur un réseau lent.
 */
export default function useTranscriptSearch(query, { delay = 220 } = {}) {
  const [state, setState] = useState({ hits: null, common: [], loading: false, q: "" });

  useEffect(() => {
    const q = query.trim();
    if (!q) {
      setState({ hits: null, common: [], loading: false, q: "" });
      return;
    }
    let alive = true;
    setState((s) => ({ ...s, loading: true }));
    const timer = setTimeout(() => {
      searchTranscripts(q)
        .then((r) => alive && setState({ hits: r?.hits || null, common: r?.common || [], loading: false, q }))
        .catch(() => alive && setState({ hits: null, common: [], loading: false, q }));
    }, delay);
    return () => { alive = false; clearTimeout(timer); };
  }, [query, delay]);

  // Les résultats ne valent que pour la requête qui les a produits.
  return state.q === query.trim() ? state : { hits: null, common: [], loading: true, q: query.trim() };
}
