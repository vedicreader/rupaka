/* body: one part of a scene. A primitive shape, or a group that holds other bodies. `in` puts it inside another body, so it
   moves and turns with that body. `at` is in the frame of its parent. `rot` (degrees about x, y and z) turns it about `pivot`.
   An item of `rot` can be a state key, so a slider turns the part; the turn eases, or cuts with prefers-reduced-motion. */
(() => {
  const SIZE = {box: [1, 1, 1], cylinder: [.5, 1], cone: [.5, 1], sphere: [.5], capsule: [.25, 1], torus: [.5, .15], group: []};
  const rad = d => d * Math.PI / 180;

  // A box with round edges: a rounded square, pushed out with a bevel. The normals are smooth, so the bands of light curve.
  function rounded(T, [x, y, z], r) {
    const s = new T.Shape(), e = 1e-5, w = x - 2 * r, h = y - 2 * r;
    s.absarc(e, e, e, -Math.PI / 2, -Math.PI, true);
    s.absarc(e, h, e, Math.PI, Math.PI / 2, true);
    s.absarc(w, h, e, Math.PI / 2, 0, true);
    s.absarc(w, e, e, 0, -Math.PI / 2, true);
    const g = new T.ExtrudeGeometry(s, {depth: Math.max(e, z - 2 * r), bevelEnabled: true, bevelSegments: 4, steps: 1,
                                        bevelSize: r - e, bevelThickness: r, curveSegments: 4});
    g.center();
    return smooth(T, g);
  }
  // Join the corners that share a place, then find the normals again.
  function smooth(T, g) {
    const p = g.attributes.position, seen = new Map(), pos = [], idx = [];
    for (let i = 0; i < p.count; i++) {
      const k = `${p.getX(i).toFixed(4)},${p.getY(i).toFixed(4)},${p.getZ(i).toFixed(4)}`;
      let j = seen.get(k);
      if (j === undefined) { j = pos.length / 3; seen.set(k, j); pos.push(p.getX(i), p.getY(i), p.getZ(i)); }
      idx.push(j);
    }
    const out = new T.BufferGeometry();
    out.setAttribute('position', new T.Float32BufferAttribute(pos, 3)); out.setIndex(idx); out.computeVertexNormals();
    return out;
  }
  function shape(T, b) {
    const z = Object.assign([...SIZE[b.kind]], b.size || []);
    switch (b.kind) {
      case 'box': {
        const r = Math.min(...z) * Math.min(.5, b.round ?? .14);
        return r > 1e-3 ? rounded(T, z, r) : new T.BoxGeometry(...z);
      }
      case 'cylinder': return z.length > 2 ? new T.CylinderGeometry(z[0], z[1], z[2], 40) : new T.CylinderGeometry(z[0], z[0], z[1], 40);
      case 'cone': return new T.ConeGeometry(z[0], z[1], 40);
      case 'sphere': return new T.SphereGeometry(z[0], 40, 24);
      case 'capsule': return new T.CapsuleGeometry(z[0], z[1], 8, 32);
      case 'torus': return new T.TorusGeometry(z[0], z[1], 20, 56);
    }
  }

  Rupaka.block('body', (b, ctx) => {
    const S = ctx.scene;
    if (!S) throw new Error('a body must be inside a scene');
    if (!Object.hasOwn(SIZE, b.kind)) throw new Error(`"${b.kind}" is not a body kind; use one of: ${Object.keys(SIZE).join(', ')}`);
    if (b.in && !S.ids.has(b.in)) throw new Error(`the body "${b.id}" is in "${b.in}", which is not a body`);
    return S.part(b, {
      make(T, P) {
        const outer = new T.Group(), frame = new T.Group(), at = S.vec(b.at), pv = b.pivot ? S.vec(b.pivot) : at;
        outer.position.set(...pv); frame.position.set(at[0] - pv[0], at[1] - pv[1], at[2] - pv[2]);
        outer.add(frame);
        if (b.kind !== 'group') frame.add(new T.Mesh(shape(T, b), S.mat(b.color || 'body')));
        (b.in ? S.bodies[b.in].frame : S.world).add(outer);
        S.bodies[b.id] = {outer, frame, b, P};
        P.rot = S.vec(b.rot).map(rad); outer.rotation.set(...P.rot);
        P.outer = outer;
        return outer;
      },
      sync(P, live) {
        S.show(P, P.outer, live);
        const to = S.vec(b.rot).map(rad), o = P.outer;
        if (to.every((x, i) => x === P.rot[i])) return;
        const from = [o.rotation.x, o.rotation.y, o.rotation.z];
        P.rot = to;
        S.anim(P, b.turn ?? 700, k => o.rotation.set(...from.map((x, i) => x + (to[i] - x) * k)));
      },
    }, Rupaka.el('li', {text: `${b.id}: a ${b.kind}`}));
  });
})();
