import { readFileSync, writeFileSync, mkdirSync, rmSync } from 'node:fs';
import { join } from 'node:path';
import { BOOK_ORDER } from '../src/lib/books.js';
import { buildBibleIndex } from '../src/lib/bible.js';

export function buildBible(root, out, sermons) {
  const source = join(root, 'data/bible/lsg');
  const manifest = JSON.parse(readFileSync(join(source, 'manifest.json'), 'utf8'));
  if (JSON.stringify(Object.keys(manifest.books)) !== JSON.stringify(BOOK_ORDER)) throw Error('LSG canon mismatch');
  const dest = join(out, 'bible');
  rmSync(dest, {recursive:true, force:true});
  mkdirSync(dest, {recursive:true});
  const {index, issues} = buildBibleIndex(sermons, manifest);
  let verses = 0, chapters = 0;
  for (const book of BOOK_ORDER) {
    const data = JSON.parse(readFileSync(join(source, `${book}.json`), 'utf8'));
    const structure = JSON.parse(readFileSync(join(source, `${book}.structure.json`), 'utf8'));
    if (Object.keys(data).length !== manifest.books[book].length) throw Error(`Chapter count: ${book}`);
    mkdirSync(join(dest, book), {recursive:true});
    for (const [i,count] of manifest.books[book].entries()) {
      const chapter = i + 1, rows = data[chapter];
      if (!rows || Object.keys(rows).length !== count) throw Error(`Verse count: ${book}.${chapter}`);
      for (let n = 1; n <= count; n++) {
        if (typeof rows[n] !== 'string' || !rows[n].trim() || /\\|strong=/.test(rows[n])) throw Error(`Invalid text: ${book}.${chapter}.${n}`);
      }
      const blocks = structure[chapter];
      if (!Array.isArray(blocks) || !blocks.length) throw Error(`Reading structure: ${book}.${chapter}`);
      writeFileSync(join(dest,book,`${chapter}.json`), JSON.stringify({verses: rows, blocks}));
      chapters++; verses += count;
    }
    writeFileSync(join(dest,book,'sermons.json'), JSON.stringify(index[book] || []));
  }
  writeFileSync(join(dest,'manifest.json'), JSON.stringify(manifest));
  writeFileSync(join(dest,'reference-issues.json'), JSON.stringify(issues,null,2));
  console.log(`[bible] 66 books · ${chapters} chapters · ${verses} verses · ${issues.length} references excluded (see bible/reference-issues.json)`);
}
