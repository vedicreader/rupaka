/* body: one part of a scene. A primitive shape, or a group that holds other bodies. `in` puts it inside another body, so it
   moves and turns with that body. `at` is in the frame of its parent. `rot` (degrees about x, y and z) turns it about `pivot`.
   An item of `rot` can be a state key, so a slider turns the part; the turn eases, or cuts with prefers-reduced-motion.
   An item of `at` or `scale` can be a state key too: the body then follows the state at once. `along` puts it on a path (`t`, 0 to 1).
   `texture` wraps a vendored picture (earth, moon); `uv` is the lon/lat window of a plane or map. `glow` adds a halo, and `light` makes
   the body a lamp for the lit parts. `drag` gives the learner a grip that writes a state key: an angle round an axis, or a place on x, y or z. */
(() => {
  const SIZE = {box: [1, 1, 1], cylinder: [.5, 1], cone: [.5, 1], sphere: [.5], capsule: [.25, 1], torus: [.5, .15], plane: [1, 1], ring: [.6, 1],
                disc: [.5], map: [], globe: [], group: []};
  const rad = d => d * Math.PI / 180, deg = r => r * 180 / Math.PI, wrap = a => ((a + 540) % 360 + 360) % 360 - 180;
  const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
  const hasKey = v => Array.isArray(v) && v.some(x => typeof x === 'string');
  // The lon/lat window [lon0, lat0, lon1, lat1] of the world picture, as a change of the uv of a flat shape.
  function window_(g, [lo0, la0, lo1, la1]) {
    const uv = g.attributes.uv, u0 = (lo0 + 180) / 360, u1 = (lo1 + 180) / 360, v0 = (la0 + 90) / 180, v1 = (la1 + 90) / 180;
    for (let i = 0; i < uv.count; i++) uv.setXY(i, u0 + (u1 - u0) * uv.getX(i), v0 + (v1 - v0) * uv.getY(i));
    return g;
  }

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
  function shape(T, b, arc = [0, 360]) {
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
      case 'plane': { const g = new T.PlaneGeometry(z[0], z[1]).rotateX(-Math.PI / 2); return b.uv ? window_(g, b.uv) : g; }
      case 'map': { const [lo0, la0, lo1, la1] = b.uv; return window_(new T.PlaneGeometry(lo1 - lo0, la1 - la0).rotateX(-Math.PI / 2), b.uv); }
      case 'ring': return new T.RingGeometry(z[0], z[1], 128, 1, rad(arc[0]), rad(arc[1] - arc[0])).rotateX(-Math.PI / 2);
      case 'disc': return new T.CircleGeometry(z[0], 96, rad(arc[0]), rad(arc[1] - arc[0])).rotateX(-Math.PI / 2);
      case 'globe': return new T.SphereGeometry(R.GLOBE, 96, 64);
    }
  }

  // The look of a body: flat toon colour, a lit picture, or a lamp (a glow with no shading). Opacity makes it see-through.
  function material(T, S, b) {
    const name = b.color || 'body', tex = b.texture && S.tex(b.texture);
    let m;
    if (tex && (b.kind === 'map' || b.kind === 'plane')) m = new T.MeshBasicMaterial({map: tex});   // a map is read, not lit
    else if (tex) { S.lights(); m = new T.MeshStandardMaterial({map: tex, roughness: 1, metalness: 0}); }
    else if (b.glow != null || b.light) { const c = b.color || 'glow'; m = new T.MeshBasicMaterial({color: S.col(S.palette()[c])}); S.recolors.push(() => S.paint(m, S.palette()[c])); }
    else if (b.opacity != null || b.kind === 'ring' || b.kind === 'disc') { S.lights(); m = S.mat(name).clone(); if (m.uniforms) m.uniforms.light = S.light; S.recolors.push(() => S.paint(m, S.palette()[name] || S.palette().body)); }
    else return S.mat(name);
    if (b.opacity != null) { m.transparent = true; m.opacity = b.opacity; m.depthWrite = false; }
    if (m.isMeshStandardMaterial) m.side = T.DoubleSide;
    return m;
  }
  // The halo of a glowing body: a soft sprite that adds light to what is behind it.
  function halo(T, S, color) {
    const c = document.createElement('canvas'); c.width = c.height = 128;
    const g = c.getContext('2d'), r = g.createRadialGradient(64, 64, 0, 64, 64, 64);
    r.addColorStop(0, 'rgba(255,255,255,1)'); r.addColorStop(.25, 'rgba(255,255,255,.45)'); r.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = r; g.fillRect(0, 0, 128, 128);
    const t = new T.CanvasTexture(c); t.colorSpace = T.SRGBColorSpace;
    const m = new T.SpriteMaterial({map: t, color: S.col(color), blending: T.AdditiveBlending, depthWrite: false, transparent: true});
    const sp = new T.Sprite(m); sp.userData.flat = true;
    return sp;
  }

  // The grip of a body with `drag`: a button over the body. A drag writes the key `to`: an angle in degrees (orbit) or a place (x, y, z).
  // The keys A/D and ←/→ move it by `nudge` (⇧ for ten). A locked grip does nothing, as every locked control.
  function grip(S, b, ctx, P) {
    const orbit = b.drag === 'orbit', ax = {x: [1, 0, 0], y: [0, 1, 0], z: [0, 0, 1]}[b.drag];
    const [lo, hi] = b.range || [-Infinity, Infinity], step = b.nudge ?? (orbit ? 1 : .1);
    const g = Rupaka.el('button', {type: 'button', class: 'rk-grip', role: 'slider', 'aria-label': b.label || `Move ${b.id}`, 'aria-orientation': 'horizontal'});
    S.gripBox.append(g);
    const cur = () => +ctx.s.get(b.to) || 0, put = v => ctx.put(b, b.to, +clamp(v, lo, hi).toFixed(4));
    const frame = () => S.bodies[b.id].frame, T = () => S.T;
    const setup = () => {
      const V = T().Vector3, c = S.point(null, b.about), n = new V(...S.vec(b.axis, [0, 1, 0])).normalize();
      return orbit ? {c, n, uv: S.basis(n), plane: new (T().Plane)().setFromNormalAndCoplanarPoint(n, c)}
                   : {c: frame().getWorldPosition(new V()), n: S.cam().getWorldDirection(new V()), dir: new V(...ax)};
    };
    const hit = (e, k) => {
      const out = new (T().Vector3)(), ray = S.ray(e.clientX, e.clientY);
      if (!ray.intersectPlane(k.plane ?? new (T().Plane)().setFromNormalAndCoplanarPoint(k.n, k.c), out)) return null;
      if (!orbit) return out;
      const p = out.sub(k.c); return deg(Math.atan2(p.dot(k.uv[1]), p.dot(k.uv[0])));
    };
    let k = null, from = 0, v0 = 0;
    g.addEventListener('pointerdown', e => {
      if (!ctx.live(b.lock)) return;
      k = setup(); from = hit(e, k); v0 = cur(); if (from == null) { k = null; return; }
      g.setPointerCapture(e.pointerId); g.classList.add('held'); e.preventDefault();
    });
    g.addEventListener('pointermove', e => {
      if (!k) return;
      const a = hit(e, k); if (a == null) return;
      if (orbit) { const d = wrap(a - from); from = a; v0 = clamp(v0 + d, lo, hi); put(v0); }
      else put(v0 + a.clone().sub(from).dot(k.dir));
    });
    const up = () => { k = null; g.classList.remove('held'); };
    g.addEventListener('pointerup', up); g.addEventListener('pointercancel', up);
    g.addEventListener('keydown', e => {
      const d = {ArrowRight: 1, d: 1, ArrowLeft: -1, a: -1}[e.key.length === 1 ? e.key.toLowerCase() : e.key];
      if (!d || e.metaKey || e.ctrlKey || e.altKey) return;
      e.preventDefault(); e.stopPropagation(); put(cur() + d * step * (e.shiftKey ? 10 : 1));
    });
    const sync = () => {
      g.setAttribute('aria-valuenow', String(+cur().toFixed(2)));
      if (Number.isFinite(lo)) g.setAttribute('aria-valuemin', lo); if (Number.isFinite(hi)) g.setAttribute('aria-valuemax', hi);
      g.toggleAttribute('data-locked', !ctx.live(b.lock));
    };
    ctx.s.on(sync); sync();
    return g;
  }

  Rupaka.block('body', (b, ctx) => {
    const S = ctx.scene;
    if (!S) throw new Error('a body must be inside a scene');
    if (!Object.hasOwn(SIZE, b.kind)) throw new Error(`"${b.kind}" is not a body kind; use one of: ${Object.keys(SIZE).join(', ')}`);
    if (b.in && !S.ids.has(b.in)) throw new Error(`the body "${b.id}" is in "${b.in}", which is not a body`);
    if (b.kind === 'map' && !b.uv) throw new Error(`the map "${b.id}" needs uv: [lon0, lat0, lon1, lat1]`);
    if (b.drag && !b.to) throw new Error(`the body "${b.id}" has drag, so it needs "to": the state key that it writes`);
    const dyn = hasKey(b.at) || hasKey(b.pivot) || hasKey(b.scale) || !!b.along || !!b.spin || b.orbit != null;
    // The angles [from, to] of a ring or a disc now. Each can be a state key, so a sector can follow the state.
    const arcNow = () => b.arc ? [S.num(b.arc[0]), S.num(b.arc[1])] : [0, 360];
    const ends = () => { const [a, c] = arcNow(); return [a, Math.min(360, Math.max(.01, c - a)) + a]; };
    const mid = () => b.kind === 'map' ? [(b.uv[0] + b.uv[2]) / 2, (b.uv[1] + b.uv[3]) / 2, 0] : [0, 0, 0];
    // On a circle of radius `orbit` round `about`, across `axis`, at the angle `angle` in degrees.
    function onOrbit() {
      const T = S.T, n = new T.Vector3(...S.vec(b.axis, [0, 1, 0])).normalize(), [u, v] = S.basis(n), a = S.num(b.angle) * Math.PI / 180, r = S.num(b.orbit);
      return new T.Vector3(...S.pos(b.about)).addScaledVector(u, r * Math.cos(a)).addScaledVector(v, r * Math.sin(a)).toArray();
    }
    // The place of the body now: on its path, on its orbit, or at `at`. `pivot` is the point that rot turns about.
    function put(P) {
      const T = S.T, at = b.along ? S.paths[b.along]?.at(S.num(b.t)).toArray() ?? [0, 0, 0] : b.orbit != null ? onOrbit() : S.pos(b.at ?? mid()), pv = b.pivot ? S.pos(b.pivot) : at;
      P.outer.position.set(...pv); P.frame.position.set(at[0] - pv[0], at[1] - pv[1], at[2] - pv[2]);
      if (b.scale) P.frame.scale.set(...S.vec(b.scale, [1, 1, 1]).map(x => Math.max(1e-3, x)));
    }
    return S.part(b, {
      make(T, P) {
        const outer = new T.Group(), frame = new T.Group();
        outer.add(frame); P.outer = outer; P.frame = frame;
        if (b.kind !== 'group') {
          const mesh = new T.Mesh(shape(T, b, ends()), material(T, S, b));
          frame.add(mesh); P.mesh = mesh;
          if (b.glow != null) { P.halo = halo(T, S, S.palette().glow); frame.add(P.halo); S.recolors.push(() => P.halo.material.color.copy(S.col(S.palette().glow))); }
          if (b.light) { P.lamp = new T.PointLight(0xfff0d8, 3.2, 0, 0); frame.add(P.lamp); S.lights(); }
        }
        if (!b.along || S.paths?.[b.along]) put(P);
        (b.in ? S.bodies[b.in].frame : S.world).add(outer);
        S.bodies[b.id] = {outer, frame, b, P};
        P.rot = S.vec(b.rot).map(rad); outer.rotation.set(...P.rot);
        if (b.glow != null) P.r = b.kind === 'globe' ? R.GLOBE : b.kind === 'map' ? Math.max(b.uv[2] - b.uv[0], b.uv[3] - b.uv[1]) / 2 : Math.max(...(b.size || SIZE[b.kind] || [.5]));
        if (b.drag) P.grip ??= grip(S, b, ctx, P);
        return outer;
      },
      sync(P, live) {
        S.show(P, P.outer, live);
        if (P.halo) { P.halo.scale.setScalar(P.r * (3 + 7 * Math.max(0, S.num(b.glow) || 0))); }
        const to = S.vec(b.rot).map(rad), o = P.outer;
        if (to.every((x, i) => x === P.rot[i])) return;
        const from = [o.rotation.x, o.rotation.y, o.rotation.z];
        P.rot = to;
        S.anim(P, b.turn ?? 700, k => o.rotation.set(...from.map((x, i) => x + (to[i] - x) * k)));
      },
      run: () => !!b.spin,
      frame(P, now) {
        if (dyn) put(P);
        if (b.arc && P.mesh && hasKey(b.arc)) {
          const sig = arcNow().join();
          if (sig !== (P.arc ??= sig)) { P.arc = sig; P.mesh.geometry.dispose(); P.mesh.geometry = shape(S.T, b, ends()); }
        }
        if (b.spin && P.mesh) P.mesh.rotation.y = rad(b.spin * (now ?? 0) / 1000);
      },
      over(P) {
        if (!P.grip) return;
        const v = S.screen(P.frame.getWorldPosition(new S.T.Vector3())), live = S.live(b) && S.seen(b.id);
        P.grip.hidden = !live || !v.on; P.grip.style.transform = `translate(${v.x.toFixed(1)}px, ${v.y.toFixed(1)}px)`;
      },
    }, Rupaka.el('li', {text: `${b.id}: a ${b.kind}${b.drag ? ', with a grip' : ''}`}));
  });
})();
