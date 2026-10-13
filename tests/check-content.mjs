import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const context = vm.createContext({});
vm.runInContext(fs.readFileSync('lessons.js','utf8')+';globalThis.data={lessons,sources};', context);
const {lessons,sources}=context.data;
assert.equal(lessons.length,30,'all 30 lessons must be available');
assert.equal(new Set(lessons.map(l=>l.id)).size,30,'duplicate IDs break saved links');
for(let id=1;id<=30;id++) assert(lessons.some(l=>l.id===id),`missing ID ${id}`);
const distribution=[0,0,0];
for(const l of lessons){
 assert(l.deep.length>=3,`lesson ${l.id}: mechanism, worked case and limits`);
 assert.equal(l.exercises.length,3,`lesson ${l.id}: three exercises`);
 assert.deepEqual(Array.from(l.exercises,e=>e.kind),['概念','计算 / 应用','解释']);
 for(const e of l.exercises) assert(e.prompt && e.solution);
 assert(l.readingMinutes>0 && l.practiceMinutes>0);
 for(const id of l.prerequisites) assert(id!==l.id && lessons.some(x=>x.id===id));
 for(const k of l.sources) assert(sources[k] && /^https:\/\//.test(sources[k][1]));
 assert(l.sourceGuide.length>20);
 assert(l.quiz.correct>=0 && l.quiz.correct<3);distribution[l.quiz.correct]++;
 for(const file of l.downloads||[]) assert(fs.existsSync(file.path),file.path);
}
assert.deepEqual(distribution,[10,10,10]);
console.log('30 IDs, prerequisite/source/asset references, 90 exercises and balanced quizzes: PASS');
const visiting=new Set(),visited=new Set();
function checkPrerequisites(lesson){
 assert(!visiting.has(lesson.id),`prerequisite cycle at ${lesson.id}`);
 if(visited.has(lesson.id))return;
 visiting.add(lesson.id);
 for(const id of lesson.prerequisites){
  const required=lessons.find(l=>l.id===id);
  assert(lessons.indexOf(required)<lessons.indexOf(lesson),`lesson ${id} must precede ${lesson.id}`);
  checkPrerequisites(required);
 }
 visiting.delete(lesson.id);visited.add(lesson.id);
}
lessons.forEach(checkPrerequisites);
console.log('Prerequisites are acyclic and precede each lesson in the reading route: PASS');
