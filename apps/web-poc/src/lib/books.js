/**
 * Table des livres bibliques — ordre canonique et libellés français.
 *
 * Volontairement isolée de data.js : ce module ne touche ni à `fetch` ni à
 * `import.meta.env`, donc il est importable AUSSI par les scripts de build Node
 * (scripts/prerender.mjs). Une seule table, pas de copie qui dérive.
 */
/** Ordre canonique des livres — un catalogue biblique se parcourt dans l'ordre du canon. */
export const BOOK_ORDER = [
  "Gen","Exod","Lev","Num","Deut","Josh","Judg","Ruth","1Sam","2Sam","1Kgs","2Kgs","1Chr","2Chr",
  "Ezra","Neh","Esth","Job","Ps","Prov","Eccl","Song","Isa","Jer","Lam","Ezek","Dan","Hos","Joel",
  "Amos","Obad","Jonah","Mic","Nah","Hab","Zeph","Hag","Zech","Mal",
  "Matt","Mark","Luke","John","Acts","Rom","1Cor","2Cor","Gal","Eph","Phil","Col","1Thess",
  "2Thess","1Tim","2Tim","Titus","Phlm","Heb","Jas","1Pet","2Pet","1John","2John","3John","Jude","Rev",
];
export const BOOK_FR = {
  Gen:"Genèse",Exod:"Exode",Lev:"Lévitique",Num:"Nombres",Deut:"Deutéronome",Josh:"Josué",
  Judg:"Juges",Ruth:"Ruth","1Sam":"1 Samuel","2Sam":"2 Samuel","1Kgs":"1 Rois","2Kgs":"2 Rois",
  "1Chr":"1 Chroniques","2Chr":"2 Chroniques",Ezra:"Esdras",Neh:"Néhémie",Esth:"Esther",Job:"Job",
  Ps:"Psaumes",Prov:"Proverbes",Eccl:"Ecclésiaste",Song:"Cantique",Isa:"Ésaïe",Jer:"Jérémie",
  Lam:"Lamentations",Ezek:"Ézéchiel",Dan:"Daniel",Hos:"Osée",Joel:"Joël",Amos:"Amos",Obad:"Abdias",
  Jonah:"Jonas",Mic:"Michée",Nah:"Nahum",Hab:"Habacuc",Zeph:"Sophonie",Hag:"Aggée",Zech:"Zacharie",
  Mal:"Malachie",Matt:"Matthieu",Mark:"Marc",Luke:"Luc",John:"Jean",Acts:"Actes",Rom:"Romains",
  "1Cor":"1 Corinthiens","2Cor":"2 Corinthiens",Gal:"Galates",Eph:"Éphésiens",Phil:"Philippiens",
  Col:"Colossiens","1Thess":"1 Thessaloniciens","2Thess":"2 Thessaloniciens","1Tim":"1 Timothée",
  "2Tim":"2 Timothée",Titus:"Tite",Phlm:"Philémon",Heb:"Hébreux",Jas:"Jacques","1Pet":"1 Pierre",
  "2Pet":"2 Pierre","1John":"1 Jean","2John":"2 Jean","3John":"3 Jean",Jude:"Jude",Rev:"Apocalypse",
};
