/* point: a dot on its axis. It drags when its key is a state input; a point on a derived value only shows it.
   Arrows or WASD move one step; ⇧ moves ten. On a number line ↑/↓ move it too. */
Rupaka.block('point', (b, ctx) => {
  const {sv, show} = Rupaka, s = ctx.s, P = ctx.plane;
  if (!P) throw new Error('a point must be inside an axis');
  const kx = b.bind || b.x, ky = b.y, st = ctx.spec.state || {}, step = b.step ?? 1;
  const drag = b.drag ?? (Object.hasOwn(st, kx) && (!ky || Object.hasOwn(st, ky)));
  const dot = sv('circle', {class: 'dot', r: 7}), ring = sv('circle', {class: 'halo', r: 14}), txt = sv('text', {class: 'pl', 'text-anchor': 'middle'});
  const g = sv('g', drag ? {tabindex: 0, role: 'slider', 'aria-label': b.label || kx} : {role: 'img'}, ring, dot, txt);
  if (drag) g.classList.add('drag');
  const snap = (v, [lo, hi]) => +Math.min(hi, Math.max(lo, Math.round(v / step) * step)).toFixed(6);
  const put = (x, y) => { if (x !== s.get(kx)) ctx.put(b, kx, x); if (ky && y !== s.get(ky)) ctx.put(b, ky, y); };
  const at = e => { const pt = P.svg.createSVGPoint(); pt.x = e.clientX; pt.y = e.clientY; return pt.matrixTransform(P.svg.getScreenCTM().inverse()); };
  if (drag) {
    g.addEventListener('pointerdown', e => { if (!ctx.live(b.lock)) return; e.stopPropagation(); g.setPointerCapture(e.pointerId); g.classList.add('held'); });
    g.addEventListener('pointermove', e => { if (!g.hasPointerCapture(e.pointerId)) return; const p = at(e); put(snap(P.invX(p.x), P.x), ky ? snap(P.invY(p.y), P.y) : null); });
    g.addEventListener('pointerup', () => g.classList.remove('held'));
    g.addEventListener('keydown', e => {
      const k = e.key.toLowerCase(), d = step * (e.shiftKey ? 10 : 1);
      const dx = ['arrowright', 'd'].includes(k) ? d : ['arrowleft', 'a'].includes(k) ? -d : 0;
      const dy = ['arrowup', 'w'].includes(k) ? d : ['arrowdown', 's'].includes(k) ? -d : 0;
      if (!dx && !dy) return;
      e.preventDefault();
      if (ky) put(snap(+s.get(kx) + dx, P.x), snap(+s.get(ky) + dy, P.y));
      else put(snap(+s.get(kx) + (dx || dy), P.x));
    });
  }
  s.on(() => {
    const x = +s.get(kx), y = ky ? +s.get(ky) : null, cx = P.X(x), cy = ky ? P.Y(y) : P.Y(0);
    [dot, ring].forEach(c => { c.setAttribute('cx', cx); c.setAttribute('cy', cy); });
    txt.setAttribute('x', cx); txt.setAttribute('y', cy - 14); txt.textContent = b.label ? `${b.label}${b.show === false ? '' : ` ${show(x, 2)}${ky ? `, ${show(y, 2)}` : ''}`}` : '';
    g.style.visibility = Number.isFinite(x) && (!ky || Number.isFinite(y)) ? '' : 'hidden';
    if (drag) { g.setAttribute('aria-valuenow', x); g.setAttribute('aria-valuetext', ky ? `x ${show(x, 2)}, y ${show(y, 2)}` : show(x, 2)); }
  });
  return g;
});
