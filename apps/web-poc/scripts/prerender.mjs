#!/usr/bin/env node
/**
 * Sermothèque EBN — pré-rendu des pages de partage.
 *
 * Problème résolu : une SPA ne sert qu'un seul `index.html`. Quand quelqu'un colle un lien
 * de sermon dans WhatsApp ou Facebook, le robot d'aperçu ne lit que le HTML brut — il
 * n'exécute pas React. Tous les liens affichaient donc le même encart générique, sans titre
 * ni passage biblique. Pour une Église qui diffuse par WhatsApp, c'est la différence entre
 * un lien qu'on ouvre et un lien qu'on ignore.
 *
 * Ce script tourne APRÈS `vite build` : il reprend le `dist/index.html` produit (donc avec
 * les bons noms de fichiers hachés) et en écrit une copie par route, dont l'en-tête porte
 * les métadonnées propres à la page. L'application, elle, est strictement la même —
 * seul le <head> change, plus un <noscript> pour que la page dise quelque chose sans JS.
 *
 * GitHub Pages ne réécrit pas les URLs : c'est ce fichier par chemin qui rend le routage
 * par chemin possible, avec `404.html` en filet de sécurité.
 */
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
// Même table de livres que l'application — books.js est volontairement sans dépendance
// navigateur pour pouvoir être importé ici (voir son en-tête).
import { BOOK_FR } from "../src/lib/books.js";
import { available as ogAvailable, makeCard } from "./og-image.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const APP = resolve(HERE, "..");
const DIST = join(APP, "dist");
const DATA = join(DIST, "data", "catalog.json");

// URL publique — surchargeable pour un autre hébergement (SITE_URL=https://… npm run build).
const SITE = (process.env.SITE_URL || "https://kevymbappe.github.io/sermotheque-ebn/").replace(/\/?$/, "/");
const SITE_NAME = "Sermothèque — Église Bonne Nouvelle";

const esc = (s = "") =>
  String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

/** Coupe proprement sur un mot — un aperçu tronqué en plein milieu fait négligé. */
function clamp(text, max) {
  const t = String(text || "").replace(/\s+/g, " ").trim();
  if (t.length <= max) return t;
  const cut = t.slice(0, max);
  return cut.slice(0, cut.lastIndexOf(" ")).replace(/[,;:.]$/, "") + "…";
}

