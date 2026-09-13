import { useEffect, useRef, useState } from 'react';
import { BOOK_FR, BOOK_ORDER } from '../lib/books.js';
import { biblePath } from '../lib/bible.js';
import { href } from '../lib/router.js';

export default function BiblePicker({manifest,book,chapter}) {
  const dialog = useRef(null);
  const [chosenBook,setChosenBook] = useState(book);
  const [chosenChapter,setChosenChapter] = useState(chapter);
  useEffect(()=>{setChosenBook(book);setChosenChapter(chapter);},[book,chapter]);
  const close = () => dialog.current?.close();
  return <>
    <button className="bible-picker-trigger" onClick={()=>dialog.current?.showModal()} aria-haspopup="dialog">
      <span>{BOOK_FR[book]}</span><strong>{chapter}</strong><span aria-hidden="true">⌄</span>
    </button>
    <dialog className="bible-picker" ref={dialog} aria-labelledby="bible-picker-title" onClick={e=>{if(e.target===dialog.current)close();}}>
      <header><div><p className="bible-eyebrow">Aller à</p><h2 id="bible-picker-title">Choisir un passage</h2></div><button className="ghost" onClick={close} aria-label="Fermer">×</button></header>
      <div className="bible-picker-current">{BOOK_FR[chosenBook]} {chosenChapter}</div>
      <div className="bible-picker-columns">
        <section aria-label="Livres"><h3>Livre</h3><div className="bible-picker-list">
          {BOOK_ORDER.map((b,i)=><button key={b} className={b===chosenBook?'active':''} aria-pressed={b===chosenBook} onClick={()=>{setChosenBook(b);setChosenChapter(1);}}><small>{i<39?'AT':'NT'}</small>{BOOK_FR[b]}</button>)}
        </div></section>
        <section aria-label="Chapitres"><h3>Chapitre</h3><div className="bible-picker-grid">
          {manifest.books[chosenBook].map((_,i)=><button key={i} className={i+1===chosenChapter?'active':''} aria-pressed={i+1===chosenChapter} onClick={()=>setChosenChapter(i+1)}>{i+1}</button>)}
        </div></section>
        <section aria-label="Versets"><h3>Verset</h3><div className="bible-picker-grid">
          {Array.from({length:manifest.books[chosenBook][chosenChapter-1]},(_,i)=><a key={i} href={href(biblePath(`${chosenBook}.${chosenChapter}.${i+1}`))} onClick={close}>{i+1}</a>)}
        </div><a className="bible-picker-chapter" href={href(biblePath(`${chosenBook}.${chosenChapter}`))} onClick={close}>Lire tout le chapitre</a></section>
      </div>
    </dialog>
  </>;
}
