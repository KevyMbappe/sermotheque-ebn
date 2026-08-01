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

## 🆕 Ajouté le 2026-08-01 — nettoyage de navigation

- **Le filtre « Type » montrait deux fois « Enseignement »** : `teaching` (7) et
  `teaching_or_qa` (8) sont deux valeurs distinctes du catalogue, avec le même libellé.
  `teaching_or_qa` est le cas où le parseur n'a pas pu trancher entre un enseignement et
  une session de questions — une information utile **dans le catalogue**, pas dans un menu
  déroulant. `kindOf()` les regroupe pour tout ce qui est visible (affichage ET filtrage) :
  une seule entrée « Enseignement (15) ». Le catalogue, lui, garde la distinction intacte.
- **Page `/predicateurs` retirée** (décision de l'auteur : « ce n'est pas une compétition »).
  Argument qui la renforce : 331 des 517 lignes portent un prédicateur issu de la
  *règle par défaut* — un annuaire classé par nombre de sermons aurait présenté des
  inférences comme un palmarès. La nav est désormais **Livres · Thèmes · Séries**.
  ⚠️ Le **filtre** par prédicateur reste sur l'accueil : c'est un outil de recherche
  (« je veux réécouter Loïc »), pas un classement. À retirer aussi si l'intention est plus
  large. Les anciennes URL `/predicateurs` retombent sur l'accueil via `404.html`.

## 🆕 Ajouté le 2026-08-01 — une recherche partout où il y a une liste

`components/SearchBox.jsx`, un seul composant pour que le geste soit identique partout, et
le même pliage d'accents que le catalogue (« ezechiel » trouve « Ézéchiel »).

| Écran | Cherche dans | Vérifié |
|---|---|---|
| Accueil | titre, résumé, thèmes (existait déjà) | ✅ |
| `/livres` | nom du livre | 54 → 1 |
| `/themes` | libellé du thème | 44 → 1 |
| `/series` | nom de la série | 20 → 1 |
| `/livres/:book` | titre, accroche, prédicateur, passage | 14 résultats |
| `/themes/:id` | idem | 51 → 10 |
| **Transcription** | le texte prononcé | **2 909 → 28 lignes** |

La recherche dans la transcription est le « chercher où il dit X » que le minutage rendait
possible depuis #42 : les lignes filtrées restent cliquables, donc on saute directement au
moment. Le **suivi de lecture se suspend** pendant une recherche (il se battrait avec le
filtre) et la case est désactivée pour que ce soit visible.

⚠️ **Deux pièges rencontrés, à ne pas réintroduire :**
- Les cues filtrées gardent leur **index d'origine** ; sans ça, le surlignage de la ligne
  courante et le saut viseraient la mauvaise ligne.
- Sur une page de livre, un sermon figure à la fois dans la grille et dans l'index des
  chapitres : le compteur compte des **sermons distincts**, pas des lignes. Et la section
  « mentions sans chapitre » doit être filtrée comme les autres — oubliée au premier jet,
  elle restait affichée pendant une recherche et faussait le compte.

## 🆕 Ajouté le 2026-08-01 — recherche plein-texte, fiche papier, vignettes

**Recherche plein-texte** (`src/lib/search.js`). L'ancienne version était un `includes` sur
cinq champs, résultats rangés par date. Désormais : **tout le contenu est indexé** (citations,
questions, références comprises), **les champs sont pondérés** (titre 10, passage 8, thème 5…
question 1) donc les résultats sont classés par pertinence, et **chaque carte montre POURQUOI
elle ressort** — le champ qui a répondu + un extrait avec le terme en évidence. Le surlignage
passe par des segments JSX, jamais par du HTML injecté.
⚠️ `fold` a été sorti dans `src/lib/fold.js` : `data.js` importe `search.js` qui importait
`fold` depuis `data.js` — un cycle qui ne casse pas tant que l'usage est différé, mais c'est
un pari sur l'ordre d'évaluation.

**Fiche de groupe de maison.** Bouton « Imprimer » sur la fiche + `@media print` : le lecteur,
la transcription, la navigation et les boutons de partage disparaissent ; restent le titre, le
passage, le résumé, les points clés, les citations et **les questions de réflexion, espacées
pour écrire dessous**. Un bandeau papier porte le nom de l'Église et l'URL du sermon.

**Vignettes d'aperçu** (`scripts/og-image.mjs`). Une carte 1200×630 par sermon, SVG rastérisé
en PNG (`@resvg/resvg-js`) : bandeau brun, référence biblique, titre, prédicateur, date, logo.
131 cartes, ~5 Mo. Les pages passent en `summary_large_image`.
⚠️ Le rendu est **isolé derrière `available()`** : si le binaire natif manque sur une
plateforme, le build continue sans vignettes plutôt que d'échouer — un site sans images vaut
mieux qu'un déploiement rouge.
⚠️ Le facteur de largeur de caractère (0,62 em) a été **calibré sur l'image produite** : à
0,52 les titres longs débordaient du cadre, ce qui ne se voit qu'en regardant le PNG.

