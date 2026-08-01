#!/usr/bin/env python3
"""
Vocabulaire curé des thèmes — la moitié interrogeable des `topics`.

Le problème mesuré : l'enrichissement produit des étiquettes libres, riches mais
non contrôlées. Sur les 139 fiches enrichies, **1 086 étiquettes pour 594 formes
distinctes, dont 451 vues une seule fois**. « Herméneutique » et « Herméneutique
biblique » coexistent, « Union avec Christ » et « Union à Christ » aussi, tout
comme « Image de Dieu », « Imago Dei » et « Image de Dieu (Imago Dei) ». Une liste
pareille ne peut servir ni de filtre, ni de navigation : elle n'a pas de fond.

La décision d'origine prévoyait un **vocabulaire curé (~30-60 termes), amorcé
depuis le corpus puis confirmé par un humain**. Ce module l'implémente :

  * `VOCABULARY` — les catégories canoniques, chacune avec ses alias. Les alias
    ont été relevés dans les données réelles, pas imaginés.
  * `canonicalize(label)` — une étiquette libre → un id canonique, ou None.
  * `normalize_topics(labels)` — la liste d'une fiche → ids canoniques, dédupliqués.

Deux principes, les mêmes que pour les citations OSIS (#56) :

  1. **Additif** — `topics` reste la moitié affichable, riche et fidèle au message ;
     `topics_canonical` est la moitié interrogeable. On ne réécrit pas la sortie du
     LLM, on lui ajoute une clé de tri.
  2. **Dérivé, jamais stocké** — recalculé à chaque writeback, donc enrichir le
     vocabulaire améliore tout le catalogue sans un seul appel API.

Ce qui ne correspond à rien reste **non classé**, compté et affiché par
`--report`. On ne force pas une étiquette dans une case pour faire joli : un
thème mal rangé est pire qu'un thème absent, parce qu'il ment silencieusement.

Usage :
    python3 pipeline/topics.py --report     # couverture + non classés, pour étendre le vocabulaire
    python3 pipeline/topics.py --write      # écrit data/catalog/topics.json (vocabulaire + stats)
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "data" / "catalog" / "catalog.json"
OUT = ROOT / "data" / "catalog" / "topics.json"


def fold(s: str) -> str:
    """Minuscules sans accents — comparer « Ézéchiel » et « ezechiel » sans surprise.

    ATTENTION : ne jamais écrire d'accent littéral dans les alias ci-dessous. Un
    caractère accentué tapé dans le source peut être stocké en NFD (a + accent
    combinant) et la comparaison échoue alors silencieusement — le piège qui a
    coûté une heure sur #56. Tout est comparé APRÈS pliage, donc en ASCII.

    Les ligatures sont dépliées explicitement : la décomposition Unicode ne touche
    PAS « œ », si bien que « Pacte des œuvres » ne rencontrait jamais l'alias
    « pacte des oeuvres » — muettement, comme toujours avec ce genre de bug.
    """
    s = (s or "").lower().replace("œ", "oe").replace("æ", "ae")
    return "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c))


# ---------------------------------------------------------------------------
# Le vocabulaire. L'ORDRE COMPTE : la première catégorie dont un alias apparaît
# dans l'étiquette gagne, donc le spécifique doit précéder le général
# (« crainte de l'homme » avant « crainte de dieu », « peche originel » avant
# « peche »). Les alias sont en ASCII plié, cf. fold().
# ---------------------------------------------------------------------------
VOCABULARY: list[dict] = [
    # --- Écriture ---------------------------------------------------------
    {"id": "hermeneutique", "label": "Herméneutique",
     "aliases": ["hermeneutique", "revelation progressive", "typologie", "typologique",
                 "interpretation litterale", "prefiguration", "theologie biblique",
                 "christocentrisme", "dispensationalisme", "dispensations", "prophetie", "prophetes", "continuite de l'evangile", "unite de la bible",
                 "psaumes de sagesse"]},

    # --- Dieu -------------------------------------------------------------
    {"id": "ecriture", "label": "Autorité de l'Écriture",
     "aliases": ["sola scriptura", "autorite de la bible", "autorite biblique", "autorite de l'ecriture",
                 "autorite et suffisance", "suffisance de l'ecriture", "bibliologie", "ecriture sainte",
                 "parole de dieu", "inspiration des ecritures", "canon biblique",
                 "bible", "canon des ecritures", "canon du nouveau testament", "lecture de la bible", "meditation de la parole", "perspicuite", "suffisance des ecritures", "revelation"]},
    {"id": "trinite", "label": "Trinité", "aliases": ["trinite", "trinitaire"]},
    {"id": "souverainete", "label": "Souveraineté de Dieu",
     "aliases": ["souverainete", "souverain de dieu", "grace souveraine", "monergisme",
                 "election", "predestination", "decrets de dieu", "causes secondes",
                 "causes secondaires", "causalite secondaire",
                 "decrets eternels", "decrets divins", "volonte decretive", "compatibilisme", "responsabilite humaine", "doctrines de la grace", "universalisme", "arminianisme", "incapacite totale"]},
    {"id": "providence", "label": "Providence",
     "aliases": ["providence", "theodicee", "probleme du mal", "discipline divine"]},
    {"id": "attributs", "label": "Attributs de Dieu",
     "aliases": ["attributs de dieu", "transcendance", "immuabilite", "saintete de dieu",
                 "amour de dieu", "patience de dieu", "colere de dieu", "fidelite de dieu",
                 "justice de dieu", "misericorde de dieu", "bonte de dieu",
                 "saintete divine", "misericorde", "justice et equite", "simplicite divine", "existence de dieu", "condescendance divine", "el elyon", "presence de dieu", "vision de dieu", "benediction divine"]},
    {"id": "gloire", "label": "Gloire de Dieu",
     "aliases": ["gloire de dieu", "glorification de dieu", "doxologie",
                 "theologie de la gloire", "sola deo gloria", "soli deo gloria", "gloire du christ"]},

    # --- Christ -----------------------------------------------------------
    {"id": "incarnation", "label": "Incarnation",
     "aliases": ["incarnation", "naissance virginale", "noel",
                 "kenose"]},
    {"id": "christologie", "label": "Christologie",
     "aliases": ["christologie", "union hypostatique", "double nature", "heresies christologiques",
                 "second adam", "personne du christ", "deite du christ", "propheties messianiques",
                 "messie",
                 "ascension", "seigneurie du christ", "royaute de christ", "trois offices", "obeissance active", "melchisedec", "melchisedek", "melchisedech", "christophanie", "unicite de jesus", "deux adam",
                 "mystere de la piete", "mysteres de la piete"]},
    {"id": "expiation", "label": "Œuvre de Christ et expiation",
     "aliases": ["substitution penale", "justice substitutive", "expiation", "propitiation",
                 "redemption", "mediation", "mediateur", "sacerdoce", "souverain sacrificateur",
                 "intercession", "croix", "sacrifice de christ", "oeuvre de christ",
                 "oeuvre substitutive", "reconciliation", "paix avec dieu", "abandon du christ"]},
    {"id": "resurrection", "label": "Résurrection",
     "aliases": ["resurrection", "premices"]},

    # --- Saint-Esprit -----------------------------------------------------
    {"id": "pneumatologie", "label": "Le Saint-Esprit",
     "aliases": ["pneumatologie", "saint-esprit", "saint esprit", "esprit saint",
                 "fruit de l'esprit", "fruits de l'esprit", "dons spirituels",
                 "marche selon l'esprit", "cessationnisme"]},

    # --- L'homme et le péché ---------------------------------------------
    {"id": "imago_dei", "label": "L'homme à l'image de Dieu",
     "aliases": ["imago dei", "image de dieu", "dignite humaine", "anthropologie biblique",
                 "etat originel", "anthropologie",
                 "constitution de l'homme", "dichotomie", "trichotomie", "vie de l'ame"]},
    {"id": "peche", "label": "Péché et chute",
     "aliases": ["peche originel", "depravation totale", "hamartologie", "chute", "corruption de la nature",
                 "tentation", "idolatrie", "hypocrisie", "convoitise", "desobeissance",
                 "anthropologie du peche", "coupabilite", "peche",
                 "culpabilite originelle", "pollution originelle", "mort spirituelle", "cecite spirituelle", "endurcissement", "adultere spirituel", "pharisaisme", "libertinisme"]},

    # --- Le salut ---------------------------------------------------------
    {"id": "justification", "label": "Justification par la foi",
     "aliases": ["justification", "justice imputee", "imputation", "sola fide",
                 "foi et oeuvres"]},
    {"id": "regeneration", "label": "Régénération et conversion",
     "aliases": ["regeneration", "nouvelle naissance", "conversion", "appel efficace",
                 "nouvelle nature", "circoncision du coeur", "transformation du coeur"]},
    {"id": "foi_repentance", "label": "Foi et repentance",
     "aliases": ["foi salvatrice", "repentance", "authenticite de la foi", "foi vivante",
                 "confiance en dieu", "incredulite",
                 "foi et doute", "coherence de la foi", "affections religieuses", "tristesse selon dieu"]},
    {"id": "union_christ", "label": "Union avec Christ",
     "aliases": ["union avec christ", "union a christ", "union au christ",
                 "identite en christ", "co-heritage"]},
    {"id": "adoption", "label": "Adoption filiale",
     "aliases": ["adoption", "filiation"]},
    {"id": "sanctification", "label": "Sanctification",
     "aliases": ["sanctification", "croissance spirituelle", "croissance en saintete",
                 "mortification", "saintete pratique",
                 "saintete et integrite", "integrite morale", "orthopraxie", "caractere chretien", "douceur", "temperance", "maitrise de soi", "vertus theologales", "affections"]},
    {"id": "perseverance", "label": "Persévérance et assurance",
     "aliases": ["perseverance", "assurance du salut", "securite du croyant", "apostasie",
                 "decouragement"]},
    {"id": "glorification", "label": "Glorification",
     "aliases": ["glorification du croyant", "etat futur du croyant",
                 "glorification"]},
    {"id": "grace", "label": "Grâce",
     "aliases": ["moyens de grace", "grace de dieu", "don de dieu", "gratuite du salut",
                 "sola gratia", "grace commune", "faiblesse et grace", "evangile de la grace"]},
    {"id": "soteriologie", "label": "Le salut (vue d'ensemble)",
     "aliases": ["soteriologie", "ordo salutis", "salut",
                 "universalite de l'evangile"]},

    # --- Alliances et Loi -------------------------------------------------
    {"id": "alliances", "label": "Théologie des alliances",
     "aliases": ["alliance", "alliances", "pacte des oeuvres", "pacte de grace",
                 "representation federale", "proto-evangile", "protoevangile",
                 "promesses et accomplissement", "accomplissement",
                 "theologie du pacte", "theologie federale", "representativite federale"]},
    {"id": "loi_evangile", "label": "Loi et Évangile",
     "aliases": ["loi et evangile", "legalisme", "antinomisme", "liberte chretienne",
                 "usage de la loi", "loi morale",
                 "theologie de la loi", "relation loi-evangile", "loi du christ", "grands commandements"]},

    # --- L'Église ---------------------------------------------------------
    {"id": "ecclesiologie", "label": "L'Église",
     "aliases": ["ecclesiologie", "gouvernance de l'eglise", "gouvernance d'eglise",
                 "discipline ecclesiale", "discipline et ordre", "vie d'eglise", "vie de l'eglise",
                 "koinonia", "communion fraternelle", "unite de l'eglise", "membre",
                 "congregationnalisme", "organisation ecclesiale", "organisation et structure", "vie communautaire", "fraternite", "restauration fraternelle", "eglise visible", "maturite ecclesiale", "discipulat", "ordonnances de l'eglise", "reveil"]},
    {"id": "ministeres", "label": "Ministères et charges",
     "aliases": ["diaconat", "diacre", "ancien", "qualification", "ministere pastoral",
                 "leadership serviteur", "sacerdoce universel", "apostolat", "autorite apostolique",
                 "appel au ministere", "vocation", "ministere feminin", "office",
                 "anciens et diacres", "gouvernance par les anciens", "role des anciens", "supervision pastorale", "ordination", "formation des responsables", "soutien des ministres", "offices de l'eglise", "ministeres de l'eglise", "discernement pastoral",
                 "leadership ecclesial", "leadership dans l'eglise", "leadership serviteur", "doctrine et conscience pure"]},
    {"id": "bapteme", "label": "Baptême", "aliases": ["bapteme",
                 "credobaptisme", "pedobaptisme"]},
    {"id": "cene", "label": "Sainte Cène", "aliases": ["cene", "sainte cene", "eucharistie"]},
    {"id": "adoration", "label": "Adoration",
     "aliases": ["adoration", "culte", "louange", "chant",
                 "sabbat", "jour du seigneur", "second commandement", "shema"]},
    {"id": "predication", "label": "Prédication",
     "aliases": ["predication", "expositionnelle", "ministere de la parole"]},

    # --- La vie chrétienne ------------------------------------------------
    {"id": "priere", "label": "Prière",
     "aliases": ["priere", "intercession", "jeune"]},
    {"id": "souffrance", "label": "Souffrance et épreuve",
     "aliases": ["souffrance", "epreuve", "affliction", "deuil", "maladie", "persecution"]},
    {"id": "famille", "label": "Famille et mariage",
     "aliases": ["mariage", "complementarite", "roles hommes-femmes", "role de l'homme",
                 "role de la femme", "parents", "education des enfants", "celibat", "foyer",
                 "complementarisme", "feminite biblique", "leadership masculin", "ordre creationnel", "roles hommes/femmes", "vie de famille"]},
    {"id": "prochain", "label": "Amour du prochain",
     "aliases": ["amour du prochain", "favoritisme", "acception de personnes", "hospitalite",
                 "pauvres", "compassion", "misericorde envers", "justice sociale", "pardon",
                 "generosite", "intendance", "acception de personne", "impartialite", "richesses et pauvrete", "ethique relationnelle", "ethique du service",
                 "amour agape", "amour (agape"]},
    {"id": "crainte_homme", "label": "Crainte de l'homme",
     "aliases": ["crainte de l'homme", "peur de l'homme", "respect humain",
                 "crainte des hommes"]},
    {"id": "crainte_dieu", "label": "Crainte de Dieu",
     "aliases": ["crainte de dieu", "crainte du seigneur"]},
    {"id": "vie_chretienne", "label": "Vie chrétienne",
     "aliases": ["vie chretienne", "ethique chretienne", "contentement", "joie chretienne",
                 "vigilance", "identite chretienne", "perseverance chretienne", "disciplines",
                 "temps", "travail", "argent", "gratitude", "humilite", "orgueil", "colere",
                 "langue", "paroles", "resolutions", "distraction",
                 "bonheur selon dieu", "fidelite", "mammon", "besoins et desirs", "excellence", "theologie de la prosperite", "estime de soi", "developpement personnel", "responsabilite morale", "integrite", "imitation du christ", "coram deo", "discernement spirituel", "paix de dieu", "ethique biblique",
                 "parabole des talents", "les deux voies", "semence et de la moisson", "coeur et obeissance"]},

    # --- Mission ----------------------------------------------------------
    {"id": "mission", "label": "Évangélisation et mission",
     "aliases": ["evangelisation", "missiologie", "mission", "temoignage", "implantation",
                 "grande commission", "apostolat missionnaire",
                 "proclamation de l'evangile"]},
    {"id": "apologetique", "label": "Apologétique",
     "aliases": ["apologetique", "deisme", "atheisme", "sciences et foi", "psychologie et foi",
                 "philosophie",
                 "pantheisme", "bible et science", "age de la terre"]},

    # --- Création et fins dernières ---------------------------------------
    {"id": "creation", "label": "Création",
     "aliases": ["creation", "creationnisme", "genese 1", "cosmologie",
                 "mandat culturel"]},
    {"id": "eschatologie", "label": "Fins dernières",
     "aliases": ["eschatologie", "jugement", "retour de christ", "parousie", "ciel", "enfer",
                 "nouvelle creation", "nouveaux cieux", "shalom", "esperance chretienne",
                 "esperance", "vie eternelle", "couronne de vie", "signes prophetiques", "doctrine du reste"]},

    # --- Histoire et confessions ------------------------------------------
    {"id": "confessions", "label": "Confessions et histoire de l'Église",
     "aliases": ["confession de foi", "1689", "reforme protestante", "histoire de l'eglise",
                 "puritain", "solas", "catechisme",
                 "theologie confessionnelle", "theologie reformee", "theologie systematique", "reformation protestante", "ordre confessionnel", "theologie pratique",
                 "formation chretienne"]},
]

BY_ID = {c["id"]: c for c in VOCABULARY}

# Étiquettes qui ne sont PAS des thèmes : ce sont des repères bibliographiques
# (un livre, un passage). Le catalogue les indexe déjà par l'Écriture (#56), et les
# ranger dans une catégorie doctrinale serait faux. On les écarte explicitement,
# plutôt que de les laisser gonfler la liste des « non classés ».
NOT_A_TOPIC = [
    # Noms de livres / passages : le catalogue les indexe deja par l'Ecriture (#56).
    # Volontairement precis : un « evangile de » trop large avalait « Evangile de la grace ».
    "epitre aux", "epitre de", "evangile selon", "evangile de luc", "evangile de marc",
    "evangile de jean", "evangile de matthieu", "actes des apotres", "livre de",
    "prophetie d'ezechiel", "ezechiel -", "ezechiel,",
]
EXACT_NOT_A_TOPIC = {"ezechiel", "philippiens", "tite 2", "1 timothee 3", "psaumes"}

# Alias compilés en motifs à FRONTIÈRES DE MOT. Sans elles, « soumission » tombait
# dans « mission » et « empechements » dans « peche » — des rattachements faux, donc
# invisibles à la relecture d'une liste de thèmes.
_COMPILED = [
    (c["id"], [re.compile(r"\b" + re.escape(fold(a)) + r"s?\b") for a in c["aliases"]])
    for c in VOCABULARY
]
_NOT_TOPIC = [re.compile(r"\b" + re.escape(fold(p))) for p in NOT_A_TOPIC]


def canonicalize(label: str) -> str | None:
    """Une étiquette libre → l'id canonique, ou None si rien ne correspond honnêtement."""
    f = fold(label).strip()
    if not f or f in EXACT_NOT_A_TOPIC or any(p.search(f) for p in _NOT_TOPIC):
        return None
    for topic_id, patterns in _COMPILED:
        for pat in patterns:
            if pat.search(f):
                return topic_id
    return None


