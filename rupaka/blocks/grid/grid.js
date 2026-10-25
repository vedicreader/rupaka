/* grid: a heatmap of a list of numbers or a list of rows. Click a cell to focus it; arrows or WASD move;
   + or E raise the cell by one step, − or Q lower it. The ramp mixes --rk-acc into the page colour. */
Rupaka.block('grid', (b, ctx) => {
  const {el, sv, show} = Rupaka, s = ctx.s, CW = b.cell || 64, CH = 40, step = b.step ?? 1;
  const mat = () => { const v = s.get(b.bind) || []; return Array.isArray(v[0]) ? v : [v]; };
  const flat = !Array.isArray((s.get(b.bind) || [])[0]);
  const m0 = mat(), nr = m0.length, nc = m0[0]?.length || 0, L = b.rows ? (b.gutter ?? 70) : 0, T = b.cols ? 24 : 0;
  const svg = sv('svg', {viewBox: `0 0 ${L + nc * CW + 2} ${T + nr * CH + 2}`, tabindex: 0, role: 'grid', 'aria-label': b.label || b.bind, style: `width: ${L + nc * CW + 2}px`});
  const say = el('div', {class: 'rk-sr', 'aria-live': 'polite'});
  let fi = 0, fj = 0;
  const cells = m0.map((row, i) => row.map((_, j) => { const g = sv('g', {class: 'cell', transform: `translate(${L + j * CW + 1} ${T + i * CH + 1})`},
    sv('rect', {width: CW - 2, height: CH - 2, rx: 2}), sv('text', {x: CW / 2 - 1, y: CH / 2 + 4, 'text-anchor': 'middle'}));
    g.addEventListener('pointerdown', () => { fi = i; fj = j; paint(); svg.focus({preventScroll: true}); }); return g; }));
  (b.cols || []).forEach((c, j) => svg.append(sv('text', {class: 'hd', x: L + j * CW + CW / 2, y: 16, 'text-anchor': 'middle', text: c})));
  (b.rows || []).forEach((r, i) => svg.append(sv('text', {class: 'hd', x: L - 8, y: T + i * CH + CH / 2 + 5, 'text-anchor': 'end', text: r})));
  const cur = sv('rect', {class: 'cur', width: CW - 2, height: CH - 2, rx: 2});
  svg.append(...cells.flat(), cur);
  const change = d => {
    if (!ctx.live(b.lock)) return;
    const m = mat().map(r => r.slice()), lo = b.min ?? -Infinity, hi = b.max ?? Infinity;
    m[fi][fj] = +Math.min(hi, Math.max(lo, m[fi][fj] + d)).toFixed(6);
    ctx.put(b, b.bind, flat ? m[0] : m);
  };
  svg.addEventListener('keydown', e => {
    const k = e.key.toLowerCase(), d = step * (e.shiftKey && !['+', '-', '_', '='].includes(k) ? 10 : 1);
    const mv = {arrowup: [-1, 0], w: [-1, 0], arrowdown: [1, 0], s: [1, 0], arrowleft: [0, -1], a: [0, -1], arrowright: [0, 1], d: [0, 1]}[k];
    if (mv) { e.preventDefault(); fi = Math.max(0, Math.min(nr - 1, fi + mv[0])); fj = Math.max(0, Math.min(nc - 1, fj + mv[1])); paint(); return; }
    if (['+', '=', 'e'].includes(k)) { e.preventDefault(); change(d); }
    else if (['-', '_', 'q', '−'].includes(k)) { e.preventDefault(); change(-d); }
  });
  function paint() {
    const m = mat(), vs = m.flat(), lo = b.lo ?? Math.min(...vs), hi = b.hi ?? Math.max(...vs);
    m.forEach((row, i) => row.forEach((v, j) => {
      const g = cells[i]?.[j]; if (!g) return;
      const pc = hi > lo ? 6 + Math.round((v - lo) / (hi - lo) * 28) : 6;
      g.firstChild.style.fill = `color-mix(in srgb, var(--rk-acc) ${pc}%, var(--rk-bg))`;
      g.lastChild.textContent = show(v, b.digits ?? 2);
    }));
    cur.setAttribute('x', L + fj * CW + 1); cur.setAttribute('y', T + fi * CH + 1);
    const lbl = [b.rows?.[fi], b.cols?.[fj]].filter(Boolean).join(', ') || `row ${fi + 1}, column ${fj + 1}`;
    svg.setAttribute('aria-valuetext', `${lbl}: ${show(m[fi][fj], b.digits ?? 2)}`); say.textContent = svg.getAttribute('aria-valuetext');
  }
  s.on(paint);
  return el('div', {}, Rupaka.label(b), svg, say, b.note ? el('div', {class: 'rk-note', text: b.note}) : null);
});
