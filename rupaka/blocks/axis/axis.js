/* axis: a number line (no y) or x/y axes with ticks. Child blocks (point, plot) draw on its shared scale. */
(() => {
  let seq = 0;
  const nice = (lo, hi, want) => { const raw = (hi - lo) / want, p = 10 ** Math.floor(Math.log10(raw)), m = raw / p;
    return (m < 1.5 ? 1 : m < 3 ? 2 : m < 7 ? 5 : 10) * p; };
  const ticks = (lo, hi, st) => { const out = []; for (let v = Math.ceil(lo / st - 1e-9) * st; v <= hi + 1e-9; v += st) out.push(+v.toFixed(10)); return out; };
  // Which ticks get a label: every k-th tick from 0 (or from the first tick when 0 is not a tick), out in both directions. k is the
  // smallest step at which no two labels meet (`size(i)` is the width of label i in SVG units) and the label step is round:
  // 1, 2 or 5 × 10ⁿ, or a whole number when the ticks are whole. An end tick off this grid gets a label only when it has room.
  // The SVG scales as one, so this holds at any width.
  const every = (vs, ps, size, gap = 6) => {
    const n = vs.length - 1, st = vs[1] - vs[0], z = vs.findIndex(v => Math.abs(v) < 1e-9), i0 = Math.max(z, 0);
    if (n < 1) return vs.map(() => true);
    const fits = (i, j) => Math.abs(ps[j] - ps[i]) >= (size(i) + size(j)) / 2 + gap, on = k => (i => (i - i0) % k === 0);
    const clash = k => vs.some((_, i) => on(k)(i) && i + k <= n && !fits(i, i + k));
    const round = k => { const q = +(k * st).toFixed(10), m = q / 10 ** Math.floor(Math.log10(q) + 1e-9);
      return Number.isInteger(+st.toFixed(10)) || [1, 2, 5, 10].some(x => Math.abs(m - x) < 1e-6); };
    let k = 1;
    while (k <= n && (clash(k) || !round(k))) k++;
    if (k > n) { k = 1; while (k < n && clash(k)) k++; }
    const out = vs.map((_, i) => on(k)(i));
    if (!out[0]) out[0] = fits(0, out.indexOf(true));
    if (!out[n]) out[n] = fits(out.lastIndexOf(true), n);
    return out;
  };
  Rupaka.block('axis', (b, ctx) => {
    const {el, sv, show} = Rupaka, [x0, x1] = b.x || [-5, 5], line = !b.y, [y0, y1] = b.y || [0, 1];
    const W = 600, H = line ? 80 : (b.height || 360), L = line ? 16 : 40, Rm = 16, T = line ? 30 : 12, B = line ? 30 : 28;
    const X = v => L + (v - x0) / (x1 - x0) * (W - L - Rm), Y = v => line ? T : T + (y1 - v) / (y1 - y0) * (H - T - B);
    const plane = {X, Y, line, W, H, x: [x0, x1], y: [y0, y1], invX: px => x0 + (px - L) / (W - L - Rm) * (x1 - x0), invY: py => y1 - (py - T) / (H - T - B) * (y1 - y0)};
    const id = `rk-clip-${++seq}`;
    const svg = sv('svg', {viewBox: `0 0 ${W} ${H}`, role: 'group', 'aria-label': b.label || 'axes'});
    plane.svg = svg; plane.clip = `url(#${id})`;
    const g = sv('g', {class: 'grid'});
    const xs = ticks(x0, x1, b.xstep || nice(x0, x1, 10)), ys = line ? [] : ticks(y0, y1, b.ystep || nice(y0, y1, 8));
    const ax = line ? T : Y(Math.min(y1, Math.max(y0, 0))), ay = X(Math.min(x1, Math.max(x0, 0)));
    const xl = xs.map(v => show(v, 3)), xon = every(xs, xs.map(X), i => 7.5 * xl[i].length), yon = every(ys, ys.map(Y), () => 13, 2);
    xs.forEach((v, i) => { g.append(sv('line', {class: v === 0 && !line ? 'zero' : 'hair', x1: X(v), x2: X(v), y1: line ? T - 5 : T, y2: line ? T + 5 : H - B}),
      ...xon[i] ? [sv('text', {class: 'num', x: X(v), y: line ? T + 22 : H - B + 18, 'text-anchor': 'middle', text: xl[i]})] : []); });
    ys.forEach((v, i) => { g.append(sv('line', {class: v === 0 ? 'zero' : 'hair', x1: L, x2: W - Rm, y1: Y(v), y2: Y(v)}),
      ...yon[i] ? [sv('text', {class: 'num', x: L - 6, y: Y(v) + 4, 'text-anchor': 'end', text: show(v, 3)})] : []); });
    g.append(sv('line', {class: 'main', x1: L, x2: W - Rm, y1: ax, y2: ax}));
    if (!line) g.append(sv('line', {class: 'main', x1: ay, x2: ay, y1: T, y2: H - B}));
    if (b.xlabel) g.append(sv('text', {class: 'axl', x: W - Rm, y: line ? T - 10 : ax - 8, 'text-anchor': 'end', text: b.xlabel}));
    if (b.ylabel && !line) g.append(sv('text', {class: 'axl', x: ay + 8, y: T + 12, text: b.ylabel}));
    svg.append(sv('defs', {}, sv('clipPath', {id}, sv('rect', {x: L, y: line ? 0 : T, width: W - L - Rm, height: line ? H : H - T - B}))), g);
    const c2 = Object.assign(Object.create(ctx), {plane});
    svg.append(...(b.blocks || []).map(k => Rupaka.build(k, c2)));
    return el('div', {}, Rupaka.label(b), svg);
  });
})();
