/* body: one part of a scene: a shape, or a group that holds bodies. `in` nests it; `at` is in the frame of its parent; `rot` turns it about `pivot`.
   A state key in at, rot, scale, angle, t or arc moves it. `texture` wraps earth, moon or a live sun; `glow` adds a halo; `light` makes it a lamp.
   `drag` gives a grip that writes the state key `to`: an angle (orbit) or a place along x, y or z of `at`. */
(() => {
  const R = Rupaka, SIZE = {box: [1, 1, 1], cylinder: [.5, 1], cone: [.5, 1], sphere: [.5], capsule: [.25, 1], torus: [.5, .15], plane: [1, 1], ring: [.6, 1],
                disc: [.5], map: [], globe: [], group: []};
  const rad = d => d * Math.PI / 180, deg = r => r * 180 / Math.PI, wrap = a => ((a + 540) % 360 + 360) % 360 - 180;
  const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
  const hasKey = v => Array.isArray(v) && v.some(x => typeof x === 'string');
  // The lon/lat window [lon0, lat0, lon1, lat1] of the world picture, as the uv of a flat shape.
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
      case 'sphere': return new T.SphereGeometry(z[0], b.texture ? 72 : 40, b.texture ? 48 : 24);
      case 'capsule': return new T.CapsuleGeometry(z[0], z[1], 8, 32);
      case 'torus': return new T.TorusGeometry(z[0], z[1], 20, 56);
      case 'plane': { const g = new T.PlaneGeometry(z[0], z[1]).rotateX(-Math.PI / 2); return b.uv ? window_(g, b.uv) : g; }
      case 'map': { const [lo0, la0, lo1, la1] = b.uv; return window_(new T.PlaneGeometry(lo1 - lo0, la1 - la0).rotateX(-Math.PI / 2), b.uv); }
      case 'ring': return new T.RingGeometry(z[0], z[1], 128, 1, rad(arc[0]), rad(arc[1] - arc[0])).rotateX(-Math.PI / 2);
      case 'disc': return new T.CircleGeometry(z[0], 96, rad(arc[0]), rad(arc[1] - arc[0])).rotateX(-Math.PI / 2);
      case 'globe': return new T.SphereGeometry(R.GLOBE, 96, 64);
    }
  }

  // A live sun: two layers of noise that drift, hot in the middle and dark at the limb.
  const NOISE = `float hash(vec3 p){p=fract(p*.3183099+.1);p*=17.;return fract(p.x*p.y*p.z*(p.x+p.y+p.z));}
    float noise(vec3 x){vec3 i=floor(x),f=fract(x);f=f*f*(3.-2.*f);return mix(mix(mix(hash(i),hash(i+vec3(1,0,0)),f.x),mix(hash(i+vec3(0,1,0)),hash(i+vec3(1,1,0)),f.x),f.y),
      mix(mix(hash(i+vec3(0,0,1)),hash(i+vec3(1,0,1)),f.x),mix(hash(i+vec3(0,1,1)),hash(i+vec3(1,1,1)),f.x),f.y),f.z);}
    float fbm(vec3 p){float a=.5,s=0.;for(int i=0;i<5;i++){s+=a*noise(p);p=p*2.03+7.;a*=.5;}return s;}`;
  const SUN = {vertexShader: 'varying vec3 vP,vN;void main(){vP=position;vN=normalMatrix*normal;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',
    fragmentShader: `uniform float time;varying vec3 vP,vN;${NOISE}
      void main(){vec3 p=normalize(vP);float v=fbm(p*5.+vec3(0.,time*.12,0.))*.65+fbm(p*19.+time*.25)*.45,limb=.4+.6*pow(max(normalize(vN).z,0.),.55);
      vec3 c=mix(vec3(1.,.36,.03),vec3(1.,.9,.55),smoothstep(.32,.78,v))+vec3(1.,.95,.8)*pow(v,5.)*.9;gl_FragColor=vec4(c*limb*1.3,1.);}`};
  // The air of a planet: a thin blue rim, bright on the day side.
  const AIR = {vertexShader: 'varying vec3 vN,vW;void main(){vN=normalize(mat3(modelMatrix)*normal);vW=(modelMatrix*vec4(position,1.)).xyz;gl_Position=projectionMatrix*viewMatrix*vec4(vW,1.);}',
    fragmentShader: 'varying vec3 vN,vW;void main(){vec3 n=normalize(vN),v=normalize(cameraPosition-vW);float i=pow(clamp(-dot(n,v)/.36,0.,1.),1.7);gl_FragColor=vec4(vec3(.3,.6,1.)*i*.45,1.);}'};
  const add = {transparent: true, depthWrite: false};

  function material(T, S, b) {
    b = {...b, texture: b.texture ?? (['map', 'globe'].includes(b.kind) ? 'earth' : undefined)};   // a map and a globe show the world by default
    const name = b.color || 'body', tex = b.texture && b.texture !== 'sun' && S.tex(b.texture), keep = (m, c) => (S.recolors.push(() => S.paint(m, S.palette()[c] || S.palette().body)), m);
    let m;
    if (b.texture === 'sun') m = new T.ShaderMaterial({uniforms: {time: {value: 0}}, ...SUN});
    else if (tex && (b.kind === 'map' || b.kind === 'plane')) m = new T.MeshBasicMaterial({map: tex});   // a map is read, not lit
    else if (tex) { S.lights(); m = new T.MeshStandardMaterial({map: tex, roughness: 1, metalness: 0}); }
    else if (b.glow != null || b.light) m = keep(new T.MeshBasicMaterial({color: S.col(S.palette()[b.color || 'glow'])}), b.color || 'glow');
    else if (S.sky && ['ring', 'disc', 'plane'].includes(b.kind)) m = keep(new T.MeshBasicMaterial({color: S.col(S.palette()[name] || S.palette().body)}), name);   // a flat mark in the sky is not lit
    else if (b.opacity != null || b.kind === 'ring' || b.kind === 'disc') {
      S.lights(); m = keep(S.mat(name).clone(), name);
      if (m.uniforms) Object.assign(m.uniforms, {light: S.light, alpha: {value: b.opacity ?? 1}});
    }
    else return S.mat(name);
    if (b.opacity != null) Object.assign(m, {transparent: true, opacity: b.opacity, depthWrite: false});
    if (m.isMeshStandardMaterial || b.kind === 'ring' || b.kind === 'disc') m.side = T.DoubleSide;
    return m;
  }
  // A soft round sprite of `stops` [[at, rgba]], for a halo.
  function sprite(T, stops, s) {
    const c = Object.assign(document.createElement('canvas'), {width: 128, height: 128}), g = c.getContext('2d'), r = g.createRadialGradient(64, 64, 0, 64, 64, 64);
    stops.forEach(([a, v]) => r.addColorStop(a, v)); g.fillStyle = r; g.fillRect(0, 0, 128, 128);
    const t = new T.CanvasTexture(c); t.colorSpace = T.SRGBColorSpace;
    const sp = new T.Sprite(new T.SpriteMaterial({map: t, ...add, blending: T.AdditiveBlending})); sp.userData = {flat: true, s};
    return sp;
  }
  const HALO = [[[0, 'rgba(255,236,190,1)'], [.16, 'rgba(255,190,90,.75)'], [.4, 'rgba(255,130,30,.2)'], [1, 'rgba(255,90,0,0)']],
                [[0, 'rgba(255,200,120,.35)'], [.5, 'rgba(255,150,60,.08)'], [1, 'rgba(255,120,0,0)']]];
  // N thin spokes across a ring: the edges of its slices, as on a dial.
  function spokes(T, S, [r0, r1], n) {
    const ps = Array.from({length: n}, (_, i) => { const a = i / n * 2 * Math.PI, c = Math.cos(a), s = -Math.sin(a); return [r0 * c, 0, r0 * s, r1 * c, 0, r1 * s]; }).flat();
    const g = new T.BufferGeometry(); g.setAttribute('position', new T.Float32BufferAttribute(ps, 3));
    const m = new T.LineBasicMaterial({color: S.col(S.palette().lines.ink), transparent: true, opacity: .5, depthWrite: false});
    S.recolors.push(() => S.paint(m, S.palette().lines.ink));
    return new T.LineSegments(g, m);
  }

  // The grip of a body with `drag`: a button over the body. Drag it, or press A/D or ←/→ (⇧ for ten nudges). A locked grip does nothing.
  // The maths runs in the frame of the parent body, so a nested body and the geo and globe coords drag the right way.
  function grip(S, b, ctx, P) {
    const orbit = b.drag === 'orbit', ix = {x: 0, y: 1, z: 2}[b.drag], [lo, hi] = b.range || [-Infinity, Infinity], step = b.nudge ?? (orbit ? 1 : .1);
    const g = R.el('button', {type: 'button', class: 'rk-grip', role: 'slider', 'aria-label': b.label || `Move ${b.id}`});
    S.gripBox.append(g);
    const cur = () => S.num(b.to), put = v => ctx.put(b, b.to, +clamp(v, lo, hi).toFixed(4));
    const V = (...a) => new S.T.Vector3(...a), par = () => P.outer.parent;
    const world = v => par().localToWorld(v.clone()), local = v => par().worldToLocal(v.clone());
    // Orbit: the plane of the circle. Slide: the plane through the body that holds the axis and faces the camera most.
    const setup = () => {
      if (orbit) {
        const c = V(...S.pos(b.about)), n = V(...S.vec(b.axis, [0, 1, 0])).normalize(), cw = world(c), nw = world(c.clone().add(n)).sub(cw).normalize();
        return {c, n, uv: S.basis(n), plane: new S.T.Plane().setFromNormalAndCoplanarPoint(nw, cw)};
      }
      const at = S.vec(b.at), up = [...at]; up[ix] += 1;
      const p0 = world(V(...S.pos(at))), d = world(V(...S.pos(up))).sub(p0), cd = S.cam().getWorldDirection(V());
      let n = V().crossVectors(d, V().crossVectors(cd, d)); if (n.lengthSq() < 1e-9) n = cd.clone();
      return {d, dd: d.lengthSq() || 1, plane: new S.T.Plane().setFromNormalAndCoplanarPoint(n.normalize(), p0)};
    };
    const hit = (e, k) => {
      const p = S.ray(e.clientX, e.clientY).intersectPlane(k.plane, V());
      if (!p || !orbit) return p;
      const q = local(p).sub(k.c); return deg(Math.atan2(q.dot(k.uv[1]), q.dot(k.uv[0])));
    };
    let k = null, from = 0, v0 = 0;
    g.addEventListener('pointerdown', e => {
      if (!ctx.live(b.lock)) return;
      k = setup(); from = hit(e, k); v0 = cur(); if (from == null) { k = null; return; }
      g.setPointerCapture(e.pointerId); g.classList.add('held'); e.preventDefault();
    });
    g.addEventListener('pointermove', e => {
      const a = k && hit(e, k); if (a == null) return;
      if (orbit) { v0 = clamp(v0 + wrap(a - from), lo, hi); from = a; put(v0); }
      else put(v0 + a.clone().sub(from).dot(k.d) / k.dd);
    });
    const up = () => { k = null; g.classList.remove('held'); };
    g.addEventListener('pointerup', up); g.addEventListener('pointercancel', up);
    g.addEventListener('keydown', e => {
      const d = {ArrowRight: 1, d: 1, ArrowLeft: -1, a: -1}[e.key.length === 1 ? e.key.toLowerCase() : e.key];
      if (!d || e.metaKey || e.ctrlKey || e.altKey) return;
      e.preventDefault(); e.stopPropagation(); put(cur() + d * step * (e.shiftKey ? 10 : 1));
    });
    const sync = () => {
      g.setAttribute('aria-valuenow', String(+cur().toFixed(2))); g.toggleAttribute('data-locked', !ctx.live(b.lock));
      if (Number.isFinite(lo)) g.setAttribute('aria-valuemin', lo);
      if (Number.isFinite(hi)) g.setAttribute('aria-valuemax', hi);
    };
    ctx.s.on(sync); sync();
    return g;
  }

  R.block('body', (b, ctx) => {
    const S = ctx.scene;
    if (!S) throw new Error('a body must be inside a scene');
    if (!Object.hasOwn(SIZE, b.kind)) throw new Error(`"${b.kind}" is not a body kind; use one of: ${Object.keys(SIZE).join(', ')}`);
    if (b.in && !S.ids.has(b.in)) throw new Error(`the body "${b.id}" is in "${b.in}", which is not a body`);
    if (b.kind === 'map' && !b.uv) throw new Error(`the map "${b.id}" needs uv: [lon0, lat0, lon1, lat1]`);
    if (b.drag && !b.to) throw new Error(`the body "${b.id}" has drag, so it needs "to": the state key that it writes`);
    const dyn = [b.at, b.pivot, b.scale].some(hasKey) || !!b.along || !!b.spin || b.orbit != null, live = hasKey(b.arc);
    const arc = () => { const [a, c] = b.arc ? b.arc.map(x => S.num(x)) : [0, 360]; return [a, Math.min(360, Math.max(.01, c - a)) + a]; };
    const mid = () => b.kind === 'map' ? [(b.uv[0] + b.uv[2]) / 2, (b.uv[1] + b.uv[3]) / 2, 0] : [0, 0, 0];
    const size = () => b.kind === 'globe' ? R.GLOBE : b.kind === 'map' ? Math.max(b.uv[2] - b.uv[0], b.uv[3] - b.uv[1]) / 2 : Math.max(...(b.size || SIZE[b.kind]));
    const onOrbit = () => {
      const n = new S.T.Vector3(...S.vec(b.axis, [0, 1, 0])).normalize(), [u, v] = S.basis(n), a = rad(S.num(b.angle)), r = S.num(b.orbit);
      return new S.T.Vector3(...S.pos(b.about)).addScaledVector(u, r * Math.cos(a)).addScaledVector(v, r * Math.sin(a)).toArray();
    };
    const put = P => {   // the place now: on a path, on an orbit, or at `at`; `pivot` is the point that rot turns about
      const at = b.along ? S.paths[b.along]?.at(S.num(b.t)).toArray() ?? [0, 0, 0] : b.orbit != null ? onOrbit() : S.pos(b.at ?? mid()), pv = b.pivot ? S.pos(b.pivot) : at;
      P.outer.position.set(...pv); P.frame.position.set(at[0] - pv[0], at[1] - pv[1], at[2] - pv[2]);
      if (b.scale) P.frame.scale.set(...S.vec(b.scale, [1, 1, 1]).map(x => Math.max(1e-3, x)));
    };
    return S.part(b, {
      make(T, P) {
        const outer = new T.Group(), frame = new T.Group();
        outer.add(frame); Object.assign(P, {outer, frame});
        if (b.kind !== 'group') {
          frame.add(P.mesh = new T.Mesh(shape(T, b, arc()), material(T, S, b)));
          const r = size();
          if ((b.texture ?? (b.kind === 'globe' ? 'earth' : 0)) === 'earth' && ['sphere', 'globe'].includes(b.kind)) frame.add(new T.Mesh(new T.SphereGeometry(r * 1.07, 64, 48), new T.ShaderMaterial({...AIR, ...add, side: T.BackSide, blending: T.AdditiveBlending})));
          if (b.glow != null) frame.add(...(P.halos = HALO.map((st, i) => sprite(T, st, r * (i ? 18 : 6)))));
          if (b.light) { frame.add(new T.PointLight(0xfff4e0, 3.4, 0, 0)); S.lights(); S.lamp(); }
          if (b.ticks && b.kind === 'ring') frame.add(spokes(T, S, Object.assign([...SIZE.ring], b.size || []), b.ticks));
        }
        if (!b.along || S.paths[b.along]) put(P);
        (b.in ? S.bodies[b.in].frame : S.world).add(outer);
        S.bodies[b.id] = {outer, frame, b, P};
        P.rot = S.vec(b.rot).map(rad); outer.rotation.set(...P.rot);
        if (b.drag) P.grip ??= grip(S, b, ctx, P);
        return outer;
      },
      sync(P, live) {
        S.show(P, P.outer, live);
        P.halos?.forEach(h => h.scale.setScalar(h.userData.s * (.4 + .6 * Math.max(0, S.num(b.glow, 1)))));
        const to = S.vec(b.rot).map(rad), o = P.outer;
        if (to.every((x, i) => x === P.rot[i])) return;
        const from = [o.rotation.x, o.rotation.y, o.rotation.z];
        P.rot = to;
        S.anim(P, b.turn ?? 700, k => o.rotation.set(...from.map((x, i) => x + (to[i] - x) * k)));
      },
      run: () => !!b.spin || b.texture === 'sun',
      frame(P, now = 0) {
        if (dyn) put(P);
        if (live && P.ver !== S.ver) { P.ver = S.ver; P.mesh.geometry.dispose(); P.mesh.geometry = shape(S.T, b, arc()); }
        if (b.spin && P.mesh) P.mesh.rotation.y = rad(b.spin * now / 1000);
        if (b.texture === 'sun') P.mesh.material.uniforms.time.value = now / 1000;
      },
      over(P) {
        if (!P.grip) return;
        const v = S.screen(P.frame.getWorldPosition(new S.T.Vector3()));
        P.grip.hidden = !(S.live(b) && S.seen(b.id) && v.on); P.grip.style.transform = `translate(${v.x.toFixed(1)}px, ${v.y.toFixed(1)}px)`;
      },
    }, R.el('li', {text: `${b.id}: a ${b.kind}${b.drag ? ', with a grip' : ''}`}));
  });
})();
