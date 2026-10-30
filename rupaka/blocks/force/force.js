/* force: an arrow in a scene. Its length is |mag| times the scene scale, so arrows in one scene compare. `at` is a point in the
   frame of the body `on` (or in the world), so the arrow moves with the body. `dir` is in the world. With `tip`, the arrow ends at
   the point (a push); else it starts there (a pull). The arrow grows when it shows or when its mag changes. */
(() => {
  const tone = d => d[1] > .5 ? 'up' : d[1] < -.5 ? 'down' : 'side';
  Rupaka.block('force', (b, ctx) => {
    const S = ctx.scene;
    if (!S) throw new Error('a force must be inside a scene');
    if (b.on && !S.ids.has(b.on)) throw new Error(`the force is on "${b.on}", which is not a body`);
    const name = b.tone || tone(S.vec(b.dir, [0, 1, 0]));
    const node = b.label ? S.chip(b, b.label, name) : Rupaka.el('li');
    if (!b.label) ctx.s.on(() => { node.textContent = `A force, ${Rupaka.show(S.num(b.mag), 2)}`; });
    let T;
    const len = P => Math.abs(S.num(b.mag)) * S.scale || 0;
    const way = P => {   // the unit direction; a negative mag turns it round
      const d = P.dir.set(...S.vec(b.dir, [0, 1, 0]));
      if (d.lengthSq() < 1e-9) d.set(0, 1, 0);
      return S.num(b.mag) < 0 ? d.normalize().negate() : d.normalize();
    };
    return S.part(b, {
      make(lib, P) {
        T = lib;
        const g = new T.Group(), mat = S.mat(name);
        const shaft = new T.Mesh(new T.CylinderGeometry(1, 1, 1, 24).translate(0, .5, 0), mat);
        const head = new T.Mesh(new T.ConeGeometry(1, 1, 32).translate(0, .5, 0), mat);
        g.add(shaft, head); S.world.add(g);
        Object.assign(P, {g, shaft, head, len: len(P), dir: new T.Vector3(0, 1, 0), base: new T.Vector3()});
        return g;
      },
      sync(P, live) {
        S.show(P, P.g, live);
        const to = len(P), from = P.len;
        if (to !== P.to) { P.to = to; S.anim(P, 600, k => { P.len = from + (to - from) * k; }); }
      },
      // Each frame: put the arrow at its point, along its direction, at its length now.
      frame(P) {
        const d = way(P), L = Math.max(P.len, 1e-3), r = S.unit * .55, hr = r * 2.6, hl = Math.min(hr * 2.4, L * .45);
        P.base.copy(S.point(b.on, b.at)); if (b.tip) P.base.addScaledVector(d, -L);
        P.g.position.copy(P.base);
        P.g.quaternion.setFromUnitVectors(new T.Vector3(0, 1, 0), d);
        P.shaft.scale.set(r, Math.max(1e-3, L - hl), r);
        P.head.scale.set(hr, hl, hr); P.head.position.y = L - hl;
      },
      // The chip goes on the arrow, at its full length.
      anchor(P) {
        if (!P.g) return null;
        const L = P.to ?? P.len;
        return S.point(b.on, b.at).addScaledVector(way(P), b.tip ? -L * .6 : L * .6);
      },
    }, node);
  });
})();
