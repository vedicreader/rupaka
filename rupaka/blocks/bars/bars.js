/* bars: horizontal bars from a derived list of {id, value, parts} or of numbers. Rows keep their element, so a new order slides. */
Rupaka.block('bars', (b, ctx) => {
  const {el, sv, show} = Rupaka, H = 30, W = 600, L = b.gutter ?? 48, names = b.items || {};
  const svg = sv('svg', {role: 'img', 'aria-label': b.label || b.bind}), keyed = {};
  const key = b.parts ? el('div', {class: 'key'}, b.parts.map((p, i) => el('span', {}, el('i', {class: `p${i ? 1 : 0}`}), p))) : null;
  const rows = () => (ctx.s.get(b.bind) || []).map((x, i) => typeof x === 'number' ? {id: String(i), value: x} : x);
  ctx.s.on(() => {
    const xs = rows(), mx = b.max ?? Math.max(...xs.map(x => x.value), 1e-9), sc = (W - L - 70) / mx;
    svg.setAttribute('viewBox', `0 0 ${W} ${H * xs.length || H}`);
    xs.forEach((x, i) => {
      let g = keyed[x.id];
      if (!g) { g = keyed[x.id] = sv('g', {class: 'bar'}, sv('text', {class: 't', x: 0, y: H / 2 + 5, text: names[x.id] || x.id}),
                  sv('rect', {class: 'p0', x: L, y: 7, height: H - 14}), sv('rect', {class: 'p1', y: 7, height: H - 14}), sv('text', {class: 'v', y: H / 2 + 5})); svg.append(g); }
      g.style.display = '';
      g.style.transform = `translate(0px, ${i * H}px)`;
      const [a, c] = x.parts || [x.value, 0], [r0, r1] = g.querySelectorAll('rect'), v = g.querySelector('text.v');
      r0.style.width = `${Math.max(0, a * sc)}px`; r1.style.x = `${L + a * sc}px`; r1.style.width = `${Math.max(0, c * sc)}px`;
      v.setAttribute('x', L + Math.max(0, (a + c) * sc) + 6); v.textContent = show(x.value, b.digits ?? 4);
    });
    Object.keys(keyed).forEach(id => { if (!xs.some(x => x.id === id)) keyed[id].style.display = 'none'; });
    svg.setAttribute('aria-label', `${b.label || b.bind}: ${xs.map(x => `${names[x.id] || x.id} ${show(x.value, b.digits ?? 4)}`).join(', ')}`);
  });
  return el('div', {}, Rupaka.label(b), svg, key);
});
