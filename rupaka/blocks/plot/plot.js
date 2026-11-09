/* plot: a line (or dots) through a derived series of {x, y}, on its axis. With `ghost`, the line from before the latest change stays faint. */
Rupaka.block('plot', (b, ctx) => {
  const {sv} = Rupaka, P = ctx.plane;
  if (!P) throw new Error('a plot must be inside an axis');
  const ghost = sv('path', {class: 'gh', 'clip-path': P.clip}), path = sv('path', {class: 'ln', 'clip-path': P.clip}), dots = sv('g', {class: 'dots', 'clip-path': P.clip});
  const g = sv('g', {role: 'img', 'aria-label': b.label || b.series}, ...b.ghost && !b.dots ? [ghost] : [], path, dots);
  if (b.tone) g.classList.add(`t-${b.tone}`);
  let cur = null, old = '', at = -1e9;   // the line now, the line before this burst of changes, the time of the last change
  ctx.s.on(() => {
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
    dots.replaceChildren(...(b.dots ? xs.filter(p => Number.isFinite(p.y)).map(p => sv('circle', {cx: P.X(p.x), cy: P.Y(p.y), r: 3.5})) : []));
  });
  return g;
});
