/* drift: dots that ride a path, as charges ride a wire or a column rides a road. `speed` is in laps of the path in one second,
   and a negative speed turns them round. The speed can be a state key, so a slider speeds the dots up. With reduced motion they stand still. */
(() => {
  Rupaka.block('drift', (b, ctx) => {
    const S = ctx.scene;
    if (!S) throw new Error('a drift must be inside a scene');
    return S.part(b, {
      make(T, P) {
        P.n = Math.round(b.n ?? 10); P.ph = 0; P.t0 = null;
        P.mesh = new T.InstancedMesh(new T.SphereGeometry(1, 14, 10), S.lineMat(b.tone || 'glow'), P.n);
        P.mesh.frustumCulled = false; S.world.add(P.mesh);
        return P.mesh;
      },
      sync(P, live) { P.mesh.visible = live; },
      run: P => S.num(b.speed) !== 0,
      frame(P, now) {
        const p = S.paths[b.on]; if (!p || !S.unit) return;
        const dt = P.t0 == null ? 0 : Math.min(.1, (now - P.t0) / 1000); P.t0 = now;
        if (!matchMedia('(prefers-reduced-motion: reduce)').matches) P.ph += S.num(b.speed) * dt;
        const T = S.T, v = new T.Vector3(), m = new T.Matrix4(), r = S.unit * (b.size ?? 1) * .5;
        for (let i = 0; i < P.n; i++) {
          const t = (((i / P.n + P.ph) % 1) + 1) % 1;
          m.makeScale(r, r, r).setPosition(p.at(t, v)); P.mesh.setMatrixAt(i, m);
        }
        P.mesh.instanceMatrix.needsUpdate = true;
      },
    }, Rupaka.el('li', {text: `dots that ride the path ${b.on}`}));
  });
})();
