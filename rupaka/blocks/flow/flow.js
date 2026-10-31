/* flow: a few nodes and the arrows between them, left to right (row) or as a loop (cycle), for example guess → compare → adjust. */
Rupaka.block('flow', (b, ctx) => {
  const {el, sv} = Rupaka, ns = b.nodes || [], n = ns.length, cyc = b.layout === 'cycle', W = 600, LH = 19;
  const at = Object.fromEntries(ns.map((x, i) => [x.id, i]));
  const es = b.edges ?? ns.slice(cyc ? 0 : 1).map((x, i) => ({from: ns[i].id, to: ns[(i + 1) % n].id}));   // no edges: each node points to the next
  // The words of a node in at most two lines that fit `w`, at about 8 px a letter.
  const wrap = (t, w) => { const per = Math.max(4, Math.floor((w - 20) / 8)), out = [''];
    for (const wd of String(t).split(/\s+/)) { const l = out.length - 1; if (out[l] && (out[l] + ' ' + wd).length > per && out.length < 2) out.push(wd); else out[l] = out[l] ? `${out[l]} ${wd}` : wd; }
    return out; };
  const slot = cyc ? 170 : W / Math.max(n, 1), boxes = ns.map(x => { const ls = wrap(x.text, slot - 28);
    return {ls, w: Math.min(slot - 28, Math.max(64, 8 * Math.max(...ls.map(l => l.length)) + 26)), h: LH * ls.length + 16}; });
  const hmax = Math.max(...boxes.map(x => x.h), 0), arcs = es.map(e => at[e.to] - at[e.from]);
  const up = !cyc && arcs.some(d => d > 1) ? 56 : 8, down = !cyc && arcs.some(d => d < 0) ? 56 : 8;
  const H = cyc ? 300 : up + hmax + down, ry = (H - hmax) / 2 - 14, rx = W / 2 - 90;
  const ctr = i => cyc ? [W / 2 + rx * Math.cos(-Math.PI / 2 + 2 * Math.PI * i / n), H / 2 + ry * Math.sin(-Math.PI / 2 + 2 * Math.PI * i / n)] : [slot * (i + .5), up + hmax / 2];
  // The point where the line from the centre of box i toward [x, y] leaves the box, 5 px out.
  const edge = (i, [x, y]) => { const [cx, cy] = ctr(i), dx = x - cx, dy = y - cy, bx = boxes[i];
    const t = Math.min(Math.abs((bx.w / 2 + 5) / (dx || 1e-9)), Math.abs((bx.h / 2 + 5) / (dy || 1e-9))); return [cx + dx * t, cy + dy * t]; };
  const f = v => +v.toFixed(1), q = (a, c, z) => `M${f(a[0])} ${f(a[1])}Q${f(c[0])} ${f(c[1])} ${f(z[0])} ${f(z[1])}`;
  const head = (c, z) => { const a = Math.atan2(z[1] - c[1], z[0] - c[0]), p = s => [z[0] - 9 * Math.cos(a + s), z[1] - 9 * Math.sin(a + s)];
    const [l, r] = [p(.45), p(-.45)]; return `M${f(l[0])} ${f(l[1])}L${f(z[0])} ${f(z[1])}L${f(r[0])} ${f(r[1])}`; };
  const svg = sv('svg', {viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': [b.label, ...es.map(e => `${ns[at[e.from]].text} to ${ns[at[e.to]].text}`)].filter(Boolean).join('; ')});
  es.forEach((e, j) => {
    const i = at[e.from], k = at[e.to], A = ctr(i), Z = ctr(k), d = k - i;
    let c, out = [0, d < 0 ? 1 : -1];   // the side of the line that the words go on
    if (cyc) { const m = [(A[0] + Z[0]) / 2, (A[1] + Z[1]) / 2], ox = m[0] - W / 2, oy = m[1] - H / 2, l = Math.hypot(ox, oy) || 1;
      out = [ox / l, oy / l]; c = [m[0] + 30 * out[0], m[1] + 30 * out[1]]; }   // bend out from the middle, so the arrows make a loop
    else if (d === 1) c = [(A[0] + Z[0]) / 2, A[1]];
    else c = [(A[0] + Z[0]) / 2, d > 0 ? up - 48 : up + hmax + 48 - 8];   // a skip goes over the row, a step back goes under it
    const a = edge(i, d === 1 && !cyc ? Z : c), z = edge(k, d === 1 && !cyc ? A : c), mid = [(a[0] + 2 * c[0] + z[0]) / 4, (a[1] + 2 * c[1] + z[1]) / 4];
    const jog = [c[0] + 2, c[1] - 2.5];
    svg.append(sv('g', {class: 'edge', style: `--i: ${n + j}`, 'data-rk-id': ctx.id(b, `edges.${j}`)},
      sv('path', {class: 'ln', d: q(a, c, z) + head(c, z), pathLength: 1}),
      sv('path', {class: 'sk', d: q([a[0] + 1, a[1] + 1.5], jog, [z[0] - 1, z[1] + 1]), pathLength: 1}),
      e.text ? sv('text', {class: 'et', x: f(mid[0] + 10 * out[0]), y: f(mid[1] + 12 * out[1] + 4), text: e.text,
                           'text-anchor': out[0] > .3 ? 'start' : out[0] < -.3 ? 'end' : 'middle'}) : null));
  });
  ns.forEach((x, i) => { const [cx, cy] = ctr(i), bx = boxes[i], x0 = cx - bx.w / 2, y0 = cy - bx.h / 2;
    svg.append(sv('g', {class: 'node', style: `--i: ${i}`, 'data-rk-id': ctx.id(b, `nodes.${i}`)},
      sv('rect', {x: f(x0), y: f(y0), width: f(bx.w), height: f(bx.h), rx: 6}),
      sv('rect', {class: 'sk', x: f(x0 + 1.5), y: f(y0 - 1), width: f(bx.w - 2), height: f(bx.h + 1.5), rx: 8}),
      bx.ls.map((l, r) => sv('text', {x: f(cx), y: f(cy + (r - (bx.ls.length - 1) / 2) * LH + 5), 'text-anchor': 'middle', text: l})))); });
  return el('div', {}, Rupaka.label(b), svg);
});
