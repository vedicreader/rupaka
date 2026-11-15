/* links: arcs between the bodies of `nodes`, as thick and as solid as their weights. `w` is a matrix (row i, column j) or a list (the weights
   from node `row`). With `row`, only the arcs of that node show. A weight of a node on itself is a small ring round it. */
(() => {
  const num = x => { const n = +(x != null && typeof x === 'object' ? x.value : x); return Number.isFinite(n) ? n : 0; };
  Rupaka.block('links', (b, ctx) => {
    const S = ctx.scene;
    if (!S) throw new Error('links must be inside a scene');
    const bad = (b.nodes || []).find(id => !S.ids.has(id));
    if (bad) throw new Error(`links names "${bad}", which is not a body`);
    const edges = () => {   // [i, j, w] for each weight that shows
      const w = S.list(b.w), r = b.row == null ? null : Math.round(S.num(b.row)), n = b.nodes.length;
      const all = Array.isArray(w[0]) ? w.flatMap((row, i) => Array.isArray(row) ? row.map((x, j) => [i, j, num(x)]) : []) : w.map((x, j) => [r ?? 0, j, num(x)]);
      return all.filter(([i, j, x]) => i < n && j < n && (r == null || i === r) && x >= (b.min ?? .02));
    };
    function build(T, P) {
      const es = edges(), all = b.row == null && Array.isArray(S.list(b.w)[0]), at = b.nodes.map(id => S.bodies[id].frame.getWorldPosition(new T.Vector3()));
      const top = Math.max(...es.map(e => e[2]), 1e-9), gap = Math.min(...at.flatMap((p, i) => at.slice(i + 1).map(q => p.distanceTo(q))), S.size);
      const sig = JSON.stringify(es) + at.map(p => p.toArray().map(x => x.toFixed(2))).join() + S.unit;
      if (sig === P.sig) return;
      P.sig = sig;
      P.g.children.slice().forEach(c => { c.geometry.dispose(); c.material.dispose(); P.g.remove(c); });
      for (const [i, j, x] of es) {
        const a = at[i], c = at[j], k = .25 + .75 * x / top, r = Math.min(S.unit * (b.width ?? 1) * .3, gap * .06) * k, d = c.clone().sub(a).normalize();
        const up = new T.Vector3(0, 1, 0).addScaledVector(d, -d.y);   // up, with the part along the arc taken out; for a line that goes up, to the side
        if (up.lengthSq() < .05) up.set(1, 0, 0).addScaledVector(d, -d.x);
        up.normalize().multiplyScalar(i > j && all ? -1 : 1);
        const geo = i === j ? new T.TorusGeometry(gap * .22, r, 6, 40).rotateX(Math.PI / 2).translate(a.x, a.y, a.z)
          : new T.TubeGeometry(new T.QuadraticBezierCurve3(a, a.clone().lerp(c, .5).addScaledVector(up, (b.lift ?? .45) * a.distanceTo(c)), c), 28, r, 6, false);
        const m = P.mat.clone(); Object.assign(m, {transparent: true, opacity: Math.max(.2, k), depthWrite: false});
        P.g.add(new T.Mesh(geo, m));
      }
    }
    return S.part(b, {
      make(T, P) { P.mat = S.lineMat(b.tone || 'acc'); P.g = new T.Group(); S.world.add(P.g); S.recolors.push(() => { P.sig = P.ver = null; }); return P.g; },
      sync(P, live) { P.g.visible = live; },
      frame(P) { if (P.ver !== S.ver) { P.ver = S.ver; build(S.T, P); } },   // once a change: the nodes have moved by then
    }, Rupaka.el('li', {text: 'links between the bodies'}));
  });
})();
