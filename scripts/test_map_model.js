// Read the actual viewer model without a browser or external packages.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, '..', 'viewer', 'map.html'), 'utf8');
const between = (start, end) => html.slice(html.indexOf(start), html.indexOf(end, html.indexOf(start)));
const context = vm.createContext({});
vm.runInContext(between('  function natural(', '  function el(') +
  between('  function buildModel(', '  // ------------------------------------------------------------------ layout') +
  '\nthis.model = buildModel;', context);
const graph = (parent, child, third) => ({ nodes: [
  { id: 'route:r', kind: 'route', matches: parent.length, principles: [] },
  { id: 'place:db', kind: 'place', path: 'db', is_dir: true },
  { id: 'place:db/migrations', kind: 'place', path: 'db/migrations', is_dir: true },
  ...(third ? [{ id: 'place:db/seeds', kind: 'place', path: 'db/seeds', is_dir: true }] : [])
], edges: [
  { kind: 'governs', from: 'route:r', to: 'place:db', matched_files: parent },
  { kind: 'governs', from: 'route:r', to: 'place:db/migrations', matched_files: child },
  ...(third ? [{ kind: 'governs', from: 'route:r', to: 'place:db/seeds', matched_files: third }] : [])
] });
const shown = (g) => Array.from(context.model(g).routePl.get('route:r'));
assert.deepEqual(shown(graph(['db/migrations/a.sql'], ['db/migrations/a.sql'])), ['place:db/migrations']);
assert.deepEqual(shown(graph(['db/a.sql', 'db/migrations/a.sql'], ['db/migrations/a.sql'])), ['place:db', 'place:db/migrations']);
assert.deepEqual(shown(graph(['db/migrations/a.sql', 'db/seeds/b.sql'], ['db/migrations/a.sql'], ['db/seeds/b.sql'])), ['place:db/migrations', 'place:db/seeds']);
assert.deepEqual(shown(graph(['db/a.sql'], ['db/migrations/b.sql'])), ['place:db', 'place:db/migrations'], 'Equal counts are not equal membership');
const old = graph(['db/migrations/a.sql'], ['db/migrations/a.sql']);
old.edges.forEach((e) => delete e.matched_files);
assert.deepEqual(shown(old), ['place:db', 'place:db/migrations'], 'Legacy snapshots retain all links');
const g = graph(['db/migrations/a.sql'], ['db/migrations/a.sql']);
assert.deepEqual(Array.from(context.model(g).plRoutes.get('place:db')), ['route:r'], 'Inspection preserves parent association');
const empty = {nodes: [{id:'route:empty',kind:'route',matches:0,principles:[]}],edges:[]};
assert.equal(context.model(empty).dead.has('route:empty'), true);
assert.deepEqual(shown(g), shown(g), 'Repeated builds are deterministic');
console.log('Map model: 8 membership, legacy and empty-route checks passed');