def normalize_topics(labels) -> list[str]:
    """Les thèmes d'une fiche → ids canoniques, dédupliqués, dans l'ordre du vocabulaire."""
    found = {canonicalize(x) for x in (labels or [])}
    found.discard(None)
    return [c["id"] for c in VOCABULARY if c["id"] in found]


def label_of(topic_id: str) -> str:
    """Libellé français affichable d'un id canonique."""
    return BY_ID[topic_id]["label"] if topic_id in BY_ID else topic_id


# ---------------------------------------------------------------------------
# Rapport — c'est l'outil de curation : il montre ce qui n'entre dans aucune case,
# pour qu'un humain étende le vocabulaire en connaissance de cause.
# ---------------------------------------------------------------------------
def _load_rows():
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def report(rows=None, limit=40):
    from collections import Counter

    rows = rows if rows is not None else _load_rows()
    raw = Counter(t for r in rows for t in (r.get("topics") or []))
    mapped = Counter()
    unmapped = Counter()
    for label, n in raw.items():
        cid = canonicalize(label)
        (mapped if cid else unmapped)[label] = n

    tags_total = sum(raw.values())
    tags_mapped = sum(mapped.values())
    print(f"vocabulaire        : {len(VOCABULARY)} categories")
    print(f"etiquettes brutes  : {tags_total} occurrences / {len(raw)} formes distinctes")
    print(f"classees           : {tags_mapped} ({tags_mapped * 100 // max(tags_total, 1)}%) "
          f"sur {len(mapped)} formes")
    print(f"non classees       : {tags_total - tags_mapped} sur {len(unmapped)} formes")

    per_topic = Counter()
    for r in rows:
        for cid in normalize_topics(r.get("topics")):
            per_topic[cid] += 1
    used = [c for c in VOCABULARY if per_topic[c["id"]]]
    print(f"categories utilisees: {len(used)}/{len(VOCABULARY)}")
    print("\n-- couverture par categorie (fiches) --")
    for c in VOCABULARY:
        print(f"  {per_topic[c['id']]:4}  {c['id']:16} {c['label']}")
    empty = [c["id"] for c in VOCABULARY if not per_topic[c["id"]]]
    if empty:
        print("\n  (jamais utilisees pour l'instant : " + ", ".join(empty) + ")")

    print(f"\n-- non classees, les {limit} plus frequentes --")
    for label, n in unmapped.most_common(limit):
        print(f"  {n:3}  {label}")
    return {"raw": raw, "mapped": mapped, "unmapped": unmapped, "per_topic": per_topic}


