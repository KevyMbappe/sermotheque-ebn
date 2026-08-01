# POC Web — état au 2026-07-30 (WIP)

> Note de reprise. Le plan complet est dans [`WEB-POC.md`](WEB-POC.md) ; ce fichier dit
> **où on en est exactement** et **quoi faire ensuite**. Écrit pour qu'une nouvelle session
> (autre machine, autre compte) puisse reprendre sans rien redécouvrir.

## Contexte en une phrase

Le catalogue compte **139 sermons enrichis sur 517** ; ce POC est la **première fenêtre de
consommation** (décision d'architecture : *le catalogue est l'actif, les apps sont des fenêtres
remplaçables*). SPA statique **Vite + React** dans `apps/web-poc/`, données projetées depuis
`data/catalog/` au build. Objectif : montrer aux anciens ce que le pipeline produit, et
dé-risquer la future bibliothèque WordPress.

## ✅ Fait (et vérifié à l'écran)

- **Pipeline de données** `scripts/build-data.mjs` — lit `data/catalog/catalog.json`, publie
  `public/data/catalog.json` (fiches enrichies uniquement, champs utiles, URLs d'embed résolues)
  + copie les VTT dans `public/data/vtt/`. Sortie mesurée :
  **131 sermons publiés · 655 Ko · 131 lisibles · 131 avec chapitres · 131 transcriptions.**
  *(131 et non 139 : les **8 sermons du POC initial (M5b)** ont été enrichis avec l'ancien
  schéma allégé, sans `description`/`invitation` — le filtre exige `description && summary`.
  Les ré-enrichir depuis leurs transcriptions déjà commitées coûte ~0,55 $ et les ferait
  entrer dans le site : `run_enrichment.py --ids sc-2193798131,sc-2117744874,sc-2007594779,
  sc-1947861891,sc-1900264623,sc-1747280997,sc-1650117738,yt-IqNmh_XGULE`.)*
  Tourne en pré-étape de `dev` et `build`.
- **Librairies** : `lib/vtt.js` (parse VTT — port JS de `_vtt_cues` de `pipeline/build_entry.py`,
  pour que les timestamps correspondent exactement à ceux ancrés par l'enrichissement),
  `lib/player.js` (**abstraction lecteur** : une interface `seekTo`/`onTime` unique par-dessus
  SoundCloud Widget API et YouTube IFrame API), `lib/data.js` (chargement, recherche repliée
  sans accents, filtres croisés, ordre canonique des 66 livres + libellés FR).
- **App** : routing par hash (`#/`, `#/sermon/:id`, `#/livres`, `#/series`, `#/predicateurs`),
  en-tête/pied, états de chargement et d'erreur.
- **Accueil** : recherche plein-texte + 4 filtres croisés (livre, série, prédicateur, type)
  avec compteurs dynamiques, grille de cartes, pagination « afficher plus ».
- **Page sermon** : en-tête (Écriture, prédicateur + badge ♪ si identifié par empreinte vocale,
  série, date, invitation), lecteur, résumé, points clés, citations avec bouton « ▶ Écouter à
  12:34 », questions, chapitres cliquables, passages cités, thèmes, références, « dans la même
  série ».
- **Transcription synchronisée** : chargement à la demande, surlignage de la cue courante,
  clic = saut, case « suivre la lecture ».
- **Styles** : sobres (serif, brun chaud), responsive, **thème sombre** via `prefers-color-scheme`.
- **Vérifié** : `npm install` OK (39 paquets), serveur de dev OK, **accueil rendu correctement
  à l'écran** (capture d'écran : 131 prédications, filtres, cartes complètes).

## ⏳ Reste à faire

1. ~~**Page sermon**~~ — ✅ 2026-08-01. Rendu vérifié en émulation (en-tête, invitation, résumé,
   points clés, chapitres, transcription), et **le saut au timestamp a été confirmé sur desktop
   par l'auteur** : clic sur un chapitre → le lecteur saute au bon endroit. La dégradation
   gracieuse a aussi été observée (conteneur sans accès à SoundCloud : message + lien direct).
   C'était LE point à valider — il l'est.
2. **Vérifier un sermon YouTube** (ex. `#/sermon/yt-IqNmh_XGULE`) — l'API IFrame est un chemin
   de code distinct de SoundCloud, encore jamais exercé (le conteneur de dev bloque YouTube).
3. **Vérifier un sermon EN** (badge langue ; l'enrichissement reste en français, c'est voulu).
4. ~~**`npm run build`**~~ — ✅ 2026-08-01 : premier build réel (38 modules, 164 Ko JS / 53 Ko
   gzip), servi par `vite preview`, routing par hash OK.
5. ~~**Workflow GitHub Pages**~~ — ✅ 2026-08-01 : `.github/workflows/deploy-poc.yml` écrit
   (build sur push `main` touchant `apps/web-poc/**` ou `data/catalog/**`, plus
   `workflow_dispatch` ; `configure-pages@v5` avec `enablement: true` active Pages tout seul).
   **Le repo est passé public** (décision #55) → Pages est gratuit, le repli payant est caduc.
   ⏳ Reste : **fusionner dans `main`** — un workflow ne se déclenche pas depuis une branche,
   et l'environnement `github-pages` n'accepte par défaut que la branche par défaut.
6. **Responsivité — ✅ mesurée et corrigée le 2026-08-01** (Playwright, `scrollWidth` vs
   `clientWidth` à 320/360/375/390/414/768). Trois débordements horizontaux réels corrigés :
   en-tête sans `flex-wrap`, enfants de `.filters` à `min-width:auto`, `.grid` en
   `minmax(280px,…)`. Toutes les largeurs sont propres. À noter : le CSS reste **fluide mais
   pas mobile-first** (base desktop + un point de rupture `max-width: 820px`).
7. ~~**Protocole de maintenance**~~ — ✅ fait le 2026-07-30 : entrée build-log **M6a** +
   **décision #54** dans `docs/SERMOTHEQUE.md`, statut/roadmap resynchronisés dans `CLAUDE.md`,
   `README.md`, `docs/PRD.md` (#37) et `docs/SYNTHESE.md`. À re-toucher quand le POC sera
   réellement livré (page sermon vérifiée + déployée).

## Pièges connus / décisions déjà prises

- **`public/data/` est gitignoré** — c'est un artefact de build, régénéré par `npm run data`.
  Une nouvelle machine doit lancer `npm install` puis `npm run dev` (qui régénère les données).
- **`vite.config.js`** : `base: '/sermotheque-ebn/'` (nom du repo, pour Pages). Surchargeable
  via `VITE_BASE=/`.
- **Pas de lib d'index de recherche** : à 131 fiches un filtre naïf est instantané. À revoir
  seulement si le catalogue publié dépasse ~1000 fiches.
- **Dégradation gracieuse assumée** : si le SDK d'un lecteur est bloqué, l'iframe reste
  écoutable et un message le dit — on perd le saut au timestamp, pas l'écoute.
- Hors périmètre : comptes, dons, PWA/offline, i18n de l'UI, SEO/SSG, analytics.

## État du reste du projet (rappel)

- **Capture audio : en pause à 139/517 transcriptions** (+ 217 empreintes vocales), 0 échec.
  Reprendre avec `./.venv/bin/python pipeline/run_enrichment.py --source all --no-enrich`
  (résumable, $0 d'API, mais plusieurs heures de calcul/chauffe).
- **Enrichissement : 139 fiches** ; les 378 restantes coûteront **~27 $** en Sonnet une fois
  capturées (378 × 0,0705 $ ; lecture depuis les transcriptions commitées, sans re-ASR).
- ⚠️ **79 identifiants ont une empreinte vocale mais aucune transcription commitée** (59 SC /
  20 YT) alors que les deux sont écrites depuis le même téléchargement — à auditer avant de
  relancer la capture, sinon ces 79 seront re-téléchargés et re-transcrits pour rien.
- 88 tests passent (`python3 -m unittest discover -s tests`).
