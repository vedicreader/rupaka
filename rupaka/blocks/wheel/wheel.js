/* wheel: a ring. Item mode (`bind`): pick one item; drag the hand, click an item, ←/→ or A/D, Home/End.
   Angle mode (`angle`): a hand at a number of degrees over sectors (27 nakṣatras, with 12 rāśis outside); ⇧ moves ten steps.
   In angle mode the sector under the hand lights up only when the control is live, so a locked wheel does not give the answer away. */
Rupaka.block('wheel', (b, ctx) => {
  const {el, sv, show} = Rupaka, s = ctx.s, items = b.items || [], n = items.length, ang = b.angle != null;
  const key = ang ? b.angle : b.bind, W = ang ? 420 : 240, C = W / 2, r = ang ? 165 : 92, step = b.step ?? 1;
  const pol = (deg, rr) => { const t = deg * Math.PI / 180; return [C + rr * Math.sin(t), C - rr * Math.cos(t)]; };
  const svg = sv('svg', {viewBox: `0 0 ${W} ${W}`, tabindex: 0, role: 'slider', 'aria-label': b.label || key});
  const hand = sv('line', {class: 'hand'}), val = sv('text', {class: 'val', x: C, y: C + 10, 'text-anchor': 'middle'});
  const arc = (a0, a1, r0, r1) => { const [x0, y0] = pol(a0, r1), [x1, y1] = pol(a1, r1), [x2, y2] = pol(a1, r0), [x3, y3] = pol(a0, r0), big = a1 - a0 > 180 ? 1 : 0;
    return `M${x0} ${y0}A${r1} ${r1} 0 ${big} 1 ${x1} ${y1}L${x2} ${y2}A${r0} ${r0} 0 ${big} 0 ${x3} ${y3}Z`; };
  let ticks, wedge, marks;
  if (!ang) {
    ticks = items.map((it, i) => { const [x, y] = pol(360 * i / n, r);
      return sv('g', {class: 'tick', onclick: () => ctx.put(b, key, it)}, sv('circle', {class: 'dot', cx: x, cy: y, r: 15}), sv('text', {x, y: y + 5, 'text-anchor': 'middle', text: it})); });
    svg.append(sv('circle', {class: 'ring', cx: C, cy: C, r}), hand, ...ticks, val);
  } else {
    const sec = 360 / n, r0 = 80;
    wedge = sv('path', {class: 'wedge'});
    const lines = items.map((_, i) => { const [x0, y0] = pol(i * sec, r0), [x1, y1] = pol(i * sec, r); return sv('line', {class: 'sep', x1: x0, y1: y0, x2: x1, y2: y1}); });
    ticks = items.map((it, i) => { const a = (i + .5) * sec, [x, y] = pol(a, (r0 + r) / 2 + 2), rot = a <= 180 ? a - 90 : a + 90;
      return sv('text', {class: 'tick', x, y, 'text-anchor': 'middle', 'dominant-baseline': 'middle', transform: `rotate(${rot} ${x} ${y})`, text: it}); });
    marks = sv('g', {class: 'marks'}, Array.from({length: n * (b.marks || 1)}, (_, i) => { const [x0, y0] = pol(i * sec / (b.marks || 1), r - 6), [x1, y1] = pol(i * sec / (b.marks || 1), r);
      return sv('line', {x1: x0, y1: y0, x2: x1, y2: y1}); }));
    const out = b.outer || [], os = 360 / (out.length || 1), ro = 196;
    const outer = out.length ? sv('g', {class: 'outer'}, sv('circle', {class: 'ring', cx: C, cy: C, r: ro + 12}),
      out.map((t, i) => { const [x0, y0] = pol(i * os, r), [x1, y1] = pol(i * os, ro + 12), a = (i + .5) * os, [x, y] = pol(a, ro), rot = a > 90 && a < 270 ? a + 180 : a;
        return [sv('line', {class: 'sep', x1: x0, y1: y0, x2: x1, y2: y1}), sv('text', {x, y, 'text-anchor': 'middle', 'dominant-baseline': 'middle', transform: `rotate(${rot} ${x} ${y})`, text: t})]; })) : null;
    svg.append(wedge, sv('circle', {class: 'ring', cx: C, cy: C, r}), sv('circle', {class: 'ring', cx: C, cy: C, r: r0}), ...lines, marks, outer, ...ticks, hand, val);
  }
  const set = v => { if (v !== s.get(key)) ctx.put(b, key, v); };
  const norm = d => +(((Math.round(d / step) * step) % 360 + 360) % 360).toFixed(6);
  const pick = e => {
    const p = svg.getBoundingClientRect(), x = (e.clientX - p.left) / p.width * W - C, y = (e.clientY - p.top) / p.height * W - C;
    if (Math.hypot(x, y) < (ang ? 30 : 24)) return;
    const deg = (Math.atan2(x, -y) * 180 / Math.PI + 360) % 360;
    set(ang ? norm(deg) : items[Math.round(deg / 360 * n) % n]);
  };
  svg.addEventListener('pointerdown', e => { if (!ctx.live(b.lock)) return; svg.setPointerCapture(e.pointerId); svg.classList.add('drag'); pick(e); });
  svg.addEventListener('pointermove', e => { if (svg.hasPointerCapture(e.pointerId)) pick(e); });
  svg.addEventListener('pointerup', () => svg.classList.remove('drag'));
  svg.addEventListener('keydown', e => {
    const k = e.key.toLowerCase(), up = ['arrowright', 'arrowup', 'd'].includes(k), dn = ['arrowleft', 'arrowdown', 'a'].includes(k);
    if (!up && !dn && k !== 'home' && k !== 'end') return;
    e.preventDefault();
    if (ang) { const v = +s.get(key), d = step * (e.shiftKey ? 10 : 1); set(norm(k === 'home' ? 0 : k === 'end' ? 360 - step : v + (up ? d : -d))); return; }
    const i = items.indexOf(s.get(key)), j = k === 'home' ? 0 : k === 'end' ? n - 1 : i + (up ? 1 : -1);
    set(items[(j + n) % n]);
  });
  s.on(() => {
    const v = s.get(key), live = ctx.live(b.lock);
    if (ang) {
      const sec = 360 / n, i = Math.floor((+v % 360) / sec) % n, [x1, y1] = pol(+v, 30), [x2, y2] = pol(+v, r + 4);
      Object.entries({x1, y1, x2, y2}).forEach(([a, z]) => hand.setAttribute(a, z));
      val.textContent = `${show(+v, 2)}°`;
      wedge.setAttribute('d', arc(i * sec, (i + 1) * sec, 80, r)); wedge.style.display = live ? '' : 'none';
      ticks.forEach((t, j) => t.classList.toggle('on', live && j === i));
      marks.style.display = b.marks && (!b.marks_on || s.get(b.marks_on)) ? '' : 'none';
      svg.setAttribute('aria-valuenow', v); svg.setAttribute('aria-valuemin', 0); svg.setAttribute('aria-valuemax', 360);
      svg.setAttribute('aria-valuetext', `${show(+v, 2)} degrees${live ? `, ${items[i]}` : ''}`);
    } else {
      const i = items.indexOf(v), [x, y] = pol(360 * i / n, r), k = Math.hypot(x - C, y - C) || 1;
      hand.setAttribute('x1', C + (x - C) * 30 / k); hand.setAttribute('y1', C + (y - C) * 30 / k);
      hand.setAttribute('x2', C + (x - C) * (k - 16) / k); hand.setAttribute('y2', C + (y - C) * (k - 16) / k);
      val.textContent = show(v);
      ticks.forEach((t, j) => t.classList.toggle('on', j === i));
      svg.setAttribute('aria-valuenow', i); svg.setAttribute('aria-valuemin', 0); svg.setAttribute('aria-valuemax', n - 1); svg.setAttribute('aria-valuetext', show(v));
    }
  });
  const wrap = el('div', {}, Rupaka.label(b), svg);
  if (ang) wrap.classList.add('ang');
  return wrap;
});
