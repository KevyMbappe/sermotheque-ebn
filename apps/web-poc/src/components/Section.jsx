import { useState } from "react";

/**
 * Bloc repliable.
 *
 * Retour d'usage sur la fiche sermon : « trop de blocs texte », « ça fait peur ». La page
 * affichait tout ce que l'enrichissement avait produit — résumé, points clés, citations,
 * questions, passages, thèmes, références — empilé sans hiérarchie. C'est un inventaire,
 * pas une lecture.
 *
 * On garde donc tout (le contenu a de la valeur, et il est le produit du pipeline) mais
 * replié : chaque bloc annonce ce qu'il contient et combien, et s'ouvre d'un clic.
 *
 * Un <details>/<summary> natif ferait presque l'affaire, mais on veut le compteur, une
 * flèche cohérente et surtout que le bloc reste OUVERT à l'impression (la fiche de groupe
 * de maison doit tout montrer). D'où ce petit composant plutôt qu'un élément natif.
 */
export default function Section({ title, count, children, defaultOpen = false, className = "" }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section className={`panel section ${open ? "is-open" : "is-closed"} ${className}`}>
      <h2>
        <button
          className="section-toggle"
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
        >
          <span className="section-caret" aria-hidden="true">{open ? "▾" : "▸"}</span>
          <span className="section-title">{title}</span>
          {count != null && <span className="section-count">{count}</span>}
        </button>
      </h2>
      {/* Rendu même fermé : l'impression les rouvre tous (voir styles.css @media print),
          et le contenu reste dans le DOM pour la recherche du navigateur (Ctrl+F). */}
      <div className="section-body">{children}</div>
    </section>
  );
}
