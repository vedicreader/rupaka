/* plot: a line (or dots) through a derived series of {x, y}, on its axis. With `ghost`, the line from before the latest change stays faint.
   With `guess` (a gate id) and `guesses` (one series key for each option of that gate, in the order of its options), the curve that the learner
   predicted is drawn dashed beside the true one from the moment of Lock in. It is a copy made then, so it stays while the inputs move.
   Two small tags, `your guess` and `true`, sit beside the two curves where they are farthest apart. Where the curves meet, one tag names both, in the right-most place where it touches no label, dot or line. */
Rupaka.block('plot', (b, ctx) => {
  const {sv} = Rupaka, P = ctx.plane;
  if (!P) throw new Error('a plot must be inside an axis');
  const ghost = sv('path', {class: 'gh', 'clip-path': P.clip}), path = sv('path', {class: 'ln', 'clip-path': P.clip}), dots = sv('g', {class: 'dots', 'clip-path': P.clip});
  const gs = sv('path', {class: 'gs', 'clip-path': P.clip}), guess = b.guess && b.guesses && !b.dots;
  const tg = sv('text', {class: 'tg', 'text-anchor': 'middle', display: 'none'}), tt = sv('text', {class: 'tg', 'text-anchor': 'middle', display: 'none'});
  const g = sv('g', {role: 'img', 'aria-label': b.label || b.series}, ...b.ghost && !b.dots ? [ghost] : [], ...guess ? [gs] : [], path, dots, ...guess ? [tg, tt] : []);
  if (b.tone) g.classList.add(`t-${b.tone}`);
  let cur = null, old = '', at = -1e9, kept = null;   // the line now, the line before this burst of changes, the time of the last change, the guess drawn
  const line = xs => { let d = '', pen = false; for (const p of xs) { const ok = Number.isFinite(p.y) && Math.abs(P.Y(p.y)) < 1e5; if (ok) { d += `${pen ? 'L' : 'M'}${P.X(p.x).toFixed(2)} ${P.Y(p.y).toFixed(2)}`; pen = true; } else pen = false; } return d; };
  // The tags keep a readable size: a narrow axis scales its drawing down, so the font grows to make up for it.
  let fs = 13, last = [];   // last: the series as drawn now
  const fit = () => { const w = P.svg.getBoundingClientRect().width; if (w) { fs = Math.max(13, 12 * P.W / w); [tg, tt].forEach(t => t.style.fontSize = `${fs.toFixed(1)}px`); if (kept) tag(last); } };
  if (guess && typeof ResizeObserver !== 'undefined') new ResizeObserver(fit).observe(P.svg);
  const spot = (text, x, y) => {   // the place for a tag, kept inside the plot box
    const [x0, x1] = [P.X(P.x[0]), P.X(P.x[1])], [y0, y1] = [P.Y(P.y[1]), P.Y(P.y[0])], hw = text.length * fs * 0.3;
    return [+Math.min(x1 - hw, Math.max(x0 + hw, x)).toFixed(1), +Math.min(y1 - 4, Math.max(y0 + fs, y)).toFixed(1)];
  };
  const put = (t, text, x, y) => {
    const [cx, cy] = spot(text, x, y);
    t.textContent = text; t.removeAttribute('display'); t.setAttribute('x', cx); t.setAttribute('y', cy);
  };
  // Where a tag touches no text, no dot and no line: the nearest such place to the curve (its right-most one), above it or below it. null if the browser cannot measure.
  const clear = (t, text, xs) => {
    try {
      t.textContent = text; t.removeAttribute('display'); t.setAttribute('x', 0); t.setAttribute('y', 0);
      const m = t.getBBox(), pad = 3, hw = m.width / 2 + pad, top = m.y - pad, bot = m.y + m.height + pad;
      const boxes = [...P.svg.querySelectorAll('text:not(.tg), .rk-point circle')].map(e => e.getBBox()).filter(r => r.width);
      const dots = [...P.svg.querySelectorAll('path.ln, path.gs')].filter(e => e.getAttribute('d')).flatMap(e => {
        const n = Math.ceil(e.getTotalLength() / 3); return Array.from({length: n + 1}, (_, i) => e.getPointAtLength(e.getTotalLength() * i / n)); });
      for (let k = 0; k < 14; k++) for (const lift of [-fs * (0.5 + k * 0.8), fs * (1.2 + k * 0.8)]) for (let i = xs.length - 1; i >= 0; i--) {
        if (!Number.isFinite(xs[i].y)) continue;
        const [cx, cy] = spot(text, P.X(xs[i].x), P.Y(xs[i].y) + lift), a = cx - hw, z = cx + hw, u = cy + top, v = cy + bot;
        if (!boxes.some(r => a < r.x + r.width && r.x < z && u < r.y + r.height && r.y < v) && !dots.some(q => q.x > a && q.x < z && q.y > u && q.y < v)) return [cx, cy];
      }
    } catch (e) { /* no layout: the caller falls back */ }
    return null;
  };
  const tag = xs => {
    [tg, tt].forEach(t => t.setAttribute('display', 'none'));
    if (!kept) return;
    const gaps = xs.map((p, i) => { const q = kept[i]; return q && Number.isFinite(p.y) && Number.isFinite(q.y) ? Math.abs(P.Y(q.y) - P.Y(p.y)) : -1; });
    const gap = Math.max(...gaps), best = gaps.findLastIndex(d => d >= gap * 0.6);   // the right-most place where they are far apart: it leaves the middle to the labels of points
    if (gap < 0) return;
    const p = xs[best], X = P.X(p.x), yt = P.Y(p.y), yg = P.Y(kept[best].y), side = (a, o) => a < o ? -fs * 0.5 : fs * 1.2;
    if (gap < fs * 1.5) return put(tg, 'your guess, true', ...clear(tg, 'your guess, true', xs) || [X, yt - fs * 0.5]);
    put(tg, 'your guess', X, yg + side(yg, yt)); put(tt, 'true', X, yt + side(yt, yg));
  };
  const pts = k => (ctx.s.get(k) || []).map(p => Array.isArray(p) ? {x: p[0], y: p[1]} : p);
  // The curve of the option that the learner locked in, copied once; a gate opened again takes it away.
  const guessed = () => {
    if (!guess) return;
    if (ctx.s.get(`gate.${b.guess}`) !== 'done') { kept = null; gs.removeAttribute('d'); return; }
    if (kept) return;
    const gt = ctx.gates?.find(x => x.id === b.guess), log = [...(ctx.s.get('log') || [])].reverse().find(e => e.gate === b.guess);
    const k = gt && log && b.guesses[gt.options().indexOf(log.picked)];
    if (!k) return;
    kept = pts(k); gs.setAttribute('d', line(kept));
    gs.setAttribute('aria-label', 'what you predicted');
  };
  ctx.s.on(() => {
    guessed();
    const xs = (ctx.s.get(b.series) || []).map(p => Array.isArray(p) ? {x: p[0], y: p[1]} : p);
    let d = '', pen = false;
    for (const p of xs) {
      const ok = Number.isFinite(p.y) && Math.abs(P.Y(p.y)) < 1e5;
      if (ok) { d += `${pen ? 'L' : 'M'}${P.X(p.x).toFixed(2)} ${P.Y(p.y).toFixed(2)}`; pen = true; } else pen = false;
    }
    if (b.ghost && cur !== null && d !== cur) {
      const now = performance.now();
      if (now - at > 500) { old = cur; ghost.setAttribute('d', old); }
      at = now;
    }
    cur = d;
    path.setAttribute('d', b.dots ? '' : d);
    last = xs;
    if (guess) queueMicrotask(() => tag(xs));   // after the dots and labels beside it have moved
    dots.replaceChildren(...(b.dots ? xs.filter(p => Number.isFinite(p.y)).map(p => sv('circle', {cx: P.X(p.x), cy: P.Y(p.y), r: 3.5})) : []));
  });
  return g;
});
