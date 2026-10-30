/* scene: a 3D view in a toon style, drawn with three.js. Its child blocks (body, force, label3d, shot) are its parts.
   three.js loads only for a spec that has a scene (Rupaka.need). The look: flat colour in three soft bands, ink outlines from
   one edge pass on depth and normals, a soft floor with contact shadows, and label chips in screen space that never overlap.
   Colours come from the --rk-* vars. The camera moves between named shots with easing; with prefers-reduced-motion it cuts.
   `bind` is the step: a part with `step: n` shows from step n. Keys on the view: A/D back and next, 1-9 a step, Q/E turn, W/S tilt. */
(() => {
  const R = Rupaka, {el, sv, fmt} = R;
  const SHOTS = {wide: {az: 35, el: 22, fov: 32}, side: {az: 0, el: 4, fov: 12}, front: {az: 90, el: 4, fov: 12},
                 top: {az: 0, el: 89, fov: 12}, close: {az: 30, el: 18, fov: 28}};
  const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
  const inout = t => (t = clamp(t, 0, 1)) < .5 ? 4 * t ** 3 : 1 - (2 - 2 * t) ** 3 / 2;
  const settle = t => { t = clamp(t, 0, 1) - 1; return 1 + 2.4 * t ** 3 + 1.4 * t ** 2; };   // a small overshoot, then rest
  const still = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
  const rad = d => d * Math.PI / 180;
  const lum = c => .2126 * c[0] + .7152 * c[1] + .0722 * c[2];
  const mix = (a, b, t) => a.map((x, i) => x + (b[i] - x) * t);
  const scenes = new WeakMap();   // store -> its scenes, for Rupaka.cam
  // One watch on the theme for all scenes: a change of the OS scheme, or of a class, data-theme or style on <html>.
  // Each scene in `themed` gives false when its view has left the page; then it frees its WebGL context and drops out.
  const themed = new Set();
  let watch = null;
  const retheme = () => themed.forEach(f => { if (!f()) themed.delete(f); });
  const onTheme = f => {
    themed.add(f);
    if (watch) return;
    watch = new MutationObserver(retheme);
    watch.observe(document.documentElement, {attributes: true, attributeFilter: ['class', 'data-theme', 'style']});
    matchMedia('(prefers-color-scheme: dark)').addEventListener('change', retheme);
  };
  R.SHOTS = Object.keys(SHOTS).filter(k => k !== 'close');

  // A shot name: wide, side, front, top, or close:<body id>.
  const isShot = (v, ids) => typeof v === 'string' && (R.SHOTS.includes(v) || (v.startsWith('close:') && ids.has(v.slice(6))));

  // The board's `cam` operation: set the key that a shot block binds. It gives false for a bad name or a scene with no such key.
  R.cam = (host, shot) => {
    const s = host?.rupaka;
    if (!s) throw new Error('no rupaka demo is mounted in this element');
    for (const S of scenes.get(s) || []) {
      const k = S.shotKey();
      if (k && isShot(shot, S.ids)) { R.set(host, {[k]: shot}); return true; }
    }
    return false;
  };

  const TOON_V = `varying vec3 vN;
    void main() { vN = normalize(normalMatrix * normal); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.); }`;
  // Three bands of light with soft, anti-aliased edges, so a flat colour stays true in the light band.
  const TOON_F = `uniform vec3 color; uniform vec3 light; varying vec3 vN;
    void main() {
      vec3 n = normalize(vN); if (!gl_FrontFacing) n = -n;
      float d = dot(n, light), a = fwidth(d) * 1.5 + .002;
      float band = .66 + .16 * smoothstep(-.3 - a, -.3 + a, d) + .18 * smoothstep(.3 - a, .3 + a, d);
      gl_FragColor = vec4(color * band, 1.);
      #include <colorspace_fragment>
    }`;
  const FLAT_V = `varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.); }`;
  // The floor fades into the page at its rim. A contact shadow is dark at its middle and soft at its edge.
  const FLOOR_F = `uniform vec3 color; varying vec2 vUv;
    void main() { float r = length(vUv - .5) * 2.; gl_FragColor = vec4(color, 1. - smoothstep(.35, 1., r)); }`;
  // The contact shadow: the scene seen from under the floor, dark where a part is near the floor, then blurred.
  const DARK_V = `varying float vY; void main() { vec4 p = modelMatrix * vec4(position, 1.); vY = p.y; gl_Position = projectionMatrix * viewMatrix * p; }`;
  const DARK_F = `uniform float floor, fade; varying float vY;
    void main() { float a = 1. - clamp((vY - floor) / fade, 0., 1.); gl_FragColor = vec4(0., 0., 0., a * a); }`;
  const BLUR_F = `uniform sampler2D map; uniform vec2 step; varying vec2 vUv;
    void main() {
      float w[5]; w[0] = .227; w[1] = .194; w[2] = .121; w[3] = .054; w[4] = .016;
      float a = texture2D(map, vUv).a * w[0];
      for (int i = 1; i < 5; i++) a += (texture2D(map, vUv + step * float(i)).a + texture2D(map, vUv - step * float(i)).a) * w[i];
      gl_FragColor = vec4(0., 0., 0., a);
    }`;
  const SHADOW_F = `uniform vec3 color; uniform float alpha; uniform sampler2D map; varying vec2 vUv;
    void main() { float r = length(vUv - .5) * 2.; gl_FragColor = vec4(color, alpha * texture2D(map, vec2(vUv.x, 1. - vUv.y)).a * (1. - smoothstep(.7, 1., r))); }`;
  const POST_V = `varying vec2 vUv; void main() { vUv = uv; gl_Position = vec4(position.xy, 0., 1.); }`;
  // The ink: a line where the depth steps toward the viewer (the outline) or where the normal turns fast (a crease).
  const POST_F = `uniform sampler2D tC; uniform sampler2D tN; uniform sampler2D tD; uniform vec2 texel; uniform float w, near, far; uniform vec3 ink;
    varying vec2 vUv;
    float lin(float d) { float z = d * 2. - 1.; return 2. * near * far / (far + near - z * (far - near)); }
    void main() {
      vec3 col = texture2D(tC, vUv).rgb;
      float d0 = texture2D(tD, vUv).x, l0 = lin(d0), de = 0., ne = 0.;
      vec3 n0 = texture2D(tN, vUv).xyz * 2. - 1.;
      for (int i = 0; i < 8; i++) {
        float a = float(i) * .7853982;
        vec2 uv = vUv + vec2(cos(a), sin(a)) * texel * w;
        float d = texture2D(tD, uv).x;
        de += min(lin(d) - l0, l0);
        if (d0 < 1. && d < 1.) ne = max(ne, 1. - dot(n0, texture2D(tN, uv).xyz * 2. - 1.));
      }
      float e = d0 < 1. ? max(smoothstep(.05, .16, de / l0), smoothstep(.3, .6, ne)) : 0.;
      gl_FragColor = vec4(mix(col, ink, e * .92), 1.);
      #include <colorspace_fragment>
    }`;

  Rupaka.block('scene', (b, ctx) => {
    const s = ctx.s, parts = [], specs = Object.fromEntries((b.blocks || []).filter(k => k.type === 'body').map(k => [k.id, k]));
    const ids = new Set(Object.keys(specs)), S = {b, s, ids, bodies: {}, anims: new Map()};
    S.part = (pb, impl, node) => { parts.push({b: pb, impl, node}); return node; };
    S.num = v => typeof v === 'number' ? v : +s.get(v);
    S.vec = (v, d = [0, 0, 0]) => Array.isArray(v) ? v.map((x, i) => { const n = S.num(x); return Number.isFinite(n) ? n : d[i]; }) : d;
    S.step = () => b.bind ? (+s.get(b.bind) || 1) : Infinity;
    const own = pb => ctx.live(pb.after) && (pb.step == null || S.step() >= pb.step) && (pb.show == null || !!s.get(pb.show));
    S.seen = id => !!specs[id] && own(specs[id]) && (!specs[id].in || S.seen(specs[id].in));   // a body and each body that holds it
    S.live = pb => own(pb) && (pb.on == null || S.seen(pb.on));
    S.shotKey = () => parts.find(p => p.b.type === 'shot' && p.b.bind)?.b.bind;
    // A chip: a label in screen space with a leader line to its point. Its text fills {path} from the state.
    S.chip = (pb, tpl, tone) => {
      const t = el('span', {class: 'txt'}), n = el('div', {class: 'rk-chip off', 'data-tone': pb.tone || tone || 'ink'}, t);
      s.on(() => { t.textContent = fmt(tpl, s.st); });
      return n;
    };
    // An animation of one thing (`key`). A new one for the same key takes its place. f(k) gets k from 0 to 1.
    S.anim = (key, ms, f, ease = inout) => {
      if (still() || !ms || !S.T) { S.anims.delete(key); f(1); return; }
      S.anims.set(key, {t0: performance.now(), ms, f, ease, k: 0}); f(0); kick();
    };
    // Show or hide an object: it grows in with a small overshoot, or shrinks out.
    S.show = (P, o, live) => {
      if (P.on === live) return;
      const first = P.on === undefined; P.on = live;
      if (first || !S.T) { o.visible = live; o.scale.setScalar(1); return; }
      o.visible = true;
      if (live) S.anim(o, 420, k => { o.scale.setScalar(Math.max(1e-3, k)); }, settle);
      else S.anim(o, 220, k => { o.scale.setScalar(Math.max(1e-3, 1 - k)); if (k >= 1) o.visible = false; });
    };
    S.point = (on, at) => {
      const v = new S.T.Vector3(...S.vec(at));
      return on ? S.bodies[on].frame.localToWorld(v) : v;
    };

    const c2 = Object.assign(Object.create(ctx), {scene: S});
    const nodes = (b.blocks || []).map(k => R.build(k, c2));
    const cv = el('canvas', {class: 'gl'}), leads = sv('svg', {class: 'leads', 'aria-hidden': 'true'}), chips = el('div', {class: 'chips'});
    const msg = el('p', {class: 'rk-note msg', hidden: true});
    const stage = el('div', {class: 'stage', tabindex: 0, role: 'group', 'aria-roledescription': '3D scene',
                             'aria-label': b.label || 'A 3D scene', style: `height: ${b.height ?? 380}px`}, cv, leads, chips, msg);
    const sr = el('ul', {class: 'rk-sr'});
    nodes.forEach(n => (n.classList.contains('rk-chip') ? chips : sr).append(n));

    const N = b.steps?.length || Math.max(1, ...(b.blocks || []).map(k => k.step || 1));
    const say = el('p', {class: 'say', 'aria-live': 'polite'}), count = el('span', {class: 'count'});
    const go = d => { if (b.bind) { const v = clamp(S.step() + d, 1, N); if (v !== S.step()) ctx.put(b, b.bind, v); } };
    const prev = el('button', {type: 'button', onclick: () => go(-1)}, 'Back', el('kbd', {text: 'A'}));
    const next = el('button', {type: 'button', onclick: () => go(1)}, 'Next', el('kbd', {text: 'D'}));
    const bar = b.bind ? el('div', {class: 'bar'}, prev, count, next) : null;

    const user = {az: 0, el: 0};
    const turn = (daz, del, now) => { user.az += daz; user.el = clamp(user.el + del, -20, 60); if (S.T) aim(frameOf(S.shot), now ? 0 : 260); };
    stage.addEventListener('keydown', e => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const k = e.key.toLowerCase();
      if (k === 'a' || k === 'arrowleft') go(-1);
      else if (k === 'd' || k === 'arrowright') go(1);
      else if (k === 'q') turn(-20, 0); else if (k === 'e') turn(20, 0);
      else if (k === 'w') turn(0, 10); else if (k === 's') turn(0, -10);
      else if (/^[1-9]$/.test(k) && b.bind && +k <= N) ctx.put(b, b.bind, +k);
      else return;
      e.preventDefault();
    });
    let held = null;
    stage.addEventListener('pointerdown', e => { held = [e.clientX, e.clientY]; stage.setPointerCapture(e.pointerId); });
    stage.addEventListener('pointermove', e => {
      if (!held) return;
      turn((e.clientX - held[0]) * .4, (e.clientY - held[1]) * .3, true); held = [e.clientX, e.clientY];
    });
    stage.addEventListener('pointerup', () => { held = null; });

    // three.js parts, made when the library is there.
    let rtM, mask, MW = 96, MH = 48;
    let T, gl, world, cam, post, postCam, rtC, rtN, floor, W = 0, H = 0, raf = 0, sig = '', pal;
    const view = {az: 35, el: 22, fov: 32, dist: 10, tx: 0, ty: 0, tz: 0};
    let tw = null;
    const kick = () => { if (!raf && gl) raf = requestAnimationFrame(frame); };

    function palette() {
      const g = v => R.rgb(stage, v).map(x => x / 255);
      const bg = g('--rk-bg'), fg = g('--rk-fg'), acc = g('--rk-acc'), ok = g('--rk-ok'), no = g('--rk-no');
      const night = lum(bg) < lum(fg), paper = night ? fg : bg, ink = night ? bg : fg;
      const tint = c => mix(c, paper, night ? .3 : .52), deep = c => mix(c, paper, night ? .05 : .15);
      return {night, bg, floor: mix(bg, fg, night ? .1 : .06), shade: mix(ink, [0, 0, 0], .5), line: mix(ink, [0, 0, 0], night ? .7 : .3),
              body: mix(paper, ink, .2), light: mix(paper, [1, 1, 1], .6), dark: mix(paper, ink, .48),
              glass: mix(mix(paper, ink, .45), acc, .12), acc: tint(acc), ok: tint(ok), no: tint(no), up: deep(ok), down: deep(no), side: deep(acc)};
    }
    const mats = {};
    const col = c => new T.Color().setRGB(c[0], c[1], c[2], T.SRGBColorSpace);
    const LIGHT = {value: null};
    S.mat = name => mats[name] ??= new T.ShaderMaterial({uniforms: {color: {value: col(pal[name] || pal.body)}, light: LIGHT},
                                                         vertexShader: TOON_V, fragmentShader: TOON_F});
    function recolor() {
      if (!T) return;
      pal = palette();
      for (const [k, m] of Object.entries(mats)) m.uniforms.color.value = col(pal[k] || pal.body);
      floor.material.uniforms.color.value = col(pal.floor);
      shadow.material.uniforms.color.value = col(pal.shade);
      post.material.uniforms.ink.value = col(pal.line);
      kick();
    }

    // The box of what shows: each visible mesh at its end state (animations at k = 1), without the floor and the shadows.
    const tmp = () => new T.Box3();
    function boxes(o, out = []) {
      o.updateWorldMatrix(true, true);
      o.traverseVisible(m => {
        if (!m.isMesh || m.userData.flat) return;
        m.geometry.boundingBox ?? m.geometry.computeBoundingBox();
        out.push(tmp().copy(m.geometry.boundingBox).applyMatrix4(m.matrixWorld));
      });
      return out;
    }
    const boxOf = o => boxes(o).reduce((a, x) => a.union(x), tmp());
    const corners = bx => [...Array(8)].map((_, i) => new T.Vector3(i & 1 ? bx.max.x : bx.min.x, i & 2 ? bx.max.y : bx.min.y, i & 4 ? bx.max.z : bx.min.z));
    function atEnd(f) {
      const as = [...S.anims.values()];
      as.forEach(a => a.f(1)); const r = f(); as.forEach(a => a.f(a.k));
      return r;
    }
    // The camera for a shot: its angles, and the distance at which what shows fits the view, with a margin for the chips.
    // It fits the corners of the box of each mesh (not one box of all), so a long, thin shape fills the view.
    function frameOf(name) {
      const close = name.startsWith('close:'), p = SHOTS[close ? 'close' : name] || SHOTS.wide;
      const pts = atEnd(() => {
        let bs = close && S.bodies[name.slice(6)] ? boxes(S.bodies[name.slice(6)].outer) : [];
        if (bs.length) bs = [bs.reduce((a, x) => a.union(x), tmp()).expandByScalar(S.size * .1)];   // a close shot keeps some room
        if (!bs.length) bs = boxes(world);
        const out = bs.flatMap(corners);
        if (!close) for (const q of parts) { const a = q.impl.anchor?.(q); if (a && S.live(q.b)) out.push(a); }
        return out;
      });
      if (!pts.length) pts.push(new T.Vector3(-1, -1, -1), new T.Vector3(1, 1, 1));
      const az = p.az + user.az, elv = clamp(p.el + user.el, -10, 89), a = rad(az), e = rad(elv);
      const c = pts.reduce((m, x) => m.add(x), new T.Vector3()).divideScalar(pts.length);
      const dir = new T.Vector3(Math.cos(e) * Math.sin(a), Math.sin(e), Math.cos(e) * Math.cos(a));
      const right = new T.Vector3().crossVectors(new T.Vector3(0, 1, 0), dir).normalize(), up = new T.Vector3().crossVectors(dir, right);
      const tv = Math.tan(rad(p.fov) / 2) * .8, th = tv * (W / H || 1);
      const fit = () => pts.reduce((D, x) => {
        const v = x.clone().sub(c), z = v.dot(dir);
        return Math.max(D, z + Math.abs(v.dot(right)) / th, z + Math.abs(v.dot(up)) / tv);
      }, .1);
      for (let i = 0; i < 2; i++) {   // move the centre to the middle of what shows, then fit again
        const D = fit(), xs = pts.map(x => { const v = x.clone().sub(c), z = D - v.dot(dir); return [v.dot(right) / z, v.dot(up) / z]; });
        const mid = k => (Math.min(...xs.map(q => q[k])) + Math.max(...xs.map(q => q[k]))) / 2;
        c.addScaledVector(right, mid(0) * D).addScaledVector(up, mid(1) * D);
      }
      return {az, el: elv, fov: p.fov, dist: fit(), tx: c.x, ty: c.y, tz: c.z};
    }
    function aim(to, ms) {
      if (still() || !ms || !W) { Object.assign(view, to); tw = null; }
      else tw = {from: {...view}, to, t0: performance.now(), ms};
      kick();
    }
    function place() {
      const a = rad(view.az), e = rad(view.el), size = view.dist;
      cam.fov = view.fov; cam.aspect = W / H || 1;
      cam.position.set(view.tx + size * Math.cos(e) * Math.sin(a), view.ty + size * Math.sin(e), view.tz + size * Math.cos(e) * Math.cos(a));
      cam.up.set(0, 1, 0); cam.lookAt(view.tx, view.ty, view.tz);
      cam.near = Math.max(.01, size - S.size * 3); cam.far = size + S.size * 6;
      cam.updateProjectionMatrix();
    }

    // The contact shadow: draw the parts from under the floor into a small target, blur it two times, and lay it on the floor.
    let shadow, shCam, shRT, shRT2, dark, blur, blurCam;
    function shade() {
      if (b.ground === false) return;
      const flat = [floor, shadow], vis = flat.map(o => o.visible);
      flat.forEach(o => { o.visible = false; });
      world.overrideMaterial = dark; gl.setRenderTarget(shRT); gl.setClearColor(0, 0); gl.clear(); gl.render(world, shCam);
      world.overrideMaterial = null;
      flat.forEach((o, i) => { o.visible = vis[i]; });
      const u = blur.children[0].material.uniforms;
      for (const r of [1.6, .8]) {
        u.map.value = shRT.texture; u.step.value.set(r / 512, 0); gl.setRenderTarget(shRT2); gl.render(blur, blurCam);
        u.map.value = shRT2.texture; u.step.value.set(0, r / 512); gl.setRenderTarget(shRT); gl.render(blur, blurCam);
      }
    }

    // Chips: each one goes to the first free place around its point, and keeps its place while that stays free.
    const DIRS = [-45, -135, 0, 180, 45, 135, -90, 90].map(d => [Math.cos(rad(d)), Math.sin(rad(d))]);
    const hit = (p, q, m) => p.x < q.x + q.w + m && q.x < p.x + p.w + m && p.y < q.y + q.h + m && q.y < p.y + p.h + m;
    function layout() {
      const placed = [], items = [];
      for (const q of parts) {
        if (!q.node.classList.contains('rk-chip')) continue;
        const a = q.node.hidden || !S.live(q.b) ? null : q.impl.anchor?.(q);
        let it = null;
        if (a) {
          const v = a.clone().project(cam);
          if (v.z > -1 && v.z < 1) it = {q, x: (v.x + 1) / 2 * W, y: (1 - v.y) / 2 * H, w: q.node.offsetWidth, h: q.node.offsetHeight};
        }
        if (it && it.w) items.push(it); else off(q);
      }
      const free = (bx, it, dots) => bx.x >= 4 && bx.y >= 4 && bx.x + bx.w <= W - 4 && bx.y + bx.h <= H - 4 && !placed.some(p => hit(bx, p, 6))
        && (!dots || !items.some(o => o !== it && o.x > bx.x - 5 && o.x < bx.x + bx.w + 5 && o.y > bx.y - 5 && o.y < bx.y + bx.h + 5));
      const mid = new T.Vector3(view.tx, view.ty, view.tz).project(cam), mx = (mid.x + 1) / 2 * W, my = (1 - mid.y) / 2 * H;
      for (const it of items) {
        const at = ([dx, dy]) => ({x: it.x + dx - it.w / 2, y: it.y + dy - it.h / 2, w: it.w, h: it.h, d: [dx, dy]});
        const tries = [], ox = it.x - mx, oy = it.y - my, on = Math.hypot(ox, oy) || 1;
        const out = d => (d[0] * ox + d[1] * oy) / on - d[1] * .35;   // away from the middle, and a little up
        const dirs = [...DIRS].sort((p, q) => out(q) - out(p));
        if (it.q.d) tries.push(it.q.d);
        for (const r of [30, 54, 84, 124]) for (const [cx, cy] of dirs) {
          const ext = Math.abs(cx) * it.w / 2 + Math.abs(cy) * it.h / 2;
          tries.push([cx * (r + ext), cy * (r + ext)]);
        }
        // The first free place that covers almost no part; else the free place that covers the least.
        let ok = tries.map(at).filter(x => free(x, it, true));
        if (!ok.length) ok = tries.map(at).filter(x => free(x, it, false));
        const cs = ok.map(cover), i = cs.findIndex(c => c < .08), bx = ok[i >= 0 ? i : cs.indexOf(Math.min(...cs))];
        if (!bx) { off(it.q); continue; }
        placed.push(bx); it.q.d = bx.d;
        it.q.node.style.transform = `translate(${bx.x.toFixed(1)}px, ${bx.y.toFixed(1)}px)`;
        it.q.node.classList.remove('off');
        const ln = it.q.ln ??= leads.appendChild(sv('g', {}, sv('line'), sv('circle', {r: 2.6})));
        const ex = clamp(it.x, bx.x, bx.x + bx.w), ey = clamp(it.y, bx.y, bx.y + bx.h);
        const [l, c] = ln.children;
        l.setAttribute('x1', it.x); l.setAttribute('y1', it.y); l.setAttribute('x2', ex); l.setAttribute('y2', ey);
        c.setAttribute('cx', it.x); c.setAttribute('cy', it.y);
        ln.style.display = '';
      }
    }
    // The share of a box that covers a part, from a small mask of the parts that draw() reads each frame.
    function cover(bx) {
      if (!mask) return 0;
      const sx = MW / W, sy = MH / H, i0 = Math.max(0, Math.floor(bx.x * sx)), i1 = Math.min(MW, Math.ceil((bx.x + bx.w) * sx));
      const j0 = Math.max(0, Math.floor(bx.y * sy)), j1 = Math.min(MH, Math.ceil((bx.y + bx.h) * sy));
      let n = 0, t = 0;
      for (let j = j0; j < j1; j++) for (let i = i0; i < i1; i++) { t++; if (mask[((MH - 1 - j) * MW + i) * 4] > 127) n++; }
      return t ? n / t : 0;
    }
    function off(q) { q.node.classList.add('off'); q.d = null; if (q.ln) q.ln.style.display = 'none'; }

    function frame(now) {
      raf = 0;
      if (!stage.isConnected) { gone(); return; }
      for (const [k, a] of S.anims) {
        a.k = a.ease((now - a.t0) / a.ms); a.f(a.k);
        if (now - a.t0 >= a.ms) S.anims.delete(k);
      }
      if (tw) {
        const k = inout((now - tw.t0) / tw.ms), f = tw.from, t = tw.to, daz = ((t.az - f.az) % 360 + 540) % 360 - 180;
        for (const key of ['el', 'fov', 'dist', 'tx', 'ty', 'tz']) view[key] = f[key] + (t[key] - f[key]) * k;
        view.az = f.az + daz * k;
        if (k >= 1) tw = null;
      }
      draw();
      if (S.anims.size || tw) kick();
      stage.dataset.rkStill = S.anims.size || tw ? '0' : '1';
    }
    function draw() {
      if (!W || !H) return;
      place();
      world.updateMatrixWorld(true);
      for (const q of parts) q.impl.frame?.(q);
      world.updateMatrixWorld(true);
      shade();
      LIGHT.value.set(-.45, .78, .45).normalize();
      const flat = [floor, shadow], vis = flat.map(o => o.visible);
      flat.forEach(o => { o.visible = false; });
      world.overrideMaterial = S.normal; gl.setRenderTarget(rtN); gl.setClearColor(0, 0); gl.clear(); gl.render(world, cam);
      world.overrideMaterial = S.white; gl.setRenderTarget(rtM); gl.setClearColor(0, 1); gl.clear(); gl.render(world, cam);
      gl.readRenderTargetPixels(rtM, 0, 0, MW, MH, mask);
      flat.forEach((o, i) => { o.visible = vis[i]; });
      world.overrideMaterial = null; gl.setRenderTarget(rtC); gl.setClearColor(col(pal.bg), 1); gl.clear(); gl.render(world, cam);
      const u = post.material.uniforms;
      u.near.value = cam.near; u.far.value = cam.far;
      gl.setRenderTarget(null); gl.render(S.pass, postCam);
      layout();
    }
    function gone() { if (gl) { gl.dispose(); gl.forceContextLoss(); gl = null; } }
    function resize() {
      const pr = Math.min(2, devicePixelRatio || 1);
      W = stage.clientWidth; H = stage.clientHeight;
      if (!W || !H || !gl) return;
      gl.setPixelRatio(pr); gl.setSize(W, H, false);
      rtC.setSize(W * pr, H * pr); rtN.setSize(W * pr, H * pr);
      MH = Math.max(8, Math.round(MW * H / W)); rtM.setSize(MW, MH); mask = new Uint8Array(MW * MH * 4);
      post.material.uniforms.texel.value.set(1 / (W * pr), 1 / (H * pr)); post.material.uniforms.w.value = 1.1 * pr;
      aim(frameOf(S.shot), 0);
    }

    function start(lib) {
      T = S.T = lib;
      gl = new T.WebGLRenderer({canvas: cv, antialias: false, preserveDrawingBuffer: true, powerPreference: 'low-power'});
      LIGHT.value = new T.Vector3();
      pal = palette();
      world = new T.Scene(); S.world = world;
      cam = new T.PerspectiveCamera(32, 1, .1, 100);
      S.normal = new T.MeshNormalMaterial(); S.white = new T.MeshBasicMaterial({color: 0xffffff});
      rtM = new T.WebGLRenderTarget(MW, MH);
      for (const q of parts) q.obj = q.impl.make?.(T, q) ?? null;
      world.updateMatrixWorld(true);
      const all = boxOf(world);
      if (all.isEmpty()) all.set(new T.Vector3(-1, -1, -1), new T.Vector3(1, 1, 1));
      S.size = all.getSize(new T.Vector3()).length();
      S.floor = b.floor ?? all.min.y;
      S.unit = S.size / 40;
      const mags = parts.filter(q => q.b.type === 'force').map(q => Math.abs(S.num(q.b.mag))).filter(Number.isFinite);
      S.scale = b.scale ?? (mags.length && Math.max(...mags) ? S.size * .3 / Math.max(...mags) : 1);
      const flatMat = (frag, u) => new T.ShaderMaterial({uniforms: u, vertexShader: FLAT_V, fragmentShader: frag, transparent: true, depthWrite: false});
      floor = new T.Mesh(new T.PlaneGeometry(1, 1), flatMat(FLOOR_F, {color: {value: col(pal.floor)}}));
      floor.rotation.x = -Math.PI / 2; floor.userData.flat = true;
      const c = all.getCenter(new T.Vector3()), r = Math.max(all.max.x - all.min.x, all.max.z - all.min.z, S.size * .5) * 2.4;
      floor.position.set(c.x, S.floor, c.z); floor.scale.set(r, r, 1); floor.visible = b.ground !== false;
      world.add(floor);
      const sr = r * .5, fade = S.size * .35;
      shRT = new T.WebGLRenderTarget(512, 512); shRT2 = new T.WebGLRenderTarget(512, 512);
      shCam = new T.OrthographicCamera(-sr, sr, sr, -sr, 0, fade);
      shCam.position.set(c.x, S.floor, c.z); shCam.rotation.x = Math.PI / 2; shCam.updateMatrixWorld();
      dark = new T.ShaderMaterial({uniforms: {floor: {value: S.floor}, fade: {value: fade}}, vertexShader: DARK_V, fragmentShader: DARK_F, side: T.DoubleSide});
      shadow = new T.Mesh(new T.PlaneGeometry(2 * sr, 2 * sr),
                          flatMat(SHADOW_F, {color: {value: col(pal.shade)}, alpha: {value: .62}, map: {value: shRT.texture}}));
      shadow.rotation.x = -Math.PI / 2; shadow.position.set(c.x, S.floor + S.size * 1e-3, c.z);
      shadow.userData.flat = true; shadow.renderOrder = 1; shadow.visible = b.ground !== false;
      world.add(shadow);
      const quad = new T.Mesh(new T.PlaneGeometry(2, 2), new T.ShaderMaterial({uniforms: {map: {value: null}, step: {value: new T.Vector2()}},
        vertexShader: POST_V, fragmentShader: BLUR_F, depthTest: false, depthWrite: false}));
      quad.frustumCulled = false; blur = new T.Scene(); blur.add(quad); blurCam = new T.OrthographicCamera(-1, 1, 1, -1, 0, 1);
      rtC = new T.WebGLRenderTarget(1, 1, {samples: 4, type: T.HalfFloatType});
      rtN = new T.WebGLRenderTarget(1, 1, {depthTexture: new T.DepthTexture(1, 1)});
      post = new T.Mesh(new T.PlaneGeometry(2, 2), new T.ShaderMaterial({
        uniforms: {tC: {value: rtC.texture}, tN: {value: rtN.texture}, tD: {value: rtN.depthTexture}, texel: {value: new T.Vector2()},
                   w: {value: 1}, near: {value: .1}, far: {value: 100}, ink: {value: col(pal.line)}},
        vertexShader: POST_V, fragmentShader: POST_F, depthTest: false, depthWrite: false}));
      postCam = new T.OrthographicCamera(-1, 1, 1, -1, 0, 1);
      const pass = new T.Scene(); pass.add(post); post.frustumCulled = false; S.pass = pass;
      sync();
      new ResizeObserver(() => { resize(); kick(); }).observe(stage);
      onTheme(() => { if (stage.isConnected) { recolor(); return true; } gone(); return false; });
      stage.dataset.rkGl = 'ready';
    }

    // On each change of the state: the step bar, then each part, then the shot.
    function sync() {
      if (b.bind) {
        const k = S.step();
        count.textContent = `Step ${Math.min(k, N)} of ${N}`;
        prev.disabled = k <= 1 || !ctx.live(b.lock); next.disabled = k >= N || !ctx.live(b.lock);
        if (b.steps) say.textContent = fmt(b.steps[clamp(k, 1, N) - 1], s.st);
      }
      if (!T) return;
      for (const q of parts) { q.impl.sync?.(q, S.live(q.b)); q.node.toggleAttribute('aria-hidden', !S.live(q.b)); }
      // The newest shot wins: a shot that starts to show, or a bound shot whose name changes. When it goes, the last shot that shows wins.
      const shots = parts.filter(q => q.b.type === 'shot');
      for (const q of shots) { const v = S.live(q.b) ? q.impl.name() : null; if (v !== q.was && v != null) S.cur = q; q.was = v; }
      if (!S.cur || !S.live(S.cur.b)) S.cur = shots.findLast(q => S.live(q.b));
      const shot = S.cur?.impl.name(), name = isShot(shot, ids) ? shot : (S.shot || 'wide');
      const now = parts.map(q => S.live(q.b) ? 1 : 0).join('') + name;
      if (now !== sig) {
        const moved = name !== S.shot;
        if (moved) { user.az = 0; user.el = 0; }
        S.shot = name; stage.dataset.rkShot = name;
        aim(frameOf(name), sig ? (moved ? 1300 : 800) : 0);
        sig = now;
      }
      kick();
    }
    s.on(sync);
    (scenes.get(s) || scenes.set(s, []).get(s)).push(S);

    R.need('three').then(lib => {
      try { start(lib); }
      catch (e) { console.error('rupaka: scene', e); msg.hidden = false; msg.textContent = 'This browser cannot draw the 3D view.'; stage.dataset.rkGl = 'error'; }
    }, e => { console.error('rupaka: scene', e); msg.hidden = false; msg.textContent = `The 3D view could not load: ${e.message}`; stage.dataset.rkGl = 'error'; });
    return el('div', {}, R.label(b), stage, bar, b.steps ? say : null, sr);
  });
})();
