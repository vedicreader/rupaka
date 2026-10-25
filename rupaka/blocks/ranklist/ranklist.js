/* ranklist: an ordered list of ids. Drag a row, or focus it (↑/↓) and move it with ⌥↑/⌥↓ or W/S. `lock` keeps it still until that gate. */
Rupaka.block('ranklist', (b, ctx) => {
  const {el, sv} = Rupaka, s = ctx.s, H = 36, W = 300, names = b.items || {};
  const order = () => s.get(b.bind) || [];
  const svg = sv('svg', {viewBox: `0 0 ${W} ${H * order().length + 4}`, role: 'list', 'aria-label': b.label || b.bind});
  const rows = Object.fromEntries(order().map(id => [id, sv('g', {class: 'row', tabindex: 0, role: 'listitem', 'data-id': id},
    sv('rect', {class: 'hit', x: 0, y: 0, width: W, height: H, rx: 3}),
    sv('text', {class: 'n', x: 8, y: H / 2 + 5}), sv('text', {class: 't', x: 34, y: H / 2 + 5, text: names[id] || id}),
    sv('text', {class: 'grip', x: W - 18, y: H / 2 + 5, text: '⋮⋮'}), sv('line', {x1: 0, x2: W, y1: H, y2: H}))]));
  svg.append(...Object.values(rows));
  const live = () => ctx.live(b.lock);
  const move = (id, j) => {
    const o = order().filter(x => x !== id);
    o.splice(Math.max(0, Math.min(o.length, j)), 0, id);
    if (o.join() !== order().join()) ctx.put(b, b.bind, o);
  };
  let drag = null;
  svg.addEventListener('pointerdown', e => { const g = e.target.closest('.row'); if (!g || !live()) return;
    drag = {g, id: g.dataset.id}; svg.setPointerCapture(e.pointerId); g.classList.add('drag'); });
  svg.addEventListener('pointermove', e => { if (!drag) return; const p = svg.getBoundingClientRect(); move(drag.id, Math.floor((e.clientY - p.top) / p.width * W / H)); });
  svg.addEventListener('pointerup', () => { if (drag) drag.g.classList.remove('drag'); drag = null; });
  svg.addEventListener('keydown', e => {
    const g = e.target.closest('.row'); if (!g) return;
    const o = order(), i = o.indexOf(g.dataset.id), k = e.key.toLowerCase();
    const up = k === 'arrowup' || k === 'w', dn = k === 'arrowdown' || k === 's';
    if (!up && !dn) return;
    e.preventDefault();
    if (e.altKey || k === 'w' || k === 's') { if (live()) { move(g.dataset.id, i + (up ? -1 : 1)); g.focus(); } }
    else rows[o[Math.max(0, Math.min(o.length - 1, i + (up ? -1 : 1)))]].focus();
  });
  const note = el('div', {class: 'rk-note'});
  const wrap = el('div', {}, Rupaka.label(b), svg, note);
  s.on(() => {
    order().forEach((id, i) => { rows[id].setAttribute('transform', `translate(0 ${i * H})`); rows[id].querySelector('.n').textContent = i + 1;
      rows[id].setAttribute('aria-label', `${i + 1}: ${names[id] || id}`); });
    wrap.classList.toggle('live', live());
    note.textContent = b.hint || 'Drag a row, or focus it and press ⌥↑ ⌥↓ (or W S).';
    note.hidden = !live();
  });
  return wrap;
});
