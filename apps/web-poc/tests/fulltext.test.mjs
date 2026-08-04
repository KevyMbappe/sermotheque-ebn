/**
 * Tests de l'index plein-texte — `node --test` (intégré à Node, aucune dépendance, dans
 * l'esprit « pur stdlib » du pipeline Python).
 *
 * Ce qui est verrouillé ici, ce sont les pièges SILENCIEUX : un index qui se décode « avec
 * succès » sur de mauvais nombres, une apostrophe qui range un mot là où personne ne le
 * cherchera, un mot ubiquitaire qui fait échouer toute une requête. Aucun ne lève d'erreur —
 * ils rendent juste moins de résultats, et rien ne le dit.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, readdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { tokens, shardKey, MIN_TERM } from "../src/lib/tokenize.js";
import { encodePostings, decodePostings } from "../src/lib/ftcodec.js";
import { buildFulltextIndex } from "../scripts/build-fulltext.mjs";

/* ---------- tokenisation ---------- */

test("les accents sont repliés : « prière » et « priere » sont le même terme", () => {
  assert.deepEqual(tokens("Prière"), tokens("priere"));
});

test("l'apostrophe SÉPARE — sans quoi « l'Église » serait rangé sous « l'eglise »", () => {
  assert.deepEqual(tokens("l'Église"), ["eglise"]);
  assert.deepEqual(tokens("d’Abraham"), ["abraham"]); // apostrophe typographique aussi
  assert.deepEqual(tokens("aujourd'hui"), ["aujourd", "hui"]);
});

test("les mots de moins de 3 lettres sont écartés", () => {
  assert.deepEqual(tokens("la foi de Job"), ["foi", "job"]);
  assert.equal(MIN_TERM, 3);
});

test("la ponctuation sépare, et les numéros de verset tombent avec les mots courts", () => {
  // « 22 » et « 23 » passent sous les 3 caractères : c'est voulu. Chercher un numéro de
  // verset dans une transcription n'a pas de sens — les passages ont leur propre index (#56).
  assert.deepEqual(tokens("Galates 5:22-23, le fruit."), ["galates", "fruit"]);
  assert.deepEqual(tokens("en 1517, Luther"), ["1517", "luther"]);
});

test("shardKey suit le manifeste, pas une règle devinée", () => {
  const shards = new Set(["gr", "con", "co"]);
  assert.equal(shardKey("grace", shards), "gr");
  // « con » existe en 3 lettres : il gagne sur « co », sinon on lirait le mauvais fichier.
  assert.equal(shardKey("conversion", shards), "con");
  assert.equal(shardKey("compassion", shards), "co");
  assert.equal(shardKey("zebre", shards), null);
});

/* ---------- format ---------- */

test("encode → decode : aller-retour fidèle", () => {
  const postings = [
    { doc: 0, n: 7, at: [12, 480] },
    { doc: 3, n: 1, at: [3600] },
    { doc: 130, n: 42, at: [] },
  ];
  assert.deepEqual(decodePostings(encodePostings(postings)), postings);
});

test("les identifiants sont stockés en ÉCART — un décodeur naïf lirait de mauvais documents", () => {
  const encoded = encodePostings([
    { doc: 5, n: 1, at: [] },
    { doc: 9, n: 1, at: [] },
  ]);
  assert.equal(encoded, "5:1@,4:1@");
  assert.deepEqual(decodePostings(encoded).map((p) => p.doc), [5, 9]);
});

test("une entrée vide ne produit pas un posting fantôme", () => {
  assert.deepEqual(decodePostings(""), []);
  assert.deepEqual(decodePostings(undefined), []);
});

/* ---------- construction de l'index ---------- */

const vtt = (lines) =>
  "WEBVTT\n\n" +
  lines
    .map(([start, text], i) => `00:${String(start).padStart(2, "0")}.000 --> 00:${String(start + 4).padStart(2, "0")}.000\n${text}`)
    .join("\n\n");

function buildInto(docs) {
  const dir = mkdtempSync(join(tmpdir(), "ft-"));
  const stats = buildFulltextIndex(docs, dir);
  const manifest = JSON.parse(readFileSync(join(dir, "manifest.json"), "utf-8"));
  const shard = (k) => JSON.parse(readFileSync(join(dir, `${k}.json`), "utf-8"));
  const lookup = (term) => {
    const k = shardKey(term, new Set(manifest.shards));
    if (!k) return null;
    const raw = shard(k)[term];
    return raw ? decodePostings(raw) : null;
  };
  return { dir, stats, manifest, lookup, files: readdirSync(dir) };
}

test("un terme est retrouvé avec son sermon, ses occurrences et ses horodatages", () => {
  const { dir, lookup } = buildInto([
    { id: "sc-1", vtt: vtt([[0, "La circoncision du coeur"], [30, "encore la circoncision"]]) },
    { id: "sc-2", vtt: vtt([[10, "rien de particulier ici"]]) },
  ]);
  const ps = lookup("circoncision");
  assert.equal(ps.length, 1, "un seul sermon la contient");
  assert.equal(ps[0].doc, 0);
  assert.equal(ps[0].n, 2, "deux occurrences");
  assert.deepEqual(ps[0].at, [0, 30], "les deux instants, en secondes");
  rmSync(dir, { recursive: true, force: true });
});

test("un mot présent dans plus de la moitié du corpus est écarté ET NOMMÉ", () => {
  // Sans la liste `common`, le client ne pourrait pas distinguer « partout » de « nulle part »,
  // et une requête contenant ce mot ne rendrait jamais rien.
  const docs = ["a", "b", "c", "d"].map((id, i) => ({
    id,
    vtt: vtt([[0, i < 3 ? "seigneur toujours present" : "autre chose entierement"]]),
  }));
  const { dir, manifest, lookup } = buildInto(docs);
  assert.ok(manifest.common.includes("seigneur"), "écarté de l'index");
  assert.equal(lookup("seigneur"), null, "absent des shards");
  assert.ok(!manifest.common.includes("entierement"), "un mot rare reste indexé");
  rmSync(dir, { recursive: true, force: true });
});

test("deux horodatages au maximum, et jamais deux fois la même seconde", () => {
  const { dir, lookup } = buildInto([
    { id: "x", vtt: vtt([[0, "grace grace grace"], [8, "grace"], [16, "grace"]]) },
  ]);
  const [p] = lookup("grace");
  assert.equal(p.n, 5, "toutes les occurrences sont comptées");
  assert.equal(p.at.length, 2, "mais deux points d'entrée suffisent");
  assert.deepEqual(p.at, [0, 8], "et ce sont deux instants DISTINCTS");
  rmSync(dir, { recursive: true, force: true });
});

test("le manifeste liste exactement les shards écrits", () => {
  const { dir, manifest, files } = buildInto([
    { id: "x", vtt: vtt([[0, "alliance promesse esperance"]]) },
  ]);
  const written = files.filter((f) => f !== "manifest.json").map((f) => f.replace(".json", "")).sort();
  assert.deepEqual(manifest.shards, written);
  rmSync(dir, { recursive: true, force: true });
});

test("un corpus sans transcription produit un index vide, pas une erreur", () => {
  const { dir, stats, manifest } = buildInto([]);
  assert.equal(stats.docs, 0);
  assert.deepEqual(manifest.docs, []);
  assert.deepEqual(manifest.shards, []);
  rmSync(dir, { recursive: true, force: true });
});
