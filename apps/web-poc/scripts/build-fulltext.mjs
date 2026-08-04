/**
 * Index plein-texte des TRANSCRIPTIONS — construit au build, interrogé sans serveur.
 *
 * Le problème : 131 transcriptions pèsent 16 Mo (63 Mo une fois les 517 sermons captés). On ne
 * peut ni les envoyer au navigateur, ni les chercher côté serveur — le POC n'en a pas, et §8
 * du spec tranche : index statique pré-calculé. Or c'est le contenu qui compte le plus : ce
 * qu'un prédicateur a DIT n'existe nulle part ailleurs dans le catalogue.
 *
 * La solution tient en une idée : **ce n'est pas le poids de l'index qui compte, c'est le poids
 * d'une requête.** L'index est donc découpé par préfixe de terme, et une recherche ne télécharge
 * que les shards de ses propres mots — quelques kilo-octets, quel que soit le nombre de sermons.
 *
 *   mesuré sur 131 sermons : 351 shards · médiane 0,6 Ko gzip · le plus gros 22 Ko
 *   (un index monolithique ferait 244 Ko aujourd'hui et ~1 Mo à 517 sermons, à payer d'un bloc)
 *
 * Deux choix qui font la taille :
 *   • **Les termes ubiquitaires sont jetés.** Un mot présent dans plus de la moitié des sermons
 *     ne discrimine rien : le garder coûte les plus grosses listes de l'index pour un résultat
 *     qui renverrait tout le catalogue. (« dieu », « christ », « seigneur » sont dans ce cas —
 *     c'est le corpus d'une église : ces mots-là sont ses mots vides à elle.)
 *   • **Deux horodatages par sermon suffisent.** L'index sert à répondre « où, et à quelle
 *     minute » ; la liste complète des occurrences se recalcule sur la fiche, où le VTT est
 *     déjà chargé. En stocker plus triplerait l'index pour un détail qu'on affiche ailleurs.
 *
 * Sortie : public/data/ft/manifest.json + public/data/ft/<préfixe>.json
 * Format d'une entrée : "terme": "<ΔdocId>:<occurrences>@<sec>.<sec>,…"  (nombres en base 36)
 */
import { readFileSync, writeFileSync, mkdirSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tokens } from "../src/lib/tokenize.js";
import { encodePostings } from "../src/lib/ftcodec.js";
import { parseVtt } from "../src/lib/vtt.js";

/** Un terme présent dans plus de cette part du corpus ne discrimine plus rien. */
const UBIQUITY = 0.5;
/** Au-delà, un shard de 2 lettres est redécoupé à 3. Choisi pour tenir dans un aller-retour. */
const SHARD_LIMIT = 48 * 1024;
/** Horodatages conservés par (terme, sermon) — de quoi proposer un point d'entrée, pas la liste. */
const STAMPS = 2;

/**
 * @param {{id: string, vtt: string}[]} docs  sermons publiés ayant une transcription
 * @param {string} outDir  public/data/ft
 */
export function buildFulltextIndex(docs, outDir) {
  const postings = new Map(); // terme → [ [docIdx, {n, at[]}] ]

  docs.forEach(({ vtt }, docIdx) => {
    const hits = new Map();
    for (const cue of parseVtt(vtt)) {
      for (const term of tokens(cue.text)) {
        let h = hits.get(term);
        if (!h) hits.set(term, (h = { n: 0, at: [] }));
        h.n++;
        // Un même mot répété dans la même seconde ne vaut pas deux points d'entrée.
        if (h.at.length < STAMPS && h.at[h.at.length - 1] !== cue.start) h.at.push(cue.start);
      }
    }
    for (const [term, h] of hits) {
      let ps = postings.get(term);
      if (!ps) postings.set(term, (ps = []));
      ps.push([docIdx, h]);
    }
  });

  const maxDf = Math.max(1, Math.floor(docs.length * UBIQUITY));
  const kept = [...postings.entries()].filter(([, ps]) => ps.length <= maxDf);
  const dropped = postings.size - kept.length;

  // Le format vit dans src/lib/ftcodec.js, partagé avec le lecteur (voir son en-tête).
  const encode = (ps) => encodePostings(ps.map(([doc, h]) => ({ doc, n: h.n, at: h.at })));

  // Découpage adaptatif : 2 lettres, puis 3 pour les voisinages trop peuplés.
  const byTwo = new Map();
  for (const [term, ps] of kept) {
    const k = term.slice(0, 2);
    if (!byTwo.has(k)) byTwo.set(k, []);
    byTwo.get(k).push([term, ps]);
  }
  const shards = new Map();
  for (const [k, entries] of byTwo) {
    const obj = Object.fromEntries(entries.map(([t, ps]) => [t, encode(ps)]));
    if (JSON.stringify(obj).length <= SHARD_LIMIT) {
      shards.set(k, obj);
      continue;
    }
    const sub = new Map();
    for (const [t, ps] of entries) {
      const k3 = t.slice(0, 3);
      if (!sub.has(k3)) sub.set(k3, {});
      sub.get(k3)[t] = encode(ps);
    }
    for (const [k3, o] of sub) shards.set(k3, o);
  }

  rmSync(outDir, { recursive: true, force: true });
  mkdirSync(outDir, { recursive: true });
  let bytes = 0;
  for (const [k, obj] of shards) {
    // Un shard de 2 lettres peut avoir le même nom qu'un fichier de 3 sur un système
    // insensible à la casse ? Non — mais `l'` et consorts ne sont plus des clés depuis que
    // l'apostrophe est un séparateur, et les clés restantes sont [a-z0-9] : sûres en URL.
    const body = JSON.stringify(obj);
    bytes += Buffer.byteLength(body);
    writeFileSync(join(outDir, `${k}.json`), body, "utf-8");
  }
  // Les termes écartés sont NOMMÉS, pas seulement comptés — c'est ce qui permet au client de
  // distinguer « ce mot n'est nulle part » de « ce mot est partout ». Sans cette liste,
  // chercher « prière du matin » ne rendait rien : le ET butait sur un mot absent de l'index
  // alors qu'il est prononcé dans 76 sermons sur 131. Un mot ubiquitaire ne doit pas
  // contraindre la recherche, exactement comme un mot vide.
  const manifest = {
    docs: docs.map((d) => d.id),
    shards: [...shards.keys()].sort(),
    terms: kept.length,
    common: [...postings.entries()].filter(([, ps]) => ps.length > maxDf).map(([t]) => t).sort(),
  };
  writeFileSync(join(outDir, "manifest.json"), JSON.stringify(manifest), "utf-8");

  return { docs: docs.length, terms: kept.length, dropped, shards: shards.size, kb: Math.round(bytes / 1024) };
}
