/* gate: predict, then reveal. Keys 1-9 pick, ←/→ or A/D move, ⌘↩ locks in. Blocks with `after: id` wait for it.
   The verdict names the inputs it was for (`context`), because the inputs can change after the reveal. */
Rupaka.block('gate', (b, ctx) => {
  const {el, fmt, show} = Rupaka, s = ctx.s, id = b.id;
  s.st.gate[id] = 'open';
  let picked = null, said = '', seen = '';
  const opts = () => Array.isArray(b.options) ? b.options : (s.get(b.options.from) || []);
  const ans = () => b.answer && typeof b.answer === 'object' ? b.answer.is : s.get(b.answer);
  const done = () => s.get(`gate.${id}`) === 'done';
  const q = el('p', {class: 'q', id: `rk-${ctx.spec.id || 'd'}-${id}-q`});
  const box = el('div', {class: 'opts', role: 'radiogroup', 'aria-labelledby': q.id});
  const why = b.why ? el('textarea', {rows: 1, placeholder: b.why, 'aria-label': b.why}) : null;
  const go = el('button', {class: 'go', type: 'button', disabled: true}, 'Lock in', el('kbd', {text: '⌘↩'}));
  const again = el('button', {type: 'button', hidden: true}, 'Try another');
  const verdict = el('p', {class: 'verdict', 'aria-live': 'polite', hidden: true});
  const stale = el('span', {class: 'stale', hidden: true, text: ' The demo now shows other inputs.'});
  const pick = o => { if (done()) return; picked = o; paint(); };
  function paint() {
    const os = opts(), k = JSON.stringify(os);
    if (k !== seen) {
      seen = k;
      box.replaceChildren(...os.map((o, i) => el('button', {type: 'button', role: 'radio', onclick: () => pick(o)}, show(o), i < 9 ? el('kbd', {text: i + 1}) : null)));
    }
    [...box.children].forEach((x, i) => { x.setAttribute('aria-checked', String(os[i] === picked)); x.disabled = done(); x.tabIndex = os[i] === picked || (picked == null && i === 0) ? 0 : -1; });
    go.disabled = picked == null || done(); go.hidden = done(); again.hidden = !(done() && b.again); verdict.hidden = !done();
    stale.hidden = !done() || !b.context || fmt(b.context, s.st) === said;
  }
  function commit() {
    if (picked == null || done()) return false;
    const a = ans(), ok = String(picked) === String(a);
    said = b.context ? fmt(b.context, s.st) : '';
    verdict.replaceChildren(said ? `${said} ` : '', 'You said ', el('b', {class: ok ? 'ok' : 'no', text: show(picked)}), '. ',
      ok ? el('span', {class: 'ok', text: 'That is right.'}) : el('span', {}, 'It is ', el('b', {class: 'ok', text: show(a)}), '.'), stale);
    s.st.gate[id] = 'done';
    const detail = {gate: id, picked, ans: a, ok, why: why ? why.value : '', context: said};
    s.st.log = [...(s.st.log || []), detail];
    s.set('_', (s.st._ || 0) + 1);
    Rupaka.predict(ctx, detail);
    return true;
  }
  go.onclick = commit;
  again.onclick = () => { picked = null; said = ''; if (why) why.value = ''; s.st.gate[id] = 'open'; s.set('_', (s.st._ || 0) + 1); box.querySelector('button')?.focus(); };
  (ctx.gates ||= []).push({id, commit, done});
  ctx.commit ||= () => { const g = ctx.gates.find(g => !g.done()); return g ? g.commit() : false; };
  const root = el('div', {}, q, box, why, verdict, el('div', {class: 'acts'}, go, again));
  root.addEventListener('keydown', e => {
    if (e.target.tagName === 'TEXTAREA' || done() || e.metaKey || e.ctrlKey || e.altKey) return;
    const os = opts(), k = e.key.toLowerCase(), i = os.indexOf(picked);
    let j = /^[1-9]$/.test(k) ? +k - 1 : null;
    if (j == null && e.target.closest('.opts')) j = ['arrowright', 'arrowdown', 'd'].includes(k) ? i + 1 : ['arrowleft', 'arrowup', 'a'].includes(k) ? Math.max(0, i - 1) : null;
    if (j == null || j < 0 || j >= os.length) return;
    e.preventDefault(); pick(os[j]);
    if (e.target.closest('.opts')) box.children[j].focus();
  });
  s.on(() => {
    q.textContent = fmt(b.prompt, s.st);
    if (!Array.isArray(b.options) && !done() && !opts().some(o => o === picked)) picked = null;
    paint();
  });
  return root;
});
