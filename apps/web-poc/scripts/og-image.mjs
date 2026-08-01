/**
 * Vignettes d'aperçu (og:image) — une carte 1200×630 par sermon, générée au build.
 *
 * Pourquoi : jusqu'ici un lien partagé sur WhatsApp affichait un titre et une description,
 * sans image. Or l'encart avec image est nettement plus cliqué, et c'est le canal réel de
 * diffusion d'une Église. On fabrique donc un SVG (mise en page maîtrisée, zéro pixel à la
 * main) qu'on rastérise en PNG — les réseaux sociaux ne lisent pas le SVG.
 *
 * Le rendu est ISOLÉ derrière `available()` : si la bibliothèque native manque (plateforme
 * sans binaire pré-compilé), le build continue sans vignettes plutôt que d'échouer. Un site
 * sans images vaut mieux qu'un déploiement rouge.
 */

let Resvg = null;
let probed = false;

export async function available() {
  if (!probed) {
    probed = true;
    try {
      ({ Resvg } = await import("@resvg/resvg-js"));
    } catch {
      Resvg = null;
    }
  }
  return Boolean(Resvg);
}

const esc = (s = "") =>
  String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

/**
 * Découpe un titre en lignes. SVG ne sait pas passer à la ligne : on estime la largeur
 * moyenne d'un caractère et on coupe sur les mots. Le facteur 0,62 a été CALIBRÉ sur le
 * rendu réel — une première estimation à 0,52 faisait déborder les titres longs hors du
 * cadre, ce qui ne se voit qu'en regardant l'image produite, jamais dans le code.
 */
function wrap(text, maxChars, maxLines) {
  const words = String(text || "").split(/\s+/).filter(Boolean);
  const lines = [];
  let line = "";
  for (const w of words) {
    const next = line ? `${line} ${w}` : w;
    if (next.length <= maxChars) { line = next; continue; }
    if (line) lines.push(line);
    line = w;
    if (lines.length === maxLines) break;
  }
  if (line && lines.length < maxLines) lines.push(line);
  if (lines.length === maxLines && words.join(" ").length > lines.join(" ").length) {
    lines[maxLines - 1] = lines[maxLines - 1].replace(/[\s,;:.]+$/, "") + "…";
  }
  return lines;
}

const FONT = "DejaVu Serif, Liberation Serif, Georgia, serif";
const FONT_SANS = "DejaVu Sans, Liberation Sans, Helvetica, sans-serif";

/** Le SVG de la carte. Les couleurs sont celles du site (brun chaud sur crème). */
function cardSvg({ title: rawTitle, scripture, speaker, date }) {
  const title = String(rawTitle || "Sermon");
  const size = title.length > 70 ? 52 : title.length > 40 ? 62 : 72;
  const lines = wrap(title, Math.floor(980 / (size * 0.62)), 3);
  const startY = 300 - ((lines.length - 1) * size * 1.2) / 2;
  const meta = [speaker, date].filter(Boolean).join("  ·  ");

  return `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <rect width="1200" height="630" fill="#fbfaf8"/>
  <rect width="1200" height="14" fill="#8a5a2b"/>
  <rect x="0" y="616" width="1200" height="14" fill="#8a5a2b"/>

  ${scripture ? `<rect x="100" y="112" rx="26" width="${Math.min(900, 44 + scripture.length * 19)}" height="52" fill="#f3ece3"/>
  <text x="${100 + 26}" y="148" font-family="${FONT_SANS}" font-size="27" font-weight="600" fill="#8a5a2b">${esc(scripture)}</text>` : ""}

  ${lines
    .map((l, i) => `<text x="100" y="${startY + i * size * 1.2}" font-family="${FONT}" font-size="${size}" font-weight="600" fill="#1c1a17">${esc(l)}</text>`)
    .join("\n  ")}

  ${meta ? `<text x="100" y="486" font-family="${FONT_SANS}" font-size="30" fill="#55504a">${esc(meta)}</text>` : ""}

  <rect x="100" y="530" width="54" height="54" rx="12" fill="#8a5a2b"/>
  <text x="127" y="566" text-anchor="middle" font-family="${FONT_SANS}" font-size="22" font-weight="700" fill="#ffffff">EBN</text>
  <text x="172" y="552" font-family="${FONT_SANS}" font-size="25" font-weight="600" fill="#1c1a17">Sermothèque</text>
  <text x="172" y="578" font-family="${FONT_SANS}" font-size="20" fill="#857e75">Église Bonne Nouvelle · Poissy</text>
</svg>`;
}

/** Rend la carte en PNG. Retourne null si le rastériseur n'est pas disponible. */
export async function makeCard(fields) {
  if (!(await available())) return null;
  const svg = cardSvg(fields);
  const r = new Resvg(svg, { font: { loadSystemFonts: true }, fitTo: { mode: "width", value: 1200 } });
  return r.render().asPng();
}
