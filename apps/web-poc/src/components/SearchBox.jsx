import { fold } from "../lib/data.js";

/**
 * Champ de recherche partagé — partout où l'écran présente une liste.
 *
 * Le pliage (`fold`) est le même que celui du catalogue : on cherche « ezechiel » et on
 * trouve « Ézéchiel », sans que le visiteur ait à taper les accents. Un seul composant
 * pour que le geste soit identique d'une page à l'autre.
 */
export default function SearchBox({ value, onChange, placeholder, label, count }) {
  return (
    <div className="searchbox">
      <input
        className="search"
        type="search"
        value={value}
        placeholder={placeholder}
        aria-label={label || placeholder}
        onChange={(e) => onChange(e.target.value)}
      />
      {value && count != null && (
        <p className="results-count">
          {count === 0 ? "Aucun résultat" : `${count} résultat${count > 1 ? "s" : ""}`}
        </p>
      )}
    </div>
  );
}

/** Filtre une liste sur un ou plusieurs champs textuels, sans accents ni casse. */
export function matches(query, ...fields) {
  const q = fold(query).trim();
  if (!q) return true;
  return fold(fields.filter(Boolean).join(" ")).includes(q);
}
