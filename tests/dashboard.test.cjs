// Run with: node --test tests/dashboard.test.cjs (no extra packages).
const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const vm = require('node:vm');
const html = readFileSync(new URL('../engine/dashboard.html', `file://${__filename}`), 'utf8');

function dashboard() {
  const elements = new Map();
  function element() {
    return {disabled: false, value: '', textContent: '', innerHTML: '', attrs: {},
      setAttribute(k, v) {this.attrs[k] = v;}, classList: {contains: () => false},
      append() {}, scrollIntoView() {}, requestSubmit() {this.onsubmit({preventDefault() {}});}};
  }
  const document = {querySelector(selector) {
    if (!elements.has(selector)) elements.set(selector, element());
    return elements.get(selector);
  }, querySelectorAll() {return [];}, createElement: element};
  const calls = [];
  const context = vm.createContext({document, Date, setInterval() {},
    EventSource: class {}, confirm: () => true,
    fetch(path, body) {calls.push({path, body}); return new Promise(() => {});}});
  vm.runInContext(html.match(/<script>([\s\S]*)<\/script>/)[1], context);
  return {context, calls, get: document.querySelector, run: (code) => vm.runInContext(code, context)};
}

test('locks immediately before HTTP completes; blocks duplicate send, Enter, and team', () => {
  const d = dashboard();
  d.get('#input').value = 'first';
  d.get('#composer').onsubmit({preventDefault() {}});
  assert.equal(d.get('#btn-send').disabled, true);
  assert.equal(d.get('#btn-team').disabled, true);
  assert.equal(d.get('#btn-stop').disabled, false);
  assert.equal(d.get('#composer').attrs['aria-busy'], 'true');
  d.run('send("duplicate")');
  d.get('#input').onkeydown({key: 'Enter', preventDefault() {}});
  d.get('#btn-team').onclick();
  assert.equal(d.calls.filter((c) => ['/api/chat', '/api/team'].includes(c.path)).length, 1);
  assert.equal(d.get('#input').disabled, false); // composing a draft is still possible
  d.run('onEvent({event_type:"run.end"})');
  assert.equal(d.get('#btn-send').disabled, false);
  assert.equal(d.get('#btn-team').disabled, false);
  assert.equal(d.get('#btn-stop').disabled, true);
});

test('team request also locks ordinary messages until run ends', () => {
  const d = dashboard();
  d.get('#input').value = 'exhibit';
  d.get('#btn-team').onclick();
  d.run('send("duplicate")');
  assert.equal(d.calls.filter((c) => c.path === '/api/team').length, 1);
  assert.equal(d.calls.filter((c) => c.path === '/api/chat').length, 0);
});

test('destination choices include custom plan folders and preserve the proposed filename', () => {
  const d = dashboard();
  const options = d.run(`destinationOptions([
    {src:'a.png', dst:'이미지/a.png'},
    {src:'b.png', dst:'커스텀/자료/b.png'}
  ], {src:'a.png', dst:'이미지/a.png'})`);
  assert.ok(options.includes('value="커스텀/자료/a.png"'));
  assert.ok(options.includes('value="레퍼런스/a.png"'));
  assert.ok(options.includes('value="이미지/a.png" selected'));
  assert.ok(options.includes('value="a.png"'));
  assert.equal((options.match(/value="이미지\/a.png"/g) || []).length, 1);
  assert.equal(html.includes('prompt("새 위치'), false);
});

test('destination labels and values escape filenames supplied by the model', () => {
  const d = dashboard();
  const options = d.run(`destinationOptions([], {src:'x', dst:'<folder>/a"<.png'})`);
  assert.ok(options.includes('&lt;'));
  assert.ok(options.includes('&quot;'));
  assert.equal(options.includes('value="<'), false);
});

test('sample selection offers direct use without copy checkboxes', async () => {
  const d = dashboard();
  d.get('input[name=kind]:checked').value = 'sample';
  d.run(`api = async () => ({source:'/kit/sample_downloads', items:[{name:'sample.txt', kb:1, skip:''}]})`);
  await d.run('loadFolder()');
  assert.equal(d.get('#folder-go').textContent, '이 폴더 사용');
  assert.ok(d.get('#folder-list').innerHTML.includes('/kit/sample_downloads'));
  assert.equal(d.get('#folder-list').innerHTML.includes('checkbox'), false);
  assert.equal(d.get('#folder-count').textContent, '');
  d.get('input[name=kind]:checked').value = 'downloads';
  await d.run('loadFolder()');
  assert.equal(d.get('#folder-go').textContent, '사본 만들기');
  assert.ok(d.get('#folder-list').innerHTML.includes('checkbox'));
});
