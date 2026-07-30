# POC Web App — Sermothèque EBN

## Contexte

Le catalogue possède maintenant **139 sermons enrichis** (résumés, descriptions, invitations, chapitres horodatés, citations, thèmes, Écritures, orateurs audio-vérifiés) sur 517, validés par un schéma gelé (`data/catalog/sermon.schema.json`, #53). L'architecture du projet dit : *« le catalogue est l'actif ; toute app est une fenêtre remplaçable »*. Ce POC est la **première fenêtre de consommation** — il matérialise la valeur du pipeline pour les anciens et dé-risque la future bibliothèque WordPress. Décision existante honorée : **index statique, zéro serveur**.

## Ce qu'on construit

SPA statique **Vite + React** dans `apps/web-poc/`, déployée sur **GitHub Pages**, données chargées depuis des fichiers statiques générés au build depuis `data/catalog/`.

### 1. Pipeline de données (build-time)
Script Node `apps/web-poc/scripts/build-data.mjs` :
- Lit `data/catalog/catalog.json` (1,1 Mo) → écrit `public/data/catalog.json` **filtré aux fiches enrichies** (139) + champs utiles seulement (~300 Ko).
- Copie les `.vtt` des sermons enrichis → `public/data/vtt/<id>.vtt` (pour la transcription synchronisée).
- Résout les URLs d'embed : SoundCloud via `https://w.soundcloud.com/player/?url=https://api.soundcloud.com/tracks/<soundcloud_id>` ; YouTube via `https://www.youtube.com/embed/<youtube_id>`.
- Tourne en prebuild (`npm run build` l'appelle) — le site est toujours le reflet du catalogue commité.

### 2. Pages / composants
- **Accueil = liste + filtres + recherche** : grille de cartes (titre, description-accroche, orateur + badge provenance, série, Écriture, durée, langue). Filtres : livre biblique (`scripture_book`), série, orateur, langue, type (`kind`). Recherche plein-texte client-side (titre, résumé, thèmes, description) — simple `includes` normalisé au POC, pas de lib d'index tant que 139 fiches (instantané).
- **Page sermon** (`/sermon/:id`, hash-routing pour Pages) :
  - En-tête : titre, Écriture, orateur, série, date, invitation.
  - **Lecteur embarqué** (SoundCloud Widget API ou YouTube IFrame API selon la source).
  - **Chapitres cliquables** : la liste `chapters[{title, t}]` saute le lecteur à `t` (SC Widget `seekTo(ms)` / YT `seekTo(s)`) — le différenciateur du pipeline.
  - Corps : résumé, points clés, citations (avec bouton « ▶ à 12:34 »), questions de réflexion, références citées, passages bibliques.
  - **Transcription synchronisée** : parse du VTT (réutiliser la logique de `_vtt_cues` de `pipeline/build_entry.py:65` portée en JS), affichage en cues ; surlignage de la cue courante via polling du temps lecteur (~500 ms) ; clic sur une cue = seek. Repli gracieux : si le lecteur ne remonte pas le temps (SC parfois capricieux), la transcription reste lisible et cliquable sans suivi.
- **Navigation par livre / série / orateur** : trois vues d'agrégats (comptes par livre OSIS ordonné canoniquement, séries avec progression x/y enrichis, orateurs avec photo-placeholder).
- FR uniquement pour l'UI du POC (contenu déjà FR-dominant).

### 3. Déploiement GitHub Pages
- Workflow `.github/workflows/deploy-poc.yml` : sur push de `apps/web-poc/**` ou `data/catalog/**` → build Vite → deploy `actions/deploy-pages`.
- `vite.config.js` avec `base: '/sermotheque-ebn/'` (nom du repo).
- ⚠️ **Repo privé** : Pages sur repo privé exige un plan GitHub payant. Si bloqué au déploiement : repli = rendre le repo public **ou** publier le build seul dans un petit repo public `sermotheque-poc` (le workflow pousse `dist/`). À trancher au moment du premier deploy, pas avant.

## Fichiers créés (tous nouveaux, rien de modifié hors workflow)
```
apps/web-poc/
  package.json, vite.config.js, index.html
  scripts/build-data.mjs
  src/main.jsx, App.jsx (hash router)
  src/lib/data.js (chargement+types), vtt.js (parse), player.js (abstraction SC/YT seek+time)
  src/pages/Home.jsx, Sermon.jsx, Browse.jsx
  src/components/SermonCard.jsx, Filters.jsx, Chapters.jsx, Transcript.jsx, Player.jsx
.github/workflows/deploy-poc.yml
```

## Vérification
1. `node scripts/build-data.mjs` → `public/data/` contient 139 fiches + les VTT.
2. `npm run dev` → parcourir : filtres croisés, recherche « incarnation », page du sermon Luc 1:26-38 (`sc-2338530545`) : lecteur SC démarre, **clic chapitre 3 → saut au bon timestamp**, transcription suit et surligne.
3. Vérifier un sermon YouTube-only (ex. `yt-IqNmh_XGULE`) : lecteur YT + chapitres OK.
4. Vérifier un sermon EN (badge langue, contenu FR de l'enrichissement).
5. `npm run build && npm run preview` → routing hash OK en build.
6. Push → workflow Pages vert → URL publique testée sur mobile.
7. Maintenance : entrée build-log `docs/SERMOTHEQUE.md` (M6a), MAJ `CLAUDE.md`/`README.md` (première fenêtre de consommation livrée), commit + push.

## Hors périmètre (assumé)
Comptes, dons, PWA/offline, i18n UI, SEO/SSG, analytics, les 378 sermons non enrichis (ils apparaîtront automatiquement aux prochains runs d'enrichissement — le build-data filtre sur la présence d'enrichissement).
