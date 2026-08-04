/**
 * Le FORMAT de l'index plein-texte — écrit par le build, lu par le navigateur.
 *
 * Encodage et décodage vivent dans le même fichier pour la même raison que la tokenisation
 * est partagée : deux implémentations d'un format finissent toujours par diverger, et l'écart
 * ne se voit pas — l'index se décode « avec succès » sur de mauvais nombres.
 *
 * Module PUR à dessein (aucun accès réseau, aucune variable Vite) : c'est ce qui le rend
 * testable sous `node --test`, là où lib/fulltext.js dépend de `fetch` et de `import.meta.env`.
 *
 * Format d'une entrée, pour un terme :
 *
 *     "0:7@1a.2f,3:1@9k"
 *      │ │  │     └── autre sermon : 3 documents plus loin, 1 occurrence, à 12 044 s
 *      │ │  └──────── horodatages en secondes (base 36), au plus deux
 *      │ └─────────── nombre d'occurrences dans ce sermon (base 36)
 *      └───────────── ÉCART depuis le document précédent (base 36) — pas un identifiant
 *
 * Les écarts plutôt que les identifiants absolus : les documents sont listés dans l'ordre,
 * donc la plupart des écarts valent 1 caractère. C'est ce qui fait tenir 188 000 postings
 * dans des shards dont la médiane pèse 0,6 Ko.
 */

const b36 = (n) => Math.max(0, Math.round(n)).toString(36);

/**
 * @param {{doc:number, n:number, at:number[]}[]} postings  triés par `doc` croissant
 * @returns {string}
 */
export function encodePostings(postings) {
  let prev = 0;
  return postings
    .map(({ doc, n, at }) => {
      const s = `${b36(doc - prev)}:${b36(n)}@${(at || []).map(b36).join(".")}`;
      prev = doc;
      return s;
    })
    .join(",");
}

/** @returns {{doc:number, n:number, at:number[]}[]} */
export function decodePostings(encoded) {
  const out = [];
  let doc = 0;
  for (const chunk of String(encoded || "").split(",")) {
    if (!chunk) continue;
    const [head, stamps = ""] = chunk.split("@");
    const [d, n] = head.split(":");
    doc += parseInt(d, 36);
    out.push({
      doc,
      n: parseInt(n, 36) || 1,
      at: stamps ? stamps.split(".").filter(Boolean).map((s) => parseInt(s, 36)) : [],
    });
  }
  return out;
}
