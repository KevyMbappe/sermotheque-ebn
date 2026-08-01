import { useEffect, useState } from "react";
import { loadCatalog } from "./lib/data.js";
import { currentPath, href, startRouter, subscribe } from "./lib/router.js";
import Home from "./pages/Home.jsx";
import Sermon from "./pages/Sermon.jsx";
import Browse from "./pages/Browse.jsx";

/**
 * Routage par chemin — voir lib/router.js pour le pourquoi (partage et aperçus de lien).
 * Routes : / · /sermon/:id · /livres · /series · /predicateurs
 */
function useRoute() {
  const [path, setPath] = useState(currentPath);
  useEffect(() => {
    startRouter();
    return subscribe(() => setPath(currentPath()));
  }, []);
  return path;
}

export default function App() {
  const route = useRoute();
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
        <a className="brand" href={href("/")}>
          <span className="brand-mark">EBN</span>
          <span>
            <strong>Sermothèque</strong>
            <small>Église Bonne Nouvelle · Poissy</small>
          </span>
        </a>
        <nav className="site-nav">
          <a href={href("/livres")}>Livres</a>
          <a href={href("/series")}>Séries</a>
          <a href={href("/predicateurs")}>Prédicateurs</a>
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
        Prédication introuvable. <a href={href("/")}>Retour au catalogue</a>
      </p>
    );
  }
  if (route === "/livres") return <Browse sermons={sermons} mode="book" />;
  if (route === "/series") return <Browse sermons={sermons} mode="series" />;
  if (route === "/predicateurs") return <Browse sermons={sermons} mode="speaker" />;
  return <Home sermons={sermons} />;
}
