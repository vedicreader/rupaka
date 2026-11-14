/* links: arcs between the bodies named in `nodes`, one arc for each pair that has weight. `w` is a matrix (row i, column j) or a list
   (the weights from the node `row`). An arc is as thick as its weight, so the learner sees who attends to whom. With `row`, only the
   arcs from that node show. The arcs rise above the line of the nodes, and a node that links to itself gets a loop. */
(() => {
  const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
  const num = x => +(x != null && typeof x === 'object' ? x.value : x) || 0;
  Rupaka.block('links', (b, ctx) => {
    const S = ctx.scene;
    if (!S) throw new Error('links must be inside a scene');
    const bad = (b.nodes || []).find(id => !S.ids.has(id));
    if (bad) throw new Error(`links names "${bad}", which is not a body`);
    // The weights now as a list of [i, j, w], largest weight first.
    const edges = () => {
      const w = S.s.get(b.w), r = b.row == null ? null : Math.round(S.num(b.row)), n = b.nodes.length, out = [];
      if (!Array.isArray(w)) return out;
      const pairs = Array.isArray(w[0]) ? w.flatMap((row, i) => row.map((x, j) => [i, j, num(x)])) : w.map((x, j) => [r ?? 0, j, num(x)]);
      for (const [i, j, x] of pairs) if (i < n && j < n && (r == null || i === r) && x >= (b.min ?? .02)) out.push([i, j, x]);
      return out;
    };
    function build(T, P) {
      const es = edges(), at = b.nodes.map(id => S.bodies[id].frame.getWorldPosition(new T.Vector3()));
      const top = Math.max(...es.map(e => e[2]), 1e-9), sig = es.map(e => e.map(x => x.toFixed(3))).join(';') + at.map(p => p.toArray().map(x => x.toFixed(2))).join(';') + S.unit;
      if (sig === P.sig) return;
      P.sig = sig;
      P.g.children.slice().forEach(c => { c.geometry.dispose(); P.g.remove(c); });
      for (const [i, j, x] of es) {
        const a = at[i], c = at[j], d = a.distanceTo(c), up = new T.Vector3(0, 1, 0), lift = (b.lift ?? .45) * Math.max(d, S.size * .12);
        const curve = i === j
          ? new T.CubicBezierCurve3(a, a.clone().addScaledVector(up, lift * 1.4).add(new T.Vector3(-lift * .5, 0, 0)), a.clone().addScaledVector(up, lift * 1.4).add(new T.Vector3(lift * .5, 0, 0)), a)
          : new T.QuadraticBezierCurve3(a, a.clone().lerp(c, .5).addScaledVector(up, lift), c);
        const r = S.unit * (b.width ?? 1) * .3 * (.25 + .75 * x / top);
        const m = P.mat.clone(); m.opacity = clamp(.25 + .75 * x / top, .2, 1); m.transparent = true;
        P.g.add(new T.Mesh(new T.TubeGeometry(curve, 28, r, 6, false), m));
      }
    }
    return S.part(b, {
      make(T, P) { P.mat = S.lineMat(b.tone || 'acc'); P.g = new T.Group(); S.world.add(P.g); return P.g; },
      sync(P, live) { P.g.visible = live; },
      frame(P) { if (S.unit && S.T) build(S.T, P); },
    }, Rupaka.el('li', {text: 'links between the bodies'}));
  });
})();
