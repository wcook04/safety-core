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

vm.runInContext(between('  const esc =', '  const clamp =') +
  between('  function skillsHTML(', '  function placeHTML(') +
  '\nthis.skillsHTML = skillsHTML; this.purposeHTML = purposeHTML;', context);
assert.equal(context.skillsHTML(undefined), '');
assert.match(context.purposeHTML({}), /not supplied/);
assert.match(context.purposeHTML({policy_source:'docs/layout.json', observation:'declared_only'}), /empty, ignored, or not yet created/);
assert.match(context.purposeHTML({policy_source:'docs/layout.json'}), /no new approval/);
const skillMarkup = context.skillsHTML([{path:'skills/notes/SKILL.md',when:'Writing notes',status:'present',text:'<script>bad()</script>'}]);
assert.match(skillMarkup, /&lt;script&gt;/);
assert.doesNotMatch(skillMarkup, /<script>/);
assert.match(skillMarkup, /do not run a workflow/);
console.log('Map purpose and skill rendering: legacy, discovery and escaping checks passed');

vm.runInContext(between('  function sessionModel(', '  // the label on a principle row') + '\nthis.sessionModel = sessionModel; this.stepList = stepList;', context);
const sample = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'docs', 'reference', 'agent-runs-20261018-trace-hook.json'), 'utf8'));
const sess = context.sessionModel(sample);
assert.equal(sess.steps.length, sample.steps.length);
assert.deepEqual(Array.from(sess.places.keys()).sort(), sample.touched.places.slice().sort(), 'Touched places come from step files');
assert.ok(sess.routes.has('route:tests') && sess.routes.get('route:tests').sent.length === 0, 'A read on an edit route sends no reminder');
assert.deepEqual(Array.from(sess.principles.get('P1'), (e) => e.decision), ['ask'], 'The retry check asked at its step');
assert.equal(sess.steps.find((st) => st.decisions.some((d) => d.decision === 'ask')).ran, false, 'No record that the asked command ran');
assert.equal(context.stepList([4, 6]), 'steps 4, 6');
console.log('Map session trace: places, routes, decisions and not-run checks passed on the recorded example');

// Exercise actual async discovery in each supported host, without a browser.
(async () => {
  async function probe(origin, protocol, available) {
    const requests = [];
    const state = {origin, session: null};
    const host = vm.createContext({S: state, location: {protocol},
      renderPanel() {}, renderTrace() {},
      async fetch(url, options) {
        assert.equal(options.method, 'HEAD');
        requests.push(url);
        return {ok: available.includes(url)};
      }});
    vm.runInContext(html.match(/  const EXAMPLE_TRACES =.*;/)[0] +
      between('  async function probeExample()', '  function traceOpenHTML()') +
      '\nthis.probeExample = probeExample;', host);
    await host.probeExample();
    return {requests, example: state.exampleUrl};
  }
  const endpoint = './example-trace.json';
  const old = '../docs/reference/agent-runs-20261018-trace-hook.json';
  const local = './docs/reference/agent-runs-20261018-trace-hook.json';
  assert.deepEqual(await probe('served', 'http:', [endpoint]), {requests: [endpoint], example: endpoint});
  assert.deepEqual(await probe('served', 'http:', []), {requests: [endpoint, old, local], example: undefined},
    'An adopted toolkit has no bundled example and retains trace-file upload');
  assert.deepEqual(await probe('served', 'http:', [local]), {requests: [endpoint, old, local], example: local},
    'Static hosting with a graph.json sidecar retains relative example discovery');
  assert.deepEqual(await probe('sample', 'http:', [local]), {requests: [old, local], example: local},
    'Static hosting retains relative recorded-example discovery');
  assert.deepEqual(await probe('embedded', 'file:', []), {requests: [], example: undefined},
    'Standalone maps do not probe HTTP-only resources');
  console.log('Map example discovery: native, adopted, static and standalone hosts passed');
})().catch((error) => { console.error(error); process.exitCode = 1; });
