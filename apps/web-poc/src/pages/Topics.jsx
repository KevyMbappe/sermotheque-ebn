import { useEffect, useState } from "react";
import SermonCard from "../components/SermonCard.jsx";
import { loadTopics } from "../lib/data.js";
import { href } from "../lib/router.js";
import SearchBox, { matches } from "../components/SearchBox.jsx";

/**
 * Navigation par thème — impossible jusqu'ici. L'enrichissement produit des étiquettes
 * libres : 1 086 occurrences pour 594 formes distinctes, dont 451 vues une seule fois.
 * Une telle liste n'a pas de fond, on ne peut pas naviguer dedans. Le vocabulaire curé
 * (#57, 44 catégories) lui donne une ossature ; `topics` reste affiché tel quel sur la
 * fiche, parce que sa richesse dit quelque chose du message.
 */
export function TopicsIndex({ sermons }) {
  const [vocab, setVocab] = useState([]);
  useEffect(() => { loadTopics().then(setVocab); }, []);

  const counts = new Map();
  for (const s of sermons) {
    for (const t of s.topics_canonical || []) counts.set(t, (counts.get(t) || 0) + 1);
  }
  const [q, setQ] = useState("");
  const all = vocab.filter((v) => counts.get(v.id));
  const used = all.filter((v) => matches(q, v.label));

  return (
    <>
      <h1 className="page-title">Parcourir par thème</h1>
      <p className="results-count">
        <strong>{all.length}</strong> thèmes — vocabulaire curé, pour que deux sermons sur la
        même doctrine se retrouvent au même endroit.
      </p>
      <SearchBox value={q} onChange={setQ} placeholder="Chercher un thème…"
                 label="Chercher un thème" count={used.length} />
      <ul className="book-grid">
        {used.map((v) => (
          <li key={v.id}>
            <a className="book-tile" href={href(`/themes/${v.id}/`)}>
              <span className="book-name">{v.label}</span>
              <span className="book-counts">
                <span className="count-preached">
                  {counts.get(v.id)} sermon{counts.get(v.id) > 1 ? "s" : ""}
                </span>
              </span>
            </a>
          </li>
        ))}
      </ul>
    </>
  );
}

export function TopicPage({ sermons, topic }) {
  const [vocab, setVocab] = useState([]);
  useEffect(() => { loadTopics().then(setVocab); }, []);

  const [q, setQ] = useState("");
  const entry = vocab.find((v) => v.id === topic);
  const all = sermons
    .filter((s) => (s.topics_canonical || []).includes(topic))
    .sort((a, b) => (b.date || "").localeCompare(a.date || ""));
  const items = all.filter((s) => matches(q, s.title, s.description, s.speaker, s.scripture_display));

  return (
    <>
      <a className="back" href={href("/themes")}>← Tous les thèmes</a>
      <h1 className="page-title">{entry ? entry.label : topic}</h1>
      <p className="results-count">
        {all.length} sermon{all.length > 1 ? "s" : ""}
      </p>
      {all.length > 4 && (
        <SearchBox value={q} onChange={setQ} placeholder="Chercher dans ces sermons…"
                   label="Chercher dans ces sermons" count={items.length} />
      )}
      {items.length > 0 ? (
        <div className="grid">
          {items.map((s) => <SermonCard key={s.id} sermon={s} />)}
        </div>
      ) : (
        <p className="state">
          Aucun sermon publié sur ce thème pour l'instant. Il se remplira au fil des
          prochains enrichissements.
        </p>
      )}
    </>
  );
}
