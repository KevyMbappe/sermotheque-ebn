# Synthèse du projet — Sermothèque EBN

*Document de présentation · anciens & équipe média · mis à jour le 30 juillet 2026*

> **Sermothèque** = la bibliothèque numérique des prédications de l'Église.

## En une phrase

Constituer **la bibliothèque durable des prédications de l'Église** : une base de données unique, riche et pérenne, à partir de laquelle alimenter le site web — puis, plus tard, des applications mobile et TV.

## Le principe directeur

**Le contenu est le trésor ; les plateformes ne sont que des fenêtres.** YouTube, SoundCloud, le site, les futures applications : autant de vitrines interchangeables. Ce qui dure et prend de la valeur avec les années, ce sont les **prédications elles-mêmes**, bien organisées et consultables. C'est donc cela que nous bâtissons d'abord — le reste viendra se brancher dessus.

## Le constat de départ

Les prédications sont aujourd'hui **dispersées** sur YouTube et SoundCloud, sans catalogue unifié ni possibilité de recherche par livre biblique, par prédicateur ou par série.

## Ce que l'analyse des données révèle

| Source | Quantité | Nature |
|---|---|---|
| SoundCloud | **239** prédications (audio) | Cœur des séries expositives françaises |
| YouTube — onglet Vidéos | **300** prédications | Prédications montées |
| YouTube — onglet Live | **102** cultes complets | Cultes du dimanche (~2 h) |

- **82 %** des titres SoundCloud contiennent déjà la **référence biblique** exacte — réutilisable sans aucune ressaisie. **28 livres** bibliques couverts au total.
- **26 séries** ont été reconstituées automatiquement, dans l'ordre des textes : *Épître aux Galates* (71 prédications), *aux Hébreux* (28), *de Jacques* (14), *Genèse* (13), *Ézéchiel* (11)…
- **Découverte majeure :** YouTube et SoundCloud ne sont **pas** des copies l'un de l'autre — ils sont en grande partie **complémentaires** (seulement **18 recoupements** confirmés, plus 4 traductions français/anglais). YouTube apporte **en plus** le **contenu des conférences** (CBN Paris, prédicateurs internationaux) et des **versions anglaises**. Le **véritable catalogue compte 517 prédications** (l'union des deux sources), et non 239.

## Ce qui a déjà été réalisé

- ✅ **Inventaire complet et automatisé** des deux plateformes.
- ✅ **Catalogue structuré** des 239 prédications SoundCloud (titre, passage biblique, prédicateur, série) — généré automatiquement à partir des titres existants.
- ✅ **Regroupement en séries** (26 séries ordonnées).
- ✅ **Mise en relation YouTube ↔ SoundCloud**, et identification du contenu propre à chaque plateforme.
- ✅ **Catalogue unifié des 517 prédications**, sous un format unique et figé.
- ✅ **Transcription automatique + enrichissement par IA validés et lancés :** à ce jour **139 prédications sur 517 (27 %)** sont transcrites (avec minutage, pour lire le texte synchronisé avec l'audio) **et enrichies** (résumé, plan, sujets, citations, versets cités dans le corps du message). Coût mesuré : **7 centimes de dollar par prédication** — soit **environ 27 $ pour terminer les 378 restantes**.
- ✅ **Reconnaissance du prédicateur à la voix :** une « empreinte vocale » a été calculée pour **217 prédications**, ce qui permet d'attribuer automatiquement un message à l'un des 5 prédicateurs réguliers (David, Loïc, Stephan, Nathanaël, Christian) même quand le titre ne le mentionne pas — avec 99 % de justesse sur les tests. **100 prédications** ont ainsi été attribuées par la voix.
- ✅ Tout est **versionné et sauvegardé** : durable, et reprenable par n'importe qui, à tout moment. Le dépôt est **public** depuis le 1er août 2026 — les prédications étant déjà publiques sur YouTube et SoundCloud, cela ne dévoile rien de nouveau, et cela rend l'hébergement du site gratuit.

## Où en sommes-nous exactement

Le travail se fait en deux temps, volontairement séparés : **(1)** écouter l'audio et le transcrire — c'est long, cela se fait **une seule fois**, et cela ne coûte rien ; **(2)** enrichir le texte par IA — rapide, peu coûteux, et **refaisable autant de fois qu'on veut** sans jamais réécouter l'audio.

**Le premier temps est à 27 % et actuellement en pause.** C'est la seule étape irréversible du projet, et donc la priorité : il reste **378 prédications** à transcrire, ce qui représente quelques nuits de calcul sur un Mac. Tout le reste peut attendre sans rien perdre.

## Feuille de route

| Phase | Objectif | État |
|---|---|---|
| **1 — Fondation du catalogue** | Base de données unifiée et enrichie | **En cours — 27 %** |
| **2 — Publication web** | Section « Prédications » sur le site : recherche par livre, série, prédicateur | **Maquette en ligne** |
| **3 — Applications** | Mobile + TV : un lieu dédié pour écouter/regarder, sans la distraction de YouTube | Ultérieur |

**Détail Phase 1, ce qu'il reste :** terminer la transcription des **378 prédications** restantes, puis leur enrichissement (≈ 27 $). Le contenu YouTube (conférences) est déjà intégré au catalogue.

**🌐 La maquette est consultable dès maintenant : https://kevymbappe.github.io/sermotheque-ebn/** — 131 prédications, sur ordinateur comme sur téléphone. Elle se remplira d'elle-même au fur et à mesure : chaque nouvelle prédication traitée y apparaît sans aucune intervention.

**Détail Phase 2 :** cette **maquette de site** (navigation par série / livre / prédicateur, lecteur audio, texte de la prédication défilant en synchronisation avec l'audio, saut direct à un point du message). Elle sert à **montrer concrètement aux anciens ce que le catalogue permet**, avant d'intégrer la bibliothèque dans le site WordPress existant. Elle lit directement le catalogue : elle se remplira donc d'elle-même à mesure que la Phase 1 avance.

## Ce dont nous avons besoin

- **Équipe média :** confirmer que l'audio SoundCloud ne contient **que la prédication** (sans la liturgie).
- **Anciens :** valider le principe ; prévoir, à terme, le **transfert de la propriété** (comptes, nom de domaine, dépôt) **au nom de l'Église**, afin que le projet ne dépende d'aucune personne en particulier.

## Chiffres clés

**517** prédications au catalogue (239 audios + 278 vidéos propres à YouTube) · **139 transcrites et enrichies (27 %)** · **217** empreintes vocales · **82 %** des titres SoundCloud déjà référencés bibliquement, **28 livres** couverts · **26 séries** reconstituées · **≈ 27 $** pour achever l'enrichissement.
