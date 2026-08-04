#!/usr/bin/env node
/**
 * Sermothèque EBN — POC web : pipeline de données (build-time).
 *
 * Le catalogue canonique (data/catalog/) est la source de vérité ; l'app n'est qu'une fenêtre.
 * Ce script projette ce catalogue en fichiers statiques servis par l'app :
 *   • public/data/catalog.json — les fiches ENRICHIES seulement, champs utiles, + URLs d'embed
 *   • public/data/vtt/<id>.vtt — les transcriptions horodatées (transcription synchronisée)
 *
 * Il tourne avant chaque dev/build : le site reflète toujours le catalogue commité. Les ~378
 * sermons pas encore enrichis apparaîtront d'eux-mêmes au fil des prochains runs d'enrichissement.
 */
import { readFileSync, writeFileSync, mkdirSync, existsSync, rmSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { buildFulltextIndex } from "./build-fulltext.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const APP = resolve(HERE, "..");
const ROOT = resolve(APP, "..", ".."); // racine du repo
const CATALOG = join(ROOT, "data", "catalog", "catalog.json");
const TOPICS = join(ROOT, "data", "catalog", "topics.json");
const TRANSCRIPTS = join(ROOT, "data", "catalog", "transcripts");
const OUT = join(APP, "public", "data");

// Une fiche est "enrichie" si le passage LLM lui a donné son contenu éditorial.
// (description est le champ le plus tardif du schéma — sa présence implique le reste.)
const isEnriched = (r) => Boolean(r.description && r.summary);

/** URLs d'embed selon la source. SoundCloud passe par l'API track id ; YouTube par l'id vidéo. */
function embedFor(row) {
  const { soundcloud_id: sc, youtube_id: yt } = row.media || {};
  if (sc) {
    return {
      kind: "soundcloud",
      // visual=false + les couleurs : lecteur compact, on veut la place pour nos chapitres
      url:
        `https://w.soundcloud.com/player/?url=${encodeURIComponent(
          `https://api.soundcloud.com/tracks/${sc}`
        )}&color=%23b45309&auto_play=false&hide_related=true&show_comments=false` +
        `&show_user=true&show_reposts=false&show_teaser=false&visual=false`,
      link: `https://soundcloud.com/ebn-paris`,
    };
  }
  if (yt) {
    return {
      kind: "youtube",
      // enablejsapi : indispensable pour piloter seekTo() depuis les chapitres
      url: `https://www.youtube-nocookie.com/embed/${yt}?enablejsapi=1&rel=0`,
      link: `https://www.youtube.com/watch?v=${yt}`,
      videoId: yt,
    };
  }
  return null;
}

/** Les champs dont l'UI a besoin — on laisse le reste (matching, provenance interne) au catalogue. */
function project(row) {
  return {
    id: row.id,
    // 5 sermons publiés ont un titre VIDE : leur titre d'origine ne contenait que la
    // référence biblique, que le parseur en retire par construction. On retombe donc sur
    // le passage — c'est ce qu'un humain écrirait. (Défaut de données à traiter en amont :
    // un enregistrement sans titre gênera aussi l'import WordPress.)
    title: row.title || row.scripture_display || row.raw_title || "Sermon",
    raw_title: row.raw_title,
    date: row.date,
    language: row.language,
    duration: row.audio_duration || row.video_duration || null,
    speaker: row.speaker,
    speaker_provenance: row.speaker_provenance,
    series_name: row.series_name,
    series_part: row.series_part,
    kind: row.kind,
    is_conference: row.is_conference,
    scripture_display: row.scripture_display,
    scripture_book: row.scripture_book,
    scripture_osis: row.scripture_osis,
    // contenu éditorial (le produit du pipeline d'enrichissement)
    description: row.description,
    invitation: row.invitation,
    summary: row.summary,
    key_points: row.key_points || [],
    chapters: row.chapters || [],
    key_quotes: row.key_quotes || [],
    questions: row.questions || [],
    references: row.references || [],
    topics: row.topics || [],
    // La moitié interrogeable des thèmes (#57) : le vocabulaire curé, qui rend la
    // navigation par thème possible là où 594 étiquettes libres l'interdisaient.
    topics_canonical: row.topics_canonical || [],
    scripture_refs: row.scripture_refs || [],
    // La moitié interrogeable des citations (#56) : c'est elle qui porte l'index inversé.
    scripture_refs_osis: row.scripture_refs_osis || [],
    embed: embedFor(row),
    has_transcript: false, // fixé plus bas si le VTT existe
  };
}

const rows = JSON.parse(readFileSync(CATALOG, "utf-8"));
const enriched = rows.filter(isEnriched).map(project);

// Ordre par défaut : le plus récent d'abord (date manquante en dernier).
enriched.sort((a, b) => (b.date || "").localeCompare(a.date || ""));

// Transcriptions : on ne copie que celles des fiches publiées.
rmSync(join(OUT, "vtt"), { recursive: true, force: true });
mkdirSync(join(OUT, "vtt"), { recursive: true });
const transcribed = [];
for (const s of enriched) {
  const src = join(TRANSCRIPTS, `${s.id}.vtt`);
  if (existsSync(src)) {
    const vtt = readFileSync(src, "utf-8");
    writeFileSync(join(OUT, "vtt", `${s.id}.vtt`), vtt, "utf-8");
    s.has_transcript = true;
    transcribed.push({ id: s.id, vtt });
  }
}
const vttCount = transcribed.length;

writeFileSync(join(OUT, "catalog.json"), JSON.stringify(enriched), "utf-8");

// Le vocabulaire curé (#57) : seulement id + libellé + ordre. Les alias servent au
// pipeline, pas au navigateur — inutile de les envoyer au visiteur.
const vocab = JSON.parse(readFileSync(TOPICS, "utf-8")).topics.map(({ id, label }) => ({ id, label }));
writeFileSync(join(OUT, "topics.json"), JSON.stringify(vocab), "utf-8");

// Index plein-texte des transcriptions (shardé par préfixe — voir build-fulltext.mjs).
const ft = buildFulltextIndex(transcribed, join(OUT, "ft"));

// Un petit récap : utile en CI pour voir grossir le catalogue publié.
const withEmbed = enriched.filter((s) => s.embed).length;
const withChapters = enriched.filter((s) => s.chapters.length).length;
const kb = Math.round(Buffer.byteLength(JSON.stringify(enriched)) / 1024);
console.log(
  `[build-data] ${enriched.length} sermons publiés (${kb} Ko) · ` +
    `${withEmbed} lisibles · ${withChapters} avec chapitres · ${vttCount} transcriptions`
);
console.log(
  `[build-data] index plein-texte : ${ft.terms.toLocaleString("fr")} termes sur ${ft.docs} transcriptions · ` +
    `${ft.shards} shards · ${ft.kb} Ko bruts · ${ft.dropped} termes ubiquitaires écartés`
);
if (!enriched.length) {
  console.error("[build-data] aucun sermon enrichi trouvé — le catalogue est-il à jour ?");
  process.exit(1);
}