def write_vocabulary(rows=None):
    """Écrit data/catalog/topics.json : le vocabulaire + sa couverture, pour relecture humaine."""
    from collections import Counter

    rows = rows if rows is not None else _load_rows()
    per_topic = Counter()
    for r in rows:
        for cid in normalize_topics(r.get("topics")):
            per_topic[cid] += 1
    raw = Counter(t for r in rows for t in (r.get("topics") or []))
    unmapped = {l: n for l, n in raw.items() if not canonicalize(l)}

    doc = {
        "note": ("Vocabulaire cure des themes. `topics` (libre) reste la moitie affichable ; "
                 "`topics_canonical` est derive de ce vocabulaire a chaque build. "
                 "Les etiquettes non classees sont listees ici pour etre traitees : "
                 "etendre les alias dans pipeline/topics.py, puis relancer build.py."),
        "topics": [
            {"id": c["id"], "label": c["label"], "aliases": c["aliases"], "sermons": per_topic[c["id"]]}
            for c in VOCABULARY
        ],
        "unmapped": dict(sorted(unmapped.items(), key=lambda kv: (-kv[1], kv[0]))),
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"ecrit {OUT.relative_to(ROOT)} · {len(VOCABULARY)} categories · "
          f"{len(unmapped)} formes non classees")


if __name__ == "__main__":
    if "--write" in sys.argv:
        write_vocabulary()
    else:
        report()
