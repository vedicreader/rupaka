/* path: a line in 3D through `pts`, round a `circle`, or through a state list (`of`). A width under 0.5 is a hairline, else a thin tube.
   `grow` (0 to 1) draws the first part only. S.paths[id].at(t) gives a place on the whole path, for a body with `along` and for a drift. */
(() => {
  const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
  // A polyline as a function of the share t of its length.
  function line(T, pts, closed) {
    const P = closed && pts.length > 1 ? [...pts, pts[0]] : pts, cum = [0];
    for (let i = 1; i < P.length; i++) cum.push(cum[i - 1] + P[i].distanceTo(P[i - 1]));
    const L = cum.at(-1), at = (t, out = new T.Vector3()) => {
      if (P.length < 2) return P.length ? out.copy(P[0]) : out.set(0, 0, 0);
      const d = clamp(t, 0, 1) * L; let i = 1;
      while (i < P.length - 1 && cum[i] < d) i++;
      const w = cum[i] - cum[i - 1];
      return out.lerpVectors(P[i - 1], P[i], w > 0 ? clamp((d - cum[i - 1]) / w, 0, 1) : 0);
    };
    return {P, L, at};
  }
  // The points of a polyline up to the share g of its length.
  const trim = (ln, g) => {
    const d = g * ln.L, out = [ln.P[0]]; let run = 0;
    for (let i = 1; i < ln.P.length; i++) {
      const w = ln.P[i].distanceTo(ln.P[i - 1]);
      if (run + w >= d) return [...out, ln.P[i - 1].clone().lerp(ln.P[i], w > 0 ? (d - run) / w : 0)];
      run += w; out.push(ln.P[i]);
    }
    return out;
  };

  // A tube through the points P: three rings a leg (at its start, and close to each end), so a corner stays sharp.
  function tube(T, P, r) {
    P = P.filter((p, i) => !i || p.distanceTo(P[i - 1]) > 1e-9);
    const n = P.length - 1, e = i => clamp(r * 1.5 / (P[i + 1].distanceTo(P[i]) || 1), 0, .3);
    class Poly extends T.Curve {
      getUtoTmapping(u) { return u; }
      getPoint(t, o = new T.Vector3()) {
        const x = clamp(t, 0, 1) * n * 3, j = Math.min(n * 3 - 1, Math.floor(x)), i = Math.floor(j / 3), k = j % 3, f = x - j, w = e(i), at = [0, w, 1 - w, 1];
        return o.lerpVectors(P[i], P[i + 1], at[k] + (at[k + 1] - at[k]) * f);
      }
    }
    return new T.TubeGeometry(new Poly(), n * 3, r, 8, false);
  }

  Rupaka.block('path', (b, ctx) => {
    const S = ctx.scene;
    if (!S) throw new Error('a path must be inside a scene');
    const closed = b.circle != null || !!b.closed, thin = (b.width ?? 1) < .5;
    const points = T => {
      if (b.circle != null) {
        const r = S.num(b.circle), c = new T.Vector3(...S.pos(b.about)), [u, v] = S.basis(new T.Vector3(...S.vec(b.axis, [0, 1, 0])).normalize());
        return Array.from({length: 192}, (_, i) => { const a = i / 96 * Math.PI; return c.clone().addScaledVector(u, r * Math.cos(a)).addScaledVector(v, r * Math.sin(a)); });
      }
      const ps = (b.of ? S.rows(b.of) : b.pts || [])
        .map(p => new T.Vector3(...S.pos(p)));
      return b.smooth && ps.length > 2 ? new T.CatmullRomCurve3(ps, !!b.closed, 'centripetal').getPoints(ps.length * 16) : ps;
    };
    function build(T, P) {
      const full = line(T, points(T), closed), g = b.grow == null ? 1 : clamp(S.num(b.grow), 0, 1), r = (S.unit || 1e-2) * .15 * (b.width ?? 1);
      if (b.id) S.paths[b.id] = {at: full.at, length: () => full.L, closed};
      const sig = full.P.map(p => p.toArray().map(x => x.toFixed(3))).join() + g.toFixed(3) + r;
      if (sig === P.sig) return;
      P.sig = sig; P.mesh.geometry.dispose();
      const cut = g >= 1 ? full : line(T, trim(full, g), false), ok = cut.P.length > 1 && cut.L > 1e-6;
      P.mesh.visible = ok; P.tip.visible = ok && !!b.arrow;
      if (!ok) { P.mesh.geometry = new T.BufferGeometry(); return; }
      P.mesh.geometry = thin ? new T.BufferGeometry().setFromPoints(cut.P) : tube(T, closed && g >= 1 ? [cut.P[0].clone().lerp(cut.P[1], .5), ...cut.P.slice(1), cut.P[0].clone().lerp(cut.P[1], .5)] : cut.P, r);
      if (!b.arrow) return;
      const e = cut.at(1), d = e.clone().sub(cut.at(.98)).normalize(), h = Math.max(r * 7, (S.unit || 1e-2) * .8);
      P.tip.geometry.dispose(); P.tip.geometry = new T.ConeGeometry(h * .43, h, 16).translate(0, h / 2, 0);
      P.tip.position.copy(e).addScaledVector(d, -h * .6); P.tip.quaternion.setFromUnitVectors(new T.Vector3(0, 1, 0), d);
    }
    return S.part(b, {
      make(T, P) {
        const op = b.opacity ?? (thin ? .55 : null), o = op != null ? {transparent: true, opacity: op, depthWrite: false} : {};
        const m = thin ? new T.LineBasicMaterial({color: S.col(S.palette().lines[b.tone || 'ink']), ...o}) : S.lineMat(b.tone || 'ink', o);
        if (thin) S.recolors.push(() => S.paint(m, S.palette().lines[b.tone || 'ink']));
        P.mesh = thin ? new T.Line(new T.BufferGeometry(), m) : new T.Mesh(new T.BufferGeometry(), m);
        P.tip = new T.Mesh(new T.BufferGeometry(), thin ? S.lineMat(b.tone || 'ink') : m);
        P.g = new T.Group(); P.g.add(P.mesh, P.tip); S.world.add(P.g);
        build(T, P);
        return P.g;
      },
      sync(P, live) { P.g.visible = live; build(S.T, P); },   // a path reads only the state, so it changes only here
    }, Rupaka.el('li', {text: `${b.id ? b.id + ': ' : ''}a path`}));
  });
})();
