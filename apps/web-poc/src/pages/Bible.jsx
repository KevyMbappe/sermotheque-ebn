import { useEffect, useMemo, useRef, useState } from 'react';
import { BOOK_FR, BOOK_ORDER } from '../lib/books.js';
import { biblePath, matchSermons, parseInput, parseOsis, referenceLabel, validReference, overlaps } from '../lib/bible.js';
import { BASE, href, navigate, replaceQuery } from '../lib/router.js';
import ShareAt from '../components/ShareAt.jsx';
import BiblePicker from '../components/BiblePicker.jsx';

const cache = new Map();
function load(path) {
  if (!cache.has(path)) cache.set(path, fetch(`${BASE}data/bible/${path}`).then(r => {
    if (!r.ok) throw Error('Chargement impossible. Réessayez.');
    return r.json();
  }).catch(e => {cache.delete(path); throw e;}));
  return cache.get(path);
}

export default function Bible({book = 'Gen', chapter = 1, search, sermons, catalogError}) {
  const [manifest, setManifest] = useState(null), [error, setError] = useState(null), [attempt, retry] = useState(0);
  useEffect(() => { let active = true; setError(null); load('manifest.json').then(m => {if(active) setManifest(m);}).catch(e => {if(active)setError(e.message);}); return () => {active=false;}; }, [attempt]);
  if (error) return <p role="alert">{error} <button onClick={() => retry(n=>n+1)}>Réessayer</button></p>;
  if (!manifest) return <p className="state">Chargement de la Bible…</p>;
  if (!manifest.books[book]?.[chapter-1]) return <p className="state">Ce chapitre n’existe pas. <a href={href('/bible/')}>Ouvrir la Bible</a></p>;
  return <Reader key={`${book}.${chapter}`} {...{manifest,book,chapter,search,sermons,catalogError}} />;
}

