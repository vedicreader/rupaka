/* path: a line in 3D, drawn as a thin tube. It goes through `pts` (a place can be a state key), round a `circle`, or through the points of a
   state list (`of`). `grow` (0 to 1) draws only the first part, so a path can be walked. A body with `along` and a drift ride it.
   The path keeps its length and its points in S.paths[id], so other parts can find a place on it by t from 0 to 1. */
(() => {
  const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
  // A polyline as a function of the share t of its length.
  function line(T, pts, closed) {
    const P = closed && pts.length > 1 ? [...pts, pts[0]] : pts, cum = [0];
    for (let i = 1; i < P.length; i++) cum.push(cum[i - 1] + P[i].distanceTo(P[i - 1]));
    const L = cum[cum.length - 1];
    const at = (t, out = new T.Vector3()) => {
      if (!P.length) return out.set(0, 0, 0);
      const d = clamp(t, 0, 1) * L; let i = 1;
      while (i < P.length - 1 && cum[i] < d) i++;
      const w = cum[i] - cum[i - 1];
      return P.length < 2 ? out.copy(P[0]) : out.lerpVectors(P[i - 1], P[i], w > 0 ? clamp((d - cum[i - 1]) / w, 0, 1) : 0);
    };
    return {P, L, at};
  }
  const pt = (S, p) => Array.isArray(p) ? S.pos(p) : S.pos([p.x ?? 0, p.y ?? 0, p.z ?? 0]);

  Rupaka.block('path', (b, ctx) => {
    const S = ctx.scene;
    if (!S) throw new Error('a path must be inside a scene');
    const keyed = !!b.of || (b.pts || []).some(p => p.some(x => typeof x === 'string')) || typeof b.circle === 'string' || typeof b.grow === 'string'
                  || (b.about || []).some(x => typeof x === 'string');
    // The points now, in the world.
    const points = (T, P) => {
      if (b.circle != null) {
        const r = S.num(b.circle) || 0, c = new T.Vector3(...S.pos(b.about)), n = new T.Vector3(...S.vec(b.axis, [0, 1, 0])).normalize();
        const [u, v] = S.basis(n);
        return Array.from({length: 192}, (_, i) => { const a = i / 192 * 2 * Math.PI; return c.clone().addScaledVector(u, r * Math.cos(a)).addScaledVector(v, r * Math.sin(a)); });
      }
      const src = b.of ? S.list(b.of).filter(p => p && typeof p === 'object').map(p => pt(S, p)) : (b.pts || []).map(p => S.pos(p));
      const ps = src.map(p => new T.Vector3(...p));
      return b.smooth && ps.length > 2 ? new T.CatmullRomCurve3(ps, !!b.closed, 'centripetal').getPoints(ps.length * 16) : ps;
    };
    const closed = b.circle != null || !!b.closed;
    function build(T, P, final) {
      const ps = points(T, P), g = b.grow == null ? 1 : clamp(S.num(b.grow), 0, 1);
      const r = final ? S.unit * .15 * (b.width ?? 1) : 1e-3, sig = [ps.map(p => p.toArray().map(x => x.toFixed(3))).join(';'), g.toFixed(3), r.toFixed(4)].join('|');
      const full = line(T, ps, closed);
      P.ln = full;   // the path as a whole: other parts ride it whatever `grow` shows
      if (b.id) S.paths[b.id] = {at: (t, o) => full.at(t, o), length: () => full.L, closed};
      if (sig === P.sig) return;
      P.sig = sig; P.mesh.geometry.dispose();
      const cut = g >= 1 ? full : line(T, trim(T, full, g), false);
      const ok = cut.P.length > 1 && cut.L > 1e-6;
      P.mesh.visible = ok && P.on !== false; P.ok = ok;
      if (!ok) { P.mesh.geometry = new T.BufferGeometry(); P.tip.visible = false; return; }
      class Poly extends T.Curve { getPoint(t, o = new T.Vector3()) { return cut.at(t, o); } }
      P.mesh.geometry = new T.TubeGeometry(new Poly(), clamp(Math.ceil(cut.P.length * 10), 24, 900), r, 6, false);
      if (b.arrow) {
        const e = cut.at(1), d = e.clone().sub(cut.at(.98)).normalize(), h = Math.max(r * 7, 1e-3);
        P.tip.visible = P.on !== false; P.tip.geometry.dispose(); P.tip.geometry = new T.ConeGeometry(r * 3, h, 16).translate(0, h / 2, 0);
        P.tip.position.copy(e).addScaledVector(d, -h * .6); P.tip.quaternion.setFromUnitVectors(new T.Vector3(0, 1, 0), d);
      }
    }
    // The points of a polyline up to the share g of its length, with the end cut where g falls.
    function trim(T, ln, g) {
      const d = g * ln.L, out = [ln.P[0].clone()]; let run = 0;
      for (let i = 1; i < ln.P.length; i++) {
        const w = ln.P[i].distanceTo(ln.P[i - 1]);
        if (run + w >= d) { out.push(ln.P[i - 1].clone().lerp(ln.P[i], w > 0 ? (d - run) / w : 0)); return out; }
        run += w; out.push(ln.P[i].clone());
      }
      return out;
    }
    return S.part(b, {
      make(T, P) {
        const m = S.lineMat(b.tone || 'ink', b.opacity != null ? {transparent: true, opacity: b.opacity, depthWrite: false} : {});
        P.mesh = new T.Mesh(new T.BufferGeometry(), m); P.tip = new T.Mesh(new T.BufferGeometry(), m); P.tip.visible = false;
        P.g = new T.Group(); P.g.add(P.mesh, P.tip); S.world.add(P.g);
        build(T, P, false); P.sig = null;
        return P.g;
      },
      sync(P, live) { P.on = live; P.g.visible = live; if (S.unit) build(S.T, P, true); },
      frame(P) { if (S.unit && (keyed || P.sig === null || !P.fin)) { P.fin = true; build(S.T, P, true); } },
    }, Rupaka.el('li', {text: `${b.id ? b.id + ': ' : ''}a path`}));
  });
})();
