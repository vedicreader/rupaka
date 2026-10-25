/* plot: a line (or dots) through a derived series of {x, y}, on its axis. */
Rupaka.block('plot', (b, ctx) => {
  const {sv} = Rupaka, P = ctx.plane;
  if (!P) throw new Error('a plot must be inside an axis');
  const path = sv('path', {class: 'ln', 'clip-path': P.clip}), dots = sv('g', {class: 'dots', 'clip-path': P.clip});
  const g = sv('g', {role: 'img', 'aria-label': b.label || b.series}, path, dots);
  ctx.s.on(() => {
    const xs = (ctx.s.get(b.series) || []).map(p => Array.isArray(p) ? {x: p[0], y: p[1]} : p);
    let d = '', pen = false;
    for (const p of xs) {
      const ok = Number.isFinite(p.y) && Math.abs(P.Y(p.y)) < 1e5;
      if (ok) { d += `${pen ? 'L' : 'M'}${P.X(p.x).toFixed(2)} ${P.Y(p.y).toFixed(2)}`; pen = true; } else pen = false;
    }
    path.setAttribute('d', b.dots ? '' : d);
    dots.replaceChildren(...(b.dots ? xs.filter(p => Number.isFinite(p.y)).map(p => sv('circle', {cx: P.X(p.x), cy: P.Y(p.y), r: 3.5})) : []));
  });
  return g;
});
