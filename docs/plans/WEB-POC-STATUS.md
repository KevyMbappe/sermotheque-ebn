# POC Web — état au 2026-08-01 (EN LIGNE)

> 🌐 **https://kevymbappe.github.io/sermotheque-ebn/** — 131 prédications publiées.

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

## 🆕 Ajouté le 2026-08-01 — partage et aperçus de lien

- **Routage par CHEMIN au lieu de `#`** (`src/lib/router.js`). Raison : les gens partagent
  en copiant l'URL de leur barre d'adresse, et tout ce qui suit un `#` n'est jamais envoyé
  au serveur — WhatsApp, Facebook et les moteurs voyaient donc *tous* les liens comme la
  même page d'accueil. Le routeur intercepte les clics internes (navigation instantanée,
  sans rechargement), respecte le clic-milieu / ⌘-clic, et gère le bouton Retour.
- **Une page HTML pré-rendue par prédication** (`scripts/prerender.mjs`, lancé après
  `vite build`) : 131 pages sermon + 3 pages de navigation + accueil + `404.html`. Chacune
  porte ses propres `<title>`, `description`, Open Graph et `canonical`, plus un `<noscript>`
  lisible sans JavaScript. Le titre retombe sur la seule accroche quand « titre — prédicateur ·
  passage » dépasse 95 caractères, pour ne pas être tronqué n'importe où par les réseaux.
- **Liens horodatés `?t=754`** : à l'arrivée le lecteur démarre à cet instant ; inversement,
  tout saut de chapitre ou de citation met l'URL à jour via `replaceState`, donc **l'adresse
  affichée pointe toujours sur le moment écouté**.
- **Bouton « Partager » sur chaque chapitre et chaque citation** (`components/ShareAt.jsx`) :
  `navigator.share` sur mobile, presse-papier sinon, et affichage de l'URL en dernier recours
  (le presse-papier est refusé hors HTTPS). ⚠️ Le partage **ne dépend pas du lecteur** : les
  horodatages viennent des données, donc un lien reste copiable même si le SDK SoundCloud
  n'a pas chargé.

**Vérifié** (Playwright) : accès direct à une page pré-rendue, `?t=` lu, clic carte →
`pushState` sans rechargement, bouton Retour, navigation d'en-tête, 9 boutons de partage sur
la fiche témoin, 0 erreur JS, et toujours aucun débordement horizontal de 320 à 768 px.

**Limite connue** : pas de vignette (`og:image`) — les aperçus affichent titre + description,
sans image. En générer une par prédication demanderait un rendu graphique au build.

## 🆕 Ajouté le 2026-08-01 — parcourir par passage biblique

Rendu possible par la normalisation OSIS des citations (#56). `src/lib/passages.js` construit
l'index `livre → chapitre → prédications` **côté client** (une seule source de vérité, pas de
second fichier à synchroniser), en distinguant **prêché** (`scripture_osis`) et **cité**
(`scripture_refs_osis`) — la relation la plus forte l'emporte quand les deux s'appliquent.

- **`/livres`** devient une vraie porte d'entrée : **54 tuiles** dans l'ordre du canon avec les
  deux compteurs, là où le regroupement sur `scripture_book` n'en montrait que 22.
- **`/livres/:book`** : ce qui a été prêché sur le livre, puis un index chapitre par chapitre.
- **Fiche sermon** : les passages cités sont devenus des liens.

⚠️ **Piège évité, à ne pas réintroduire** : les puces sont construites depuis les ids OSIS, **pas**
en appariant index par index avec `scripture_refs`. Les deux listes divergent sur 2 lignes sur
134 (`scripture_refs_osis` est dédupliqué, et une chaîne peut donner plusieurs ids) — s'y fier
donnerait un lien juste 98 fois sur 100, donc faux sur une vraie page. Le texte français
d'origine est conservé sous les puces, où la précision au verset survit.

`src/lib/books.js` a été extrait de `data.js` : la table des livres est désormais partagée avec
`scripts/prerender.mjs` (qui ne peut pas importer `data.js`, lequel utilise `fetch` et
`import.meta.env`) au lieu d'être recopiée.

**Vérifié** : 54 tuiles, Galates 22 prêchées / 32 citations, Malachie–Jude–Esther atteignables
pour la première fois, puce → page de livre, 0 erreur JS, toujours propre de 320 à 768 px.

## 🆕 Ajouté le 2026-08-01 — parcourir par thème

Rendu possible par le vocabulaire curé (#57). Avant : 594 étiquettes libres pour 139 fiches,
451 vues une seule fois — les thèmes ne servaient que de matière à la recherche plein texte,
sans filtre ni navigation possible.

- **`/themes`** : les 44 catégories avec leur nombre de prédications.
- **`/themes/:id`** : les prédications du thème (Sanctification 51, L'Église 40, Péché et chute 39…).
- **Fiche sermon** : les puces de thème sont devenues des liens ; les étiquettes libres restent
  affichées dessous, parce que leur précision dit ce que 44 catégories ne peuvent pas dire.
- **Filtre par thème** sur l'accueil, et les 44 pages de thème sont pré-rendues.

`public/data/topics.json` ne contient que `id` + `label` : les alias servent au pipeline, pas
au navigateur.

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
   Fusionné dans `main` le 2026-08-01 ; le workflow s'est déclenché seul.
   ⚠️ **Premier passage en échec** — `npm ci`, la projection (131 sermons) et le build Vite
   passent, mais `actions/configure-pages` s'arrête sur *« Create Pages site failed:
   Resource not accessible by integration »*. L'option `enablement: true` ne peut pas
   fonctionner : créer le site Pages exige les droits admin, que le `GITHUB_TOKEN` d'un
   workflow n'a pas. Option retirée.
   ✅ **EN LIGNE depuis le 2026-08-01** : https://kevymbappe.github.io/sermotheque-ebn/
   (run n°3 vert de bout en bout, `deploy-pages@v4` à 12:38:03). Il aura fallu trois passages :
   `enablement: true` (impossible — droits admin), puis l'activation **manuelle** de Pages
   (Settings → Pages → Source = « GitHub Actions »), qu'aucun workflow ne peut faire à ta place.
   Le build, lui, a réussi dès le premier essai. **À retenir pour un futur déploiement : cette
   case doit être cochée à la main, une fois, sur tout nouveau dépôt.**
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