**Trouvaille de données :** **5 sermons publiés ont un titre vide** — leur titre d'origine ne
contenait *que* la référence biblique, que le parseur retire par construction. La projection
retombe sur le passage (`title || scripture_display || raw_title`), mais **c'est un défaut à
corriger en amont** : un enregistrement sans titre gênera aussi l'import WordPress.

## 🐛 Corrigé le 2026-08-01 — un menu de filtre se contraignait lui-même

Signalé à l'usage : « on sélectionne un filtre, on reclique dessus, et tous les autres
éléments sont grisés ».

Cause exacte : les compteurs de CHAQUE menu étaient calculés sur `visible`, c'est-à-dire le
corpus déjà filtré par **tous** les critères — y compris celui du menu qu'on rouvre. Après
avoir choisi « Galates », les 53 autres livres affichaient donc 0, et `disabled` les grisait.
Le menu décrivait fidèlement une sélection déjà faite, mais donnait l'impression d'être cassé.

Règle posée : **un menu ne se contraint jamais lui-même**. Ses compteurs se calculent sur le
corpus filtré par tous les AUTRES critères. Aucune option n'est plus désactivée non plus —
une liste grise inquiète, et un choix sans résultat reste réversible.

⚠️ **Piège rencontré en corrigeant** : la clé de DONNÉES et la clé de FILTRE diffèrent
(`scripture_book` vs `book`, `series_name` vs `series`). Les confondre reproduisait le bug en
plus discret — la première version du correctif ne marchait que pour `speaker` et `kind`,
où les deux clés coïncident.

Mesuré : après sélection de « Galates », les livres restent à **23/23**, les séries tombent à
3 et les thèmes à 33 ; 0 option désactivée.

## 🆕 Restructuration de la fiche sermon — 2026-08-01

Retours d'usage : « trop de blocs texte, ça fait peur » et « la transcription est trop loin
du lecteur ». Les deux disent la même chose : la page affichait **tout ce que le pipeline
avait produit**, empilé dans l'ordre où c'était commode à rendre. Un inventaire, pas une
hiérarchie. Elle mélangeait aussi deux usages qui se disputaient l'écran — **écouter**
(lecteur, chapitres, transcription) et **étudier** (résumé, points clés, citations, questions).

- **Ordre revu** : lecteur → chapitres → transcription → résumé → le reste. Chapitres et
  transcription sont désormais collés au lecteur : ils en font partie.
- **Tout est replié sauf le résumé** (`components/Section.jsx`) : chaque bloc annonce son
  titre et son nombre d'éléments, et s'ouvre d'un clic. Rien n'est supprimé.
- **L'invitation a quitté l'en-tête.** 8 lignes en italique séparaient le titre du lecteur :
  sur mobile, le lecteur commençait à ~1 250 px. Elle ouvre maintenant le résumé, et
  **le lecteur commence à 414 px** — visible sans défiler.
- **Barre de lecture collante** (`components/StickyPlayer.jsx`) : ⏮10 s, lecture/pause,
  ⏭15 s, titre, position, retour au lecteur.

### Choix de conception de la barre collante

- **On ne duplique pas le lecteur** : un second iframe voudrait dire deux flux à synchroniser.
  La barre pilote celui qui joue déjà, via `lib/player.js` (étendu avec `toggle()` et
  `nudge(±s)`).
- **Ancrée en bas**, pas sous l'en-tête : c'est là qu'arrive le pouce, et ça n'empile pas deux
  bandeaux collants.
- **Elle n'apparaît que si le lecteur est hors écran** (IntersectionObserver) et **jamais si le
  pilote n'a pas pu se brancher** — un bouton pause qui ne met rien en pause serait pire que
  pas de bouton.
- Sous 560 px les éléments secondaires s'effacent ; sous 380 px il ne reste que les commandes.

### Vérification : il a fallu simuler le SDK

Le conteneur bloque `w.soundcloud.com`, donc le pilote ne se branche jamais et la barre ne
s'affiche pas — exactement la dégradation voulue, mais elle empêche de tester. Le test sert
donc un **faux SDK SoundCloud** via l'interception réseau de Playwright, ce qui permet de
vérifier pour de vrai : apparition au défilement, bascule lecture/pause, et `↺10` depuis 60 s
qui ramène bien à 50 s.
⚠️ Piège : Playwright donne la priorité à la route enregistrée **en dernier**. La règle large
(`player/**`) doit venir AVANT la règle précise (`player/api.js`), sinon l'iframe factice sert
aussi le script et le stub ne se charge jamais.

### Deux constats du même test

- Sur desktop, la barre ne se déclenche plus au bas de page : **la fiche ne fait plus que
  1 601 px**, le lecteur reste visible. Ce n'est pas un défaut, c'est la restructuration qui
  opère.
- Replier les chapitres a rendu leurs boutons « Partager » invisibles (9 → 0). Un **partage du
  sermon entier** a donc été ajouté dans l'en-tête ; le partage horodaté reste dans les
  chapitres et les citations, là où l'instant a un sens.

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
