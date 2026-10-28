/* rupaka core: a demo is a JSON spec of blocks over one small state. Named fns compute derived values.
   No network, no eval, no dependencies. Blocks and fns register with Rupaka.block and Rupaka.fn; boot.js mounts every [data-rupaka]. */
(() => {
  if (window.Rupaka && window.Rupaka.core) return;   // the bundle came in twice (an htmx swap): keep the first copy
  const R = window.Rupaka = {blocks: {}, fns: {}, core: true, version: '0.0.1', schema: 1};
  const NS = 'http://www.w3.org/2000/svg', BAD = new Set(['__proto__', 'prototype', 'constructor']);

  function attrs(e, a) {
    for (const [k, v] of Object.entries(a || {})) {
      if (v == null || v === false) continue;
      if (k.startsWith('on') && typeof v === 'function') e.addEventListener(k.slice(2), v);
      else if (k === 'text') e.textContent = v;
      else e.setAttribute(k, v === true ? '' : v);
    }
  }
  const kids = ks => ks.flat(9).filter(k => k != null && k !== false);
  const el = (tag, a, ...ks) => { const e = document.createElement(tag); attrs(e, a); e.append(...kids(ks)); return e; };
  const sv = (tag, a, ...ks) => { const e = document.createElementNS(NS, tag); attrs(e, a); e.append(...kids(ks)); return e; };

  // A path such as `fused.0.id` reads into lists and objects. Only own keys, so `constructor` and `__proto__` give nothing.
  const get = (o, path) => String(path).split('.').reduce((x, k) => x == null || BAD.has(k) || !Object.hasOwn(Object(x), k) ? undefined : x[k], o);
  const show = (v, d) => v == null ? '' : typeof v === 'number' ? String(+v.toFixed(d ?? 4)).replace('-', '−') : Array.isArray(v) ? v.join(', ') : String(v);
  // `{path}` or `{path:2}` (two digits) take a value from the state. Text goes in with textContent, never as HTML.
  const fmt = (s, st) => String(s ?? '').replace(/\{([\w.]+)(?::(\d))?\}/g, (_, p, d) => show(get(st, p), d == null ? null : +d));
  const hide = (n, h) => { if (n instanceof SVGElement) n.style.display = h ? 'none' : ''; else n.hidden = h; };

  Object.assign(R, {el, sv, get, fmt, show, hide, block: (name, f) => { R.blocks[name] = f; }, fn: (name, f) => { R.fns[name] = f; }});
  R.label = (b, ...more) => b.label ? el('span', {class: 'rk-lbl', text: b.label}, ...more) : null;

  function store(spec) {
    const st = structuredClone(spec.state || {}), subs = [];
    st.gate = {};
    const derive = () => (spec.derive || []).forEach(d => {
      const f = R.fns[d.fn];
      if (!f) throw new Error(`unknown fn "${d.fn}"`);
      st[d.out] = f(d, st, spec);
    });
    derive();
    const s = {st, spec, derive, get: p => get(st, p), on: f => { subs.push(f); },
               emit: k => subs.forEach(f => f(k)),
               set(k, v) { st[k] = v; derive(); s.emit(k); }};
    return s;
  }

  function build(b, ctx) {
    const f = R.blocks[b.type];
    if (!f) throw new Error(`unknown block "${b.type}"`);
    const node = f(b, ctx);
    node.classList.add('rk-b', `rk-${b.type}`);
    node.setAttribute('data-rk-type', b.type);
    if (b.after) node.setAttribute('data-rk-after', b.after);
    if (b.lock) node.setAttribute('data-rk-lock', b.lock);
    if (b.after) { const sync = () => hide(node, !ctx.live(b.after)); ctx.s.on(sync); sync(); }
    if (b.lock && !(node instanceof SVGElement)) {
      const note = el('div', {class: 'rk-note rk-locknote', text: 'Locked until you lock in your prediction.'});
      node.append(note);
      const sync = () => { const l = !ctx.live(b.lock); node.classList.toggle('rk-locked', l); note.hidden = !l; };
      ctx.s.on(sync); sync();
    }
    return node;
  }

  R.build = build;
  R.mount = (host, spec) => {
    if (!spec || typeof spec !== 'object' || Array.isArray(spec)) throw new Error('the spec is not an object');
    const v = spec.rupaka ?? R.schema;
    if (!(v === R.schema || v === R.schema - 1)) throw new Error(`schema ${v} is not supported; this runtime draws ${R.schema - 1} and ${R.schema}`);
    const s = store(spec), root = el('div', {class: 'rk', 'data-rk': spec.id || ''});
    const ctx = {s, spec, root, live: g => !g || s.get(`gate.${g}`) === 'done'};
    ctx.build = b => build(b, ctx);
    ctx.put = (b, k, val) => { if (!ctx.live(b.lock)) return false; s.set(k, val); return true; };   // a locked control refuses
    if (spec.title) root.append(el('h3', {class: 'rk-title', text: spec.title}));
    if (spec.ask) root.append(el('p', {class: 'rk-ask', text: spec.ask}));
    root.append(...(spec.blocks || []).map(ctx.build));
    root.addEventListener('keydown', e => {   // ⌘↩ anywhere in the demo locks in the first open gate
      if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && ctx.commit) { e.preventDefault(); ctx.commit(); }
    });
    host.replaceChildren(root);
    s.emit('*');
    root.dataset.rkReady = host.dataset.rkReady = '1';
    host.rupaka = s;
    return s;
  };

  // The gate tells the page about each prediction; the event crosses a shadow root. It gives false when a listener called preventDefault.
  R.predict = (ctx, detail) => ctx.root.dispatchEvent(new CustomEvent('rk-predict', {bubbles: true, composed: true, cancelable: true, detail: {demo: ctx.spec.id, ...detail}}));

  R.boot = (scope = document) => scope.querySelectorAll('[data-rupaka]:not([data-rk-ready])').forEach(n => {
    const src = n.querySelector('script[type="application/json"]');
    try { R.mount(n, JSON.parse(src ? src.textContent : n.dataset.rupaka)); }
    catch (e) { console.error('rupaka:', e); n.dataset.rkReady = 'error'; n.replaceChildren(el('p', {class: 'rk-err', text: `This demo could not draw: ${e.message}`})); }
  });
})();
