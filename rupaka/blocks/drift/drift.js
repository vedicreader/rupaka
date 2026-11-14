/* drift: dots that ride a path, as charge rides a wire. `speed` is laps a second (a key lets a slider set it; below 0 turns them round).
   With reduced motion they stand still. */
(() => {
  const still = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
  Rupaka.block('drift', (b, ctx) => {
    const S = ctx.scene;
    if (!S) throw new Error('a drift must be inside a scene');
    return S.part(b, {
      make(T, P) {
        Object.assign(P, {n: Math.round(b.n ?? 10), ph: 0, t0: null, v: new T.Vector3(), m: new T.Matrix4()});
        P.mesh = new T.InstancedMesh(new T.SphereGeometry(1, 14, 10), S.lineMat(b.tone || 'glow'), P.n);
        P.mesh.frustumCulled = false; S.world.add(P.mesh);
        return P.mesh;
      },
      sync(P, live) { P.mesh.visible = live; },
      run: () => S.num(b.speed) !== 0,
      frame(P, now) {
        const p = S.paths[b.on], r = S.unit * (b.size ?? 1) * .5; if (!p || !S.unit) return;
        if (!still() && P.t0 != null) P.ph += S.num(b.speed) * Math.min(.1, (now - P.t0) / 1000);
        P.t0 = now;
        for (let i = 0; i < P.n; i++) P.mesh.setMatrixAt(i, P.m.makeScale(r, r, r).setPosition(p.at((((i / P.n + P.ph) % 1) + 1) % 1, P.v)));
        P.mesh.instanceMatrix.needsUpdate = true;
      },
    }, Rupaka.el('li', {text: `dots that ride the path ${b.on}`}));
  });
})();
