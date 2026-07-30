import { useEffect, useState } from "react";
import { loadCatalog } from "./lib/data.js";
import Home from "./pages/Home.jsx";
import Sermon from "./pages/Sermon.jsx";
import Browse from "./pages/Browse.jsx";

/**
 * Routing par hash — GitHub Pages sert des fichiers statiques : pas de réécriture serveur,
 * donc `#/sermon/sc-123` est la façon la plus robuste d'avoir des URLs partageables.
 * Routes : #/ · #/sermon/:id · #/livres · #/series · #/predicateurs
 */
function useHashRoute() {
  const [hash, setHash] = useState(() => window.location.hash.slice(1) || "/");
  useEffect(() => {
    const on = () => {
      setHash(window.location.hash.slice(1) || "/");
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return hash;
}

export default function App() {
  const route = useHashRoute();
  const [state, setState] = useState({ loading: true, sermons: [], error: null });

  useEffect(() => {
    loadCatalog()
      .then((sermons) => setState({ loading: false, sermons, error: null }))
      .catch((error) => setState({ loading: false, sermons: [], error }));
  }, []);

  const { loading, sermons, error } = state;

  return (
    <>
      <header className="site-header">
        <a className="brand" href="#/">
          <span className="brand-mark">EBN</span>
          <span>
            <strong>Sermothèque</strong>
            <small>Église Bonne Nouvelle · Poissy</small>
          </span>
        </a>
        <nav className="site-nav">
          <a href="#/livres">Livres</a>
          <a href="#/series">Séries</a>
          <a href="#/predicateurs">Prédicateurs</a>
        </nav>
      </header>

      <main className="site-main">
        {loading && <p className="state">Chargement du catalogue…</p>}
        {error && (
          <p className="state state-error">
            Impossible de charger le catalogue : {error.message}
          </p>
        )}
        {!loading && !error && <Route route={route} sermons={sermons} />}
      </main>

      <footer className="site-footer">
        <p>
          {sermons.length} prédications publiées · catalogue généré depuis le dépôt canonique.
          <br />
          <span className="muted">
            Prototype interne — les données proviennent de SoundCloud et YouTube de l'église.
          </span>
        </p>
      </footer>
    </>
  );
}

function Route({ route, sermons }) {
  const sermonMatch = route.match(/^\/sermon\/(.+)$/);
  if (sermonMatch) {
    const sermon = sermons.find((s) => s.id === decodeURIComponent(sermonMatch[1]));
    return sermon ? (
      <Sermon sermon={sermon} all={sermons} />
    ) : (
      <p className="state">
        Prédication introuvable. <a href="#/">Retour au catalogue</a>
      </p>
    );
  }
  if (route === "/livres") return <Browse sermons={sermons} mode="book" />;
  if (route === "/series") return <Browse sermons={sermons} mode="series" />;
  if (route === "/predicateurs") return <Browse sermons={sermons} mode="speaker" />;
  return <Home sermons={sermons} />;
}