function Reader({manifest, book, chapter, search, sermons, catalogError}) {
  const [data, setData] = useState(null), [error, setError] = useState(null), [attempt, retry] = useState(0);
  const [query, setQuery] = useState(''), [queryError, setQueryError] = useState('');
  const [rangeMode,setRangeMode] = useState(false), anchor = useRef(null), sheet = useRef(null), keepScroll = useRef(false);
  const raw = new URLSearchParams(search).get('ref');
  const parsed = parseOsis(raw);
  const valid = validReference(parsed,manifest) && parsed.start.book === book && overlaps(parsed,parseOsis(`${book}.${chapter}`),manifest);
  const selected = raw && valid ? raw : `${book}.${chapter}`;
  const selection = parseOsis(selected);
  const path = biblePath(`${book}.${chapter}`).split('?')[0] + `?ref=${encodeURIComponent(selected)}`;
  const count = manifest.books[book][chapter-1];
  const results = useMemo(() => data ? matchSermons(data.entries,selected,manifest) : [], [data,selected,manifest]);
  const byId = useMemo(() => new Map(sermons.map(s=>[s.id,s])),[sermons]);
  const visible = results.filter(r=>byId.has(r.id));
  const verseCounts = useMemo(() => data ? Array.from({length:count},(_,i)=>matchSermons(data.entries,`${book}.${chapter}.${i+1}`,manifest).filter(r=>r.group==='preached'||r.group==='cited').length) : [], [data,book,chapter,count,manifest]);

  useEffect(() => {
    let active=true; setError(null);
    Promise.all([load(`${book}/${chapter}.json`),load(`${book}/sermons.json`)]).then(([document,entries])=>{if(active)setData({...document,entries});}).catch(e=>{if(active)setError(e.message);});
    return ()=>{active=false;};
  },[book,chapter,attempt]);
  useEffect(() => {
    if (keepScroll.current) {keepScroll.current=false; return;}
    if(data && selection.start.verse) document.getElementById(`verse-${Math.max(1, selection.start.chapter === chapter ? selection.start.verse : 1)}`)?.scrollIntoView({block:'center'});
    // Shared/typed references scroll into view; tapping a verse preserves reading position.
  },[data,selected]);
  useEffect(() => {document.title = `${referenceLabel(selected)} · LSG 1910 — Sermothèque EBN`;},[selected]);

  function selectVerse(n, extend) {
    const start = (extend || rangeMode) && anchor.current ? Math.min(anchor.current,n) : n;
    const end = (extend || rangeMode) && anchor.current ? Math.max(anchor.current,n) : n;
    const id = `${book}.${chapter}.${start}` + (end !== start ? `-${book}.${chapter}.${end}` : '');
    if (!((extend || rangeMode) && anchor.current)) anchor.current=n;
    else anchor.current=null;
    keepScroll.current=id!==selected;
    replaceQuery(`?ref=${encodeURIComponent(id)}`);
  }
  function submit(e) {
    e.preventDefault(); const ref = parseInput(query,manifest);
    if (!ref) {setQueryError('Référence introuvable. Exemple : Jean 3:16–18.'); return;}
    setQueryError(''); navigate(biblePath(ref));
  }
  const index = BOOK_ORDER.indexOf(book);
  const previous = chapter > 1 ? `${book}.${chapter-1}` : index > 0 ? `${BOOK_ORDER[index-1]}.${manifest.books[BOOK_ORDER[index-1]].length}` : null;
  const next = chapter < manifest.books[book].length ? `${book}.${chapter+1}` : index < BOOK_ORDER.length-1 ? `${BOOK_ORDER[index+1]}.1` : null;
  const panel = <>
    <p className="bible-eyebrow">Prédications associées</p>
    <h2>{referenceLabel(selected)}</h2>
    {catalogError && <p role="alert">Le catalogue est indisponible. La lecture biblique reste accessible.</p>}
    <p className="muted">Les liens reposent sur les références du catalogue. Une citation ne signifie pas que le sermon expose tout le passage.</p>
    {!visible.length && <p className="bible-empty">Aucune prédication associée dans le catalogue disponible.</p>}
    {Object.entries({preached:'Prédications sur ce passage',cited:'Passage cité',chapter:'Sur ce chapitre — versets non précisés',book:'Sur ce livre — chapitre non précisé'}).map(([group,label]) => {
      const rows = visible.filter(r=>r.group===group);
      return rows.length ? <section className="bible-matches" key={group}><h3>{label} <span>({rows.length})</span></h3><ul>{rows.map(r=>{
        const s=byId.get(r.id);
        return <li key={r.id}><a href={href(`/sermon/${encodeURIComponent(s.id)}/?bible=${encodeURIComponent(selected)}`)} onClick={()=>sheet.current?.close()}>{s.title}</a><small>{referenceLabel(r.reference)} · {r.relation==='preached'?'Texte principal':'Référence citée'}</small>{s.speaker && <small>{s.speaker}{s.speaker_provenance==='default-rule'?' (à confirmer)':''}</small>}</li>;
      })}</ul></section> : null;
    })}
  </>;
  return <article className="bible-reader">
    <header className="bible-head"><p className="bible-eyebrow">Lire · retrouver · écouter</p><h1>La Bible</h1><p>Louis Segond 1910 <span className="muted">· Avec les prédications de l’Église Bonne Nouvelle</span></p></header>
    <form className="bible-reference" onSubmit={submit}><label className="sr-only" htmlFor="bible-reference">Aller à une référence</label><input id="bible-reference" className="search" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Jean 3:16–18" aria-describedby={queryError?'reference-error':undefined}/><button className="ghost" type="submit">Ouvrir</button></form>
    {queryError && <p id="reference-error" role="alert">{queryError}</p>}
    <div className="bible-controls"><BiblePicker manifest={manifest} book={book} chapter={chapter} /><ShareAt key={path} path={path} seconds={null} title={`${referenceLabel(selected)} · LSG 1910`} label="Partager le passage" /></div>
    {raw && !valid && <p role="alert">La sélection demandée est invalide. Le chapitre complet est affiché.</p>}
    {error && <p role="alert">{error} <button onClick={()=>retry(n=>n+1)}>Réessayer</button></p>}
    {!data && !error && <p className="state">Chargement du chapitre…</p>}
    {data && <div className="bible-layout"><section className="bible-text" aria-label={`${BOOK_FR[book]} ${chapter}`}>
      <div className="bible-chapter-head"><h2>{BOOK_FR[book]} {chapter}</h2><p className="muted">Sélectionnez un numéro de verset pour retrouver les prédications associées.</p><label className="bible-range"><input type="checkbox" checked={rangeMode} onChange={e=>{setRangeMode(e.target.checked);anchor.current=null;}}/> Sélectionner une plage (premier puis dernier verset)</label>{selection.precision==='verse' && <button className="ghost small" onClick={()=>{anchor.current=null;keepScroll.current=true;replaceQuery('');}}>Tout le chapitre</button>}</div>
      <ChapterDocument blocks={data.blocks} {...{book,chapter,selection,manifest,verseCounts,selectVerse}} />
      <nav className="bible-chapter-nav" aria-label="Parcourir les chapitres">{previous?<a href={href(biblePath(previous))}>← {referenceLabel(previous)}</a>:<span/>}{next && <a href={href(biblePath(next))}>{referenceLabel(next)} →</a>}</nav>
      <p className="muted bible-attribution">Louis Segond 1910 · Domaine public. Texte : <a href="https://ebible.org/fraLSG/" target="_blank" rel="noreferrer">eBible.org</a>. Numérotation conservée ; titres et texte rouge sont des repères éditoriaux de cette édition.</p>
    </section><aside className="bible-sidebar" aria-label="Prédications associées">{panel}</aside></div>}
    {data && <button className="bible-mobile-results" onClick={()=>sheet.current.showModal()}>{referenceLabel(selected)} · {visible.length} prédication{visible.length!==1?'s':''}</button>}
    <dialog className="bible-sheet" ref={sheet} aria-label="Prédications associées"><button className="ghost bible-sheet-close" onClick={()=>sheet.current.close()}>Fermer ×</button>{panel}</dialog>
  </article>;
}