function metaTags({ title, description, path, image }) {
  const url = SITE + path.replace(/^\//, "");
  const img = image ? SITE + image.replace(/^\//, "") : null;
  return [
    `<title>${esc(title)}</title>`,
    `<meta name="description" content="${esc(description)}" />`,
    `<link rel="canonical" href="${esc(url)}" />`,
    `<meta property="og:type" content="article" />`,
    `<meta property="og:site_name" content="${esc(SITE_NAME)}" />`,
    `<meta property="og:locale" content="fr_FR" />`,
    `<meta property="og:title" content="${esc(title)}" />`,
    `<meta property="og:description" content="${esc(description)}" />`,
    `<meta property="og:url" content="${esc(url)}" />`,
    ...(img
      ? [`<meta property="og:image" content="${esc(img)}" />`,
         `<meta property="og:image:width" content="1200" />`,
         `<meta property="og:image:height" content="630" />`,
         `<meta name="twitter:card" content="summary_large_image" />`,
         `<meta name="twitter:image" content="${esc(img)}" />`]
      // Sans vignette, `summary_large_image` afficherait un encart vide : on retombe
      // sur la carte compacte plutôt que sur un trou.
      : [`<meta name="twitter:card" content="summary" />`]),
    `<meta name="twitter:title" content="${esc(title)}" />`,
    `<meta name="twitter:description" content="${esc(description)}" />`,
  ].join("\n    ");
}

/** Contenu lisible sans JavaScript (robots, lecteurs d'écran en cas d'échec du bundle). */
function noscript(s) {
  if (!s) return "";
  const bits = [
    `<h1>${esc(s.title)}</h1>`,
    `<p>${esc([s.speaker, s.scripture_display, s.series_name].filter(Boolean).join(" · "))}</p>`,
    s.summary ? `<p>${esc(s.summary)}</p>` : "",
    s.embed?.link ? `<p><a href="${esc(s.embed.link)}">Écouter le sermon</a></p>` : "",
  ];
  return `<noscript>${bits.join("")}</noscript>`;
}

function write(path, html) {
  const dir = join(DIST, path.replace(/^\//, ""));
  mkdirSync(dir, { recursive: true });
  writeFileSync(join(dir, "index.html"), html);
}

async function main() {
  if (!existsSync(DIST) || !existsSync(join(DIST, "index.html"))) {
    console.error("[prerender] dist/index.html absent — lancer `vite build` d'abord.");
    process.exit(1);
  }
  const template = readFileSync(join(DIST, "index.html"), "utf-8");
  // Les vignettes sont un bonus : si le rastériseur manque, on publie sans, plutôt que
  // de faire échouer le déploiement.
  const cards = await ogAvailable();
  let made = 0;
  if (!cards) console.warn("[prerender] rastériseur SVG indisponible — aperçus sans vignette");
  const sermons = JSON.parse(readFileSync(DATA, "utf-8"));

  // Le gabarit porte un <title> ET une <meta description> génériques : on retire les deux
  // avant d'injecter, sinon la description par défaut resterait en double dans le <head>
  // et les robots d'aperçu liraient la mauvaise (le dernier gagne selon les implémentations).
  const stripped = template
    .replace(/\s*<meta\s+name="description"[^>]*>/i, "")
    .replace(/<title>[\s\S]*?<\/title>/, "%%META%%");
  const render = (meta, body = "") => {
    let html = stripped.replace("%%META%%", meta);
    if (body) html = html.replace(/(<div id="root"[^>]*>)/, `$1${body}`);
    return html;
  };

  // 1) Racine : mêmes métadonnées, mais explicites (le gabarit n'a qu'un <title>).
  const homeDesc = `Les sermons de l'Église Bonne Nouvelle (Poissy) : ${sermons.length} sermons à écouter, avec résumé, chapitres horodatés et transcription — à parcourir par livre biblique, série ou prédicateur.`;
  writeFileSync(
    join(DIST, "index.html"),
    render(metaTags({ title: SITE_NAME, description: homeDesc, path: "" }))
  );

  // 2) Pages de navigation.
  const browse = [
    ["/livres", "Parcourir par livre biblique", "Tous les sermons classés par livre de la Bible."],
    ["/series", "Parcourir par série", "Les séries d'exposition suivie, dans l'ordre des textes."],
  ];
  for (const [path, t, d] of browse) {
    write(path, render(metaTags({ title: `${t} — ${SITE_NAME}`, description: d, path: path.slice(1) + "/" })));
  }

  // 3) Une page par livre biblique touché (#56). Ce sont de vraies pages d'entrée :
  // « sermon sur Malachie » est typiquement ce qu'on cherche depuis un moteur.
  const books = new Map();
  for (const s of sermons) {
    const add = (id, preached) => {
      const book = String(id || "").split(/[.\-]/)[0];
      if (!book) return;
      if (!books.has(book)) books.set(book, { preached: 0, cited: 0 });
      books.get(book)[preached ? "preached" : "cited"]++;
    };
    add(s.scripture_osis, true);
    for (const r of s.scripture_refs_osis || []) add(r, false);
  }
  for (const [book, n] of books) {
    const label = BOOK_FR[book] || book;
    const bits = [];
    if (n.preached) bits.push(`${n.preached} sermon${n.preached > 1 ? "s" : ""} sur ce livre`);
    if (n.cited) bits.push(`${n.cited} citation${n.cited > 1 ? "s" : ""} dans d'autres messages`);
    write(
      `/livres/${book}/`,
      render(
        metaTags({
          title: `${label} — sermons · ${SITE_NAME}`,
          description: `${label} dans les sermons de l'Église Bonne Nouvelle : ${bits.join(" · ")}.`,
          path: `livres/${book}/`,
        })
      )
    );
  }

  // 4) Une page par thème du vocabulaire curé (#57), même raison que pour les livres.
  const vocab = JSON.parse(readFileSync(join(DIST, "data", "topics.json"), "utf-8"));
  const topicCounts = new Map();
  for (const s of sermons) {
    for (const t of s.topics_canonical || []) topicCounts.set(t, (topicCounts.get(t) || 0) + 1);
  }
  let topicPages = 0;
  for (const { id, label } of vocab) {
    const n = topicCounts.get(id);
    if (!n) continue; // pas de page vide : elle apparaîtra quand le thème sera abordé
    write(
      `/themes/${id}/`,
      render(
        metaTags({
          title: `${label} — sermons · ${SITE_NAME}`,
          description: `${n} sermon${n > 1 ? "s" : ""} de l'Église Bonne Nouvelle sur le thème « ${label} », avec résumé, chapitres horodatés et transcription.`,
          path: `themes/${id}/`,
        })
      )
    );
    topicPages++;
  }
  write(
    "/themes/",
    render(
      metaTags({
        title: `Parcourir par thème — ${SITE_NAME}`,
        description: "Les sermons classés par thème doctrinal et pratique.",
        path: "themes/",
      })
    )
  );

  // 5) Une page par sermon — le cœur du sujet.
  for (const s of sermons) {
    // Les réseaux coupent le titre autour de 60-70 caractères. Plutôt que de laisser
    // tronquer n'importe où, on sacrifie le suffixe (prédicateur · passage) quand le
    // titre est déjà long, et on ne coupe qu'en dernier recours, sur un mot.
    // Ne pas répéter le passage quand il TIENT LIEU de titre (5 sermons dont le titre
    // d'origine n'était qu'une référence) : « Actes 1 — David · Actes 1 » fait négligé.
    const who = [s.speaker, s.scripture_display !== s.title ? s.scripture_display : null]
      .filter(Boolean).join(" · ");
    const full = `${s.title}${who ? ` — ${who}` : ""}`;
    const title = full.length <= 95 ? full : clamp(s.title, 95);
    // `description` est l'accroche écrite par l'enrichissement : c'est exactement
    // ce qu'on veut voir apparaître sous le lien. `summary` en repli.
    const description = clamp(s.description || s.summary, 200);
    const path = `/sermon/${encodeURIComponent(s.id)}/`;
    let image = null;
    if (cards) {
      const png = await makeCard({
        title: s.title,
        scripture: s.scripture_display,
        speaker: s.speaker,
        date: s.date ? new Date(s.date + "T00:00:00").toLocaleDateString("fr-FR",
          { day: "numeric", month: "long", year: "numeric" }) : "",
      });
      if (png) {
        mkdirSync(join(DIST, "og"), { recursive: true });
        writeFileSync(join(DIST, "og", `${s.id}.png`), png);
        image = `og/${s.id}.png`;
        made++;
      }
    }
    write(path, render(metaTags({ title, description, path: path.slice(1), image }), noscript(s)));
  }

  // 4) Filet : toute URL inconnue retombe sur l'app, qui affiche son propre message.
  writeFileSync(
    join(DIST, "404.html"),
    render(metaTags({ title: `Page introuvable — ${SITE_NAME}`, description: homeDesc, path: "" }))
  );

  if (cards) console.log(`[prerender] ${made} vignettes d'aperçu (1200×630)`);
  console.log(
    `[prerender] ${sermons.length} pages de sermon + ${books.size} pages de livre ` +
      `+ ${topicPages} pages de thème + ${browse.length} pages de navigation + accueil + 404`
  );
  console.log(`[prerender] URL publique : ${SITE}`);

}

await main();
