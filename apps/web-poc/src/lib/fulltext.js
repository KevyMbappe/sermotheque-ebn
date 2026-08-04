import { tokens, shardKey, MIN_TERM } from "./tokenize.js";
import { decodePostings } from "./ftcodec.js";

/**
 * Recherche DANS CE QUI A ÉTÉ DIT — l'autre moitié du catalogue.
 *
 * Jusqu'ici la recherche ne voyait que le contenu éditorial : titre, résumé, points clés. Or
 * ce qu'un prédicateur a réellement dit n'existe que dans les transcriptions, et c'est là que
 * se trouvent les noms, les illustrations, les objections — tout ce que personne ne pense à
 * écrire dans un résumé.
 *
 * Mesuré sur les 131 sermons publiés : **77 % du vocabulaire indexé (16 586 mots sur 21 637)
 * n'apparaît nulle part dans le contenu éditorial.** Ce ne sont pas des mots rares et sans
 * intérêt — ce sont « cancer » (5 sermons), « divorce » (3), « hôpital » (7),
 * « adolescence » (7), « propitiation » (2), « indulgences » (3). Exactement ce qu'un membre
 * cherche, et exactement ce qu'aucun résumé ne mentionne.
 *
 * Le compromis d'architecture est côté build (scripts/build-fulltext.mjs) : l'index est
 * découpé par préfixe, donc **une requête ne télécharge que les shards de ses propres mots**,
 * quelques kilo-octets, et ce coût ne bouge pas quand le catalogue passera de 131 à 517.
 *
 * Ici, trois règles :
 *   1. **ET entre les termes** — comme la recherche éditoriale, pour que les deux se
 *      comportent pareil ; un OU rendrait tout le catalogue sur « grâce et loi ».
 *   2. **Extension par préfixe** : « prier » trouve aussi « prière », « prières », « prié ».
 *      Sans radicalisation (pas de stemmer français ici) mais moins cher qu'une famille de
 *      formes à maintenir — et le shard contient déjà tous les mots de ce voisinage.
 *      L'occurrence exacte pèse plus qu'une occurrence étendue, sinon « foi » serait noyée
 *      sous « foire » et « foin ».
 *   3. **Pondération par rareté** (idf) : un mot présent dans trois sermons dit quelque chose
 *      du sermon ; un mot présent partout ne dit rien.
 *
 * Ce que l'index NE contient pas, à dessein : les mots présents dans plus de la moitié du
 * corpus (jetés au build — pour une église, « dieu » ou « christ » sont des mots vides) et le
 * texte lui-même. Une recherche rend donc des minutes, pas des phrases ; la phrase se lit sur
 * la fiche, où le VTT est de toute façon chargé.
 */

const BASE = import.meta.env.BASE_URL;

let manifestPromise = null;
const shardCache = new Map(); // clé de shard → Promise<objet>

function loadManifest() {
  if (!manifestPromise) {
    manifestPromise = fetch(`${BASE}data/ft/manifest.json`)
      .then((r) => (r.ok ? r.json() : null))
      .then((m) => (m ? { ...m, shardSet: new Set(m.shards), commonSet: new Set(m.common || []) } : null))
      // Un index absent n'est pas une panne : le site marche sans, avec la recherche
      // éditoriale seule. On ne casse jamais la page pour un enrichissement optionnel.
      .catch(() => null);
  }
  return manifestPromise;
}

function loadShard(key) {
  if (!shardCache.has(key)) {
    shardCache.set(
      key,
      fetch(`${BASE}data/ft/${key}.json`)
        .then((r) => (r.ok ? r.json() : {}))
        .catch(() => ({}))
    );
  }
  return shardCache.get(key);
}

/**
 * Cherche `query` dans les transcriptions.
 * @returns {Promise<{hits: Map<string, {score:number, n:number, at:number[]}>, common: string[]}|null>}
 *   `hits` : id de sermon → occurrences et points d'entrée. `common` : les mots de la requête
 *   trop répandus pour discriminer (voir plus bas). `null` = rien à en dire — requête vide,
 *   index indisponible, ou requête entièrement faite de mots ubiquitaires ; à distinguer d'un
 *   `hits` vide, qui veut dire « cherché, rien trouvé ».
 */
export async function searchTranscripts(query) {
  const terms = [...new Set(tokens(query))];
  if (!terms.length) return null;

  const manifest = await loadManifest();
  if (!manifest) return null;

  const N = manifest.docs.length;
  /** @type {Map<number, {score:number, n:number, at:number[]}>[]} un résultat par terme */
  const perTerm = [];
  const common = [];

  for (const term of terms) {
    // Un mot présent dans plus de la moitié du corpus a été écarté de l'index au build. Il ne
    // CONTRAINT PAS la recherche : le compter comme absent ferait échouer « prière du matin »
    // sur son premier mot, alors qu'il est prononcé dans 76 sermons sur 131. C'est le
    // traitement classique d'un mot vide — sauf qu'ici les mots vides sont ceux de l'église.
    if (manifest.commonSet.has(term)) { common.push(term); continue; }
    const key = shardKey(term, manifest.shardSet);
    if (!key) return { hits: new Map(), common }; // aucun shard : ce mot n'est nulle part
    const shard = await loadShard(key);

    // Le terme exact, puis ses extensions par préfixe (pluriels, formes fléchies).
    const matches = [];
    if (shard[term]) matches.push([term, 1]);
    for (const t in shard) {
      if (t !== term && t.startsWith(term)) matches.push([t, 0.6]);
    }
    if (!matches.length) return { hits: new Map(), common };

    const hits = new Map();
    for (const [t, weight] of matches) {
      const postings = decodePostings(shard[t]);
      const idf = Math.log(1 + N / postings.length);
      for (const p of postings) {
        const prev = hits.get(p.doc);
        const score = weight * idf * (1 + Math.log(p.n));
        if (prev) {
          prev.score += score;
          prev.n += p.n;
          // Les points d'entrée du terme EXACT priment : ce sont ceux qu'on affichera.
          if (weight === 1) prev.at = [...p.at, ...prev.at];
        } else {
          hits.set(p.doc, { score, n: p.n, at: [...p.at] });
        }
      }
    }
    perTerm.push(hits);
  }

  // Requête entièrement composée de mots ubiquitaires : on n'a rien d'utile à ajouter, et
  // prétendre le contraire remplirait la liste de tout le catalogue.
  if (!perTerm.length) return { hits: new Map(), common };

  // ET : un sermon doit porter TOUS les termes. On part du terme le plus rare — c'est lui
  // qui coûte le moins d'intersections.
  perTerm.sort((a, b) => a.size - b.size);
  const result = new Map();
  for (const [doc, first] of perTerm[0]) {
    let score = first.score;
    let n = first.n;
    const at = [...first.at];
    let all = true;
    for (const other of perTerm.slice(1)) {
      const h = other.get(doc);
      if (!h) { all = false; break; }
      score += h.score;
      n += h.n;
      at.push(...h.at);
    }
    if (!all) continue;
    at.sort((a, b) => a - b);
    result.set(manifest.docs[doc], { score, n, at: [...new Set(at)].slice(0, 3) });
  }
  return { hits: result, common };
}

/** Un mot est-il assez long pour être cherché dans les transcriptions ? */
export const searchable = (q) => tokens(q).length > 0;
export { MIN_TERM };
