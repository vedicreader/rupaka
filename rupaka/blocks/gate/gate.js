/* gate: predict, then reveal. Keys 1-9 pick, ←/→ or A/D move, ⌘↩ locks in. Blocks with `after: id` wait for it.
   The verdict names the inputs it was for (`context`), because the inputs can change after the reveal.
   A host that saves the prediction calls preventDefault on rk-predict. The gate then waits ('pending') until the host calls
   detail.settle(saved, message): true reveals, false opens the gate again and shows the message as text. Only the first call counts.
   Rupaka.settle(host, id, pick, {answer}) closes the gate from the host: no rk-predict, no log. A null pick reveals with no verdict.
   `answer` draws the verdict when the spec has none (a copy for a room has its answers taken out); it is never stored.
   With no answer at all, the gate reveals with no verdict. Rupaka.options(host, id) reads the options as opts() gives them.
   Rupaka.open(host, id) opens a closed gate again with reopen(), as Try another does, but it does not move the focus. */
Rupaka.block('gate', (b, ctx) => {
  const {el, fmt, show} = Rupaka, s = ctx.s, id = b.id;
  s.st.gate[id] = 'open';
  let picked = null, said = '', seen = '';
  const opts = () => Array.isArray(b.options) ? b.options : (s.get(b.options.from) || []);
  const ans = (a = b.answer) => a && typeof a === 'object' ? a.is : s.get(a);   // {is: value} or a path in the state
  const done = () => s.get(`gate.${id}`) === 'done', open = () => s.get(`gate.${id}`) === 'open';
  const q = el('p', {class: 'q', id: `rk-${ctx.spec.id || 'd'}-${id}-q`});
  const box = el('div', {class: 'opts', role: 'radiogroup', 'aria-labelledby': q.id});
  const why = b.why ? el('textarea', {rows: 1, placeholder: b.why, 'aria-label': b.why}) : null;
  const go = el('button', {class: 'go', type: 'button', disabled: true}, 'Lock in', el('kbd', {text: '⌘↩'}));
  const again = el('button', {type: 'button', hidden: true}, 'Try another');
  const verdict = el('p', {class: 'verdict', 'aria-live': 'polite', hidden: true});
  const stale = el('span', {class: 'stale', hidden: true, text: ' The demo now shows other inputs.'});
  const note = el('p', {class: 'note', 'aria-live': 'polite', hidden: true});
  const say = t => { note.textContent = t; note.hidden = !t; };
  const pick = o => { if (!open()) return; picked = o; paint(); };
  function paint() {
    const os = opts(), k = JSON.stringify(os);
    if (k !== seen) {
      seen = k;
      box.replaceChildren(...os.map((o, i) => el('button', {type: 'button', role: 'radio', onclick: () => pick(o)}, show(o), i < 9 ? el('kbd', {text: i + 1}) : null)));
    }
    [...box.children].forEach((x, i) => { x.setAttribute('aria-checked', String(os[i] === picked)); x.disabled = !open(); x.tabIndex = os[i] === picked || (picked == null && i === 0) ? 0 : -1; });
    go.disabled = picked == null || !open(); go.hidden = done(); again.hidden = !(done() && b.again); verdict.hidden = !done() || !verdict.childNodes.length;
    stale.hidden = !done() || !b.context || fmt(b.context, s.st) === said;
  }
  const tell = (c, ok, a) => {
    said = c; say('');
    verdict.replaceChildren(said ? `${said} ` : '', 'You said ', el('b', {class: ok ? 'ok' : 'no', text: show(picked)}), '. ',
      ok ? el('span', {class: 'ok', text: 'That is right.'}) : el('span', {}, 'It is ', el('b', {class: 'ok', text: show(a)}), '.'), stale);
  };
  function commit() {
    if (picked == null || !open()) return false;
    const a = ans(), ok = String(picked) === String(a), c = b.context ? fmt(b.context, s.st) : '';
    const detail = {gate: id, picked, ans: a, ok, why: why ? why.value : '', context: c};
    let settled = false;
    const settle = (saved, message = '') => {
      if (settled) return;
      settled = true;
      if (!saved) { s.st.gate[id] = 'open'; say(String(message ?? '')); paint(); return; }
      tell(c, ok, a);
      s.st.gate[id] = 'done';
      s.st.log = [...(s.st.log || []), detail];
      s.set('_', (s.st._ || 0) + 1);
    };
    s.st.gate[id] = 'pending'; say(''); paint();
    if (Rupaka.predict(ctx, {...detail, settle})) settle(true);
    else if (!settled) say('Saving your prediction.');
    return true;
  }
  go.onclick = commit;
  // Open a closed gate again: no pick, no reason, no verdict. One draw hides the blocks that wait for the gate. An open gate does not change.
  const reopen = () => {
    if (!done()) return;
    picked = null; said = ''; if (why) why.value = ''; verdict.replaceChildren();
    s.st.gate[id] = 'open'; s.set('_', (s.st._ || 0) + 1);
  };
  again.onclick = () => { reopen(); box.querySelector('button')?.focus(); };   // only the learner's button moves the focus
  // The host closes the gate. The caller (Rupaka.settle) draws once after it. The answer of the spec comes first.
  const settle = (p, answer) => {
    const w = b.answer ?? answer;
    if (p != null) picked = p;
    if (p == null || w == null) { said = ''; say(''); verdict.replaceChildren(); }
    else { const a = ans(w); tell(b.context ? fmt(b.context, s.st) : '', String(p) === String(a), a); }
    s.st.gate[id] = 'done';
  };
  (ctx.gates ||= []).push({id, commit, done, settle, open: reopen, options: opts});
  ctx.commit ||= () => { const g = ctx.gates.find(g => !g.done()); return g ? g.commit() : false; };
  const root = el('div', {}, q, box, why, verdict, note, el('div', {class: 'acts'}, go, again));
  root.addEventListener('keydown', e => {
    if (e.target.tagName === 'TEXTAREA' || !open() || e.metaKey || e.ctrlKey || e.altKey) return;
    const os = opts(), k = e.key.toLowerCase(), i = os.indexOf(picked);
    let j = /^[1-9]$/.test(k) ? +k - 1 : null;
    if (j == null && e.target.closest('.opts')) j = ['arrowright', 'arrowdown', 'd'].includes(k) ? i + 1 : ['arrowleft', 'arrowup', 'a'].includes(k) ? Math.max(0, i - 1) : null;
    if (j == null || j < 0 || j >= os.length) return;
    e.preventDefault(); pick(os[j]);
    if (e.target.closest('.opts')) box.children[j].focus();
  });
  s.on(() => {
    q.textContent = fmt(b.prompt, s.st);
    if (!Array.isArray(b.options) && open() && !opts().some(o => o === picked)) picked = null;
    paint();
  });
  return root;
});