function ChapterDocument({blocks,book,chapter,selection,manifest,verseCounts,selectVerse}) {
  const seen = new Set();
  const run = (item, key) => {
    const n = item.verse;
    const first = !seen.has(n); seen.add(n);
    const selected = selection.precision === 'verse' && overlaps(parseOsis(`${book}.${chapter}.${n}`),selection,manifest);
    return <span id={first ? `verse-${n}` : undefined} className={`bible-run${selected?' is-selected':''}`} key={key}>
      {first && <button className="verse-number" aria-pressed={selected} aria-label={`Verset ${n}${verseCounts[n-1] ? `, ${verseCounts[n-1]} prédications associées` : ''}`} onClick={e=>selectVerse(n,e.shiftKey)}>{n}{verseCounts[n-1]>0 && <span className="verse-dot" aria-hidden="true">•</span>}</button>}
      {item.segments.map((segment,i)=><span className={segment.red?'words-of-jesus':undefined} key={i}>{segment.text}{' '}</span>)}
    </span>;
  };
  return <div className="bible-document">
    {blocks.map((block,i) => {
      if (block.type === 'heading') return block.level === 1 ? <h3 className="bible-section major" key={i}>{block.text}</h3> : <h3 className="bible-section" key={i}>{block.text}</h3>;
      if (block.type === 'break') return <div className="bible-break" aria-hidden="true" key={i} />;
      if (block.type === 'poetry') return <div className={`bible-poetry level-${block.level}`} key={i}>{block.content.map((item,j)=><div className="bible-poetry-line" key={j}>{run(item,`${i}-${j}`)}</div>)}</div>;
      return <p className={`bible-paragraph level-${block.level}`} key={i}>{block.content.map((item,j)=>run(item,`${i}-${j}`))}</p>;
    })}
  </div>;
}
