# Sermothèque EBN — le POC web

**En ligne : https://kevymbappe.github.io/sermotheque-ebn/**

> Ce fichier répond à une question restée ouverte depuis la décision #54 : *ce POC est-il le
> premier livrable public, ou un brouillon jetable une fois la bibliothèque WordPress faite ?*
> **Ni l'un ni l'autre.** Voici sa raison d'être, écrite noir sur blanc pour qu'elle cesse de se
> re-négocier à chaque itération.

## Raison d'être

Ce site existe pour répondre à une seule question : **« Regarde ce qu'on peut faire avec ces
données. »**

Le projet Sermothèque a produit un actif que personne dans l'église n'a encore vu : 131 sermons
enrichis, découpés en chapitres horodatés, transcrits mot à mot, rattachés à 54 livres bibliques
et 44 thèmes. Décrit dans un document, cet actif reste abstrait. Cliquable, il devient évident en
dix secondes.

Le POC est donc **la démonstration du potentiel du catalogue**, et cela a une conséquence directe
sur la manière de le construire : ici, **le design et les fonctionnalités ingénieuses ne sont pas
un supplément, ce sont le produit**. Une recherche qui mène à la minute exacte où un mot est
prononcé, un lien partageable sur un instant, une fiche de groupe de maison qui s'imprime — ce
sont ces choses-là qui font comprendre la valeur des données. Un site correct mais quelconque
échouerait à sa mission tout en fonctionnant parfaitement.

## Ce qu'il est — et ce qu'il n'est pas

| | |
|---|---|
| **C'est** une **vue prospective** : à quoi la bibliothèque de sermons du site de l'église pourrait ressembler à terme. | **Ce n'est pas** le site de l'église, ni son remplacement. |
| **C'est** un **terrain d'essai vivant** : on y teste une idée en un après-midi, on la montre aux anciens, on garde ou on jette. | **Ce n'est pas** un brouillon à supprimer une fois WordPress fait. |
| **C'est** une **feuille de route exécutable** : chaque fonctionnalité qui tient ici devient une spécification pour l'import WordPress — démontrée, pas décrite. | **Ce n'est pas** une maquette : il tourne sur les vraies données, et se met à jour tout seul. |
| **C'est** un **pré-production à part** : on y voit une idée en vrai avant de l'engager sur le site de l'église. | **Ce n'est pas** un environnement de test *de* WordPress : les deux sont indépendants. |

Autrement dit : le POC **précède** le site de l'église et lui **survit**. Il précède, parce qu'une
idée s'y prototype pour quelques heures de travail au lieu de plusieurs jours dans WordPress. Il
survit, parce qu'une fois la bibliothèque WordPress livrée, il reste l'endroit où l'on essaie ce
qui n'y est pas encore.

## Pourquoi ça marche : la projection au build

Le POC ne parle **jamais** au pipeline, ni à une base, ni à une API. Avant chaque `dev` et chaque
`build`, `scripts/build-data.mjs` lit le dataset canonique (`data/catalog/`) et en projette une
copie statique dans `public/data/`.

```
data/catalog/  ──projection au build──▶  public/data/  ──▶  site statique (GitHub Pages)
(source de vérité)                       (artefact)
```

Trois conséquences, qui sont exactement ce qui rend le playground viable :

1. **Il ne peut pas dériver du catalogue.** Ce qui s'affiche vient du dépôt, ou ne s'affiche pas.
2. **Il se republie tout seul.** Le workflow surveille `data/catalog/**` : la prochaine passe
   d'enrichissement met le site à jour sans toucher une ligne de code.
3. **Il est jetable sans rien perdre.** Aucune donnée ne vit ici. C'est précisément ce qui
   autorise à y expérimenter sans prudence — et ce qui distingue un playground d'un système.

## Ce qu'on peut y essayer sans risque

Tout ce qui touche à la **présentation, la navigation et la découverte** : mise en page, parcours
de lecture, nouveaux axes de navigation, formats de partage, essais A/B avec les anciens.

Ce qui **n'a rien à y faire** : la vérité des données. Un titre faux, un prédicateur mal attribué,
un passage mal parsé se corrigent **en amont**, dans le pipeline — sinon le POC devient une
deuxième source de vérité, et le projet a été bâti pour éviter exactement ça.

## Faire tourner

```bash
npm install
npm run dev      # projette les données puis lance Vite
npm run build    # projection + build + pré-rendu (185 pages) + vignettes d'aperçu
npm test         # tests de l'index plein-texte (node --test, sans dépendance)
```

## Repères

- Plan et notes de reprise : [`docs/plans/WEB-POC.md`](../../docs/plans/WEB-POC.md) ·
  [`WEB-POC-STATUS.md`](../../docs/plans/WEB-POC-STATUS.md) ← **à lire avant de toucher au code**
- Décisions : #54 (projection au build), #55 (dépôt public), #56 (citations OSIS),
  #57 (vocabulaire de thèmes), #58 (cette raison d'être) — dans
  [`docs/SERMOTHEQUE.md`](../../docs/SERMOTHEQUE.md)
