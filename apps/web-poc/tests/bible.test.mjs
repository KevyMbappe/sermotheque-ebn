import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {parseOsis, validReference, referenceLabel, parseInput, matchSermons, buildBibleIndex, biblePath} from '../src/lib/bible.js';
const read=name=>JSON.parse(readFileSync(new URL(`../../../data/bible/lsg/${name}.json`,import.meta.url)));
const manifest=read('manifest');
const entry=(id,reference,relation='preached')=>({id,reference,relation});
test('verse boundaries and precision: no whole-chapter false positives',()=>{
 const rows=[entry('exact','Rom.8.28-Rom.8.30'),entry('other','Rom.8.29'),entry('chapter','Rom.8'),entry('book','Rom'),entry('citation','Rom.8.28','cited')];
 assert.deepEqual(matchSermons(rows,'Rom.8.28',manifest).map(r=>[r.id,r.group]),[['exact','preached'],['citation','cited'],['chapter','chapter'],['book','book']]);
 assert.equal(matchSermons([rows[0]],'Rom.8.31',manifest).length,0);
 assert.equal(matchSermons([rows[0]],'Rom.8.30',manifest).length,1);
});
test('cross-chapter ranges respect both endpoints',()=>{
 const rows=[entry('span','John.3.35-John.4.3')];
 for(const [ref,count] of [['John.3.34',0],['John.3.35',1],['John.3.36',1],['John.4.1',1],['John.4.3',1],['John.4.4',0]]) assert.equal(matchSermons(rows,ref,manifest).length,count,ref);
});
test('deduplicate sermons; exact citation beats broad primary passage',()=>{
 const rows=[entry('a','Rom.8'),entry('a','Rom.8.28','cited'),entry('a','Rom.8.28','cited')];
 assert.deepEqual(matchSermons(rows,'Rom.8.28',manifest).map(r=>r.group),['cited']);
 rows.push(entry('a','Rom.8.28'));assert.equal(matchSermons(rows,'Rom.8.28',manifest)[0].group,'preached');
});
test('reject malformed, reversed, out-of-range and cross-book references',()=>{
 for(const value of ['John.0','John.3.0','John.3.99','John.22','John.4.3-John.3.9','John.3.18-John.3.16','John.3.1-Acts.1.1','John.3-nope','Unknown.1','John.3.1.extra','John.3.1-John.3.2-junk']) assert.equal(validReference(parseOsis(value),manifest),false,value);
 assert.equal(validReference(parseOsis('Ps.119.176'),manifest),true);
});
test('French input, accents, numbered books, verse/chapter ranges and single-chapter books',()=>{
 for(const [input,expected] of [['Jean 3:16–18','John.3.16-John.3.18'],['Jean 3:35-4:3','John.3.35-John.4.3'],['Genese 1-3','Gen.1-Gen.3'],['1 Jean 2:1','1John.2.1'],['Jude 24-25','Jude.1.24-Jude.1.25'],['Jean 3:99',null],['Jean 3:18-16',null]]) assert.equal(parseInput(input,manifest),expected);
 assert.equal(referenceLabel('John.3.16-John.3.18'),'Jean 3:16–18');
 assert.equal(referenceLabel('John.3.35-John.4.3'),'Jean 3:35–4:3');
 assert.equal(biblePath('John.3.16'),'/bible/John/3/?ref=John.3.16');
});
test('invalid catalogue references are excluded and reported',()=>{
 const {index,issues}=buildBibleIndex([{id:'a',scripture_osis:'John.3.99',scripture_refs_osis:['John.3.16']}],manifest);
 assert.equal(issues.length,1);assert.equal(index.John.length,1);assert.equal(index.John[0].relation,'cited');
});
test('complete pinned text, contiguous chapters/verses, no leaked annotations',()=>{
 let chapters=0,verses=0;assert.equal(Object.keys(manifest.books).length,66);
 for(const [book,counts] of Object.entries(manifest.books)) {
  const data=read(book);assert.equal(Object.keys(data).length,counts.length);
  counts.forEach((count,i)=>{assert.equal(Object.keys(data[i+1]).length,count);
   for(let v=1;v<=count;v++){assert.ok(data[i+1][v]?.trim());assert.doesNotMatch(data[i+1][v],/\\|strong=|INTRODUCTION/);}
   chapters++;verses+=count;
  });
 }
 assert.equal(chapters,1189);assert.equal(verses,31170);
 assert.match(read('John')['3']['16'],/^Car Dieu a tant aimé le monde/);
});
