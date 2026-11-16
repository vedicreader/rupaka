/* arrow: a straight arrow on its axis, from `from` to `to` ([x, y]; an item can be a state key). It uses the scale of the axis (ctx.plane).
   The head is a filled triangle with its tip at `to`; its size grows with `width`. With `head` false it is a plain bar, for a beam or a distance. The line stops under the head, so a dashed line
   does not show through it. The label sits past the tip, so it does not cover the line. An arrow of zero length draws nothing. */
Rupaka.block('arrow', (b, ctx) => {
  const {sv, fmt} = Rupaka, s = ctx.s, P = ctx.plane;
  if (!P) throw new Error('an arrow must be inside an axis');
  const w = b.width ?? 2.5, from = b.from || [0, 0], to = b.to || [0, 0];
  const line = sv('line', {class: 'ln', 'stroke-width': w, ...b.dash ? {'stroke-dasharray': `${(w * 2.4).toFixed(1)} ${(w * 2).toFixed(1)}`} : {}});
  const head = sv('path', {class: 'hd'}), txt = sv('text', {class: 'al'});
  const g = sv('g', {role: 'img'}, sv('g', {'clip-path': P.clip}, line, head), txt);
  g.classList.add(`t-${b.tone || 'acc'}`);
  const val = v => typeof v === 'string' ? +s.get(v) : +v, f = n => n.toFixed(2);
  const parts = [line, head, txt], off = empty => { parts.forEach(n => n.style.display = 'none'); g.toggleAttribute('data-rk-empty', empty); };   // empty: nothing to draw on purpose, so check does not call it a broken block
  s.on(() => {
    const label = b.label ? fmt(b.label, s.st) : '';
    g.setAttribute('aria-label', label || 'arrow');
    const [x0, y0] = from.map(val), [x1, y1] = to.map(val);
    if (b.show && !s.get(b.show)) return off(true);
    if (![x0, y0, x1, y1].every(Number.isFinite)) return off(false);   // a bad value is a fault, and check says so
    const ax = P.X(x0), ay = P.Y(P.line ? 0 : y0), tx = P.X(x1), ty = P.Y(P.line ? 0 : y1), dx = tx - ax, dy = ty - ay, len = Math.hypot(dx, dy);
    if (len < 0.5) return off(true);   // zero length: no direction, so no line and no head
    parts.forEach(n => n.style.display = ''); g.removeAttribute('data-rk-empty'); if (b.head === false) head.style.display = 'none';
    const ux = dx / len, uy = dy / len, hl = b.head === false ? 0 : Math.min(4 + w * 4, len * 0.6), hw = hl * 0.45;   // the head: its length and its half width
    const bx = tx - ux * hl, by = ty - uy * hl, cut = Math.max(0, len - hl * 0.85);   // the middle of the base; the line ends under the head
    Object.entries({x1: ax, y1: ay, x2: ax + ux * cut, y2: ay + uy * cut}).forEach(([k, v]) => line.setAttribute(k, f(v)));
    head.setAttribute('d', `M${f(tx)} ${f(ty)}L${f(bx - uy * hw)} ${f(by + ux * hw)}L${f(bx + uy * hw)} ${f(by - ux * hw)}Z`);
    // The label of an arrow goes past the tip, on the far side from the tail. The label of a bar goes at its middle, above it,
    // as on a drawing. Both stay inside the drawing.
    txt.textContent = label;
    const bar = b.head === false, up = ux >= 0 ? 1 : -1;   // (up·uy, −up·ux) is the normal of the bar that points up the screen
    const lx = bar ? (ax + tx) / 2 + up * uy * 9 : tx + ux * 8, ly = bar ? (ay + ty) / 2 - up * ux * 9 + 4 : ty + uy * 8 + (uy < -0.5 ? -4 : uy > 0.5 ? 14 : 5);
    txt.setAttribute('text-anchor', bar || Math.abs(ux) <= 0.35 ? 'middle' : ux > 0 ? 'start' : 'end');
    txt.setAttribute('x', f(Math.min(P.W - 4, Math.max(4, lx)))); txt.setAttribute('y', f(Math.min(P.H - 4, Math.max(14, ly))));
  });
  return g;
});
