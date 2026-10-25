/* expr: a formula in a tiny safe grammar: numbers, names, + - * / ^, parentheses, and the functions
   sin cos tan exp log sqrt abs min max floor ceil round. Names are state keys; `over: {x: [min, max, n]}` gives a series of {x, y}.
   There is no eval: the text is parsed to a tree, and only own state keys can be read. */
(() => {
  const FN = {sin: Math.sin, cos: Math.cos, tan: Math.tan, exp: Math.exp, log: Math.log, sqrt: Math.sqrt, abs: Math.abs,
              min: Math.min, max: Math.max, floor: Math.floor, ceil: Math.ceil, round: Math.round};
  const K = {pi: Math.PI, e: Math.E}, OPS = {'×': '*', '÷': '/', '−': '-', '**': '^'};
  const lex = src => {
    const out = [], re = /\s*(?:(\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+)|([A-Za-z_]\w*)|(\*\*|[-+*/^(),×÷−]))/y, s = String(src);
    let i = 0;
    while (i < s.length) {
      if (!s.slice(i).trim()) break;
      re.lastIndex = i;
      const m = re.exec(s);
      if (!m) throw new Error(`expr: "${s}" has a bad character at ${i}`);
      i = re.lastIndex;
      out.push(m[1] != null ? {t: 'n', v: +m[1]} : m[2] != null ? {t: 'id', v: m[2]} : {t: 'op', v: OPS[m[3]] || m[3]});
    }
    return out;
  };
  const parse = src => {
    const ts = lex(src); let p = 0;
    const peek = () => ts[p], eat = v => { const t = ts[p]; if (!t || (v && t.v !== v)) throw new Error(`expr: "${src}" needs ${v || 'more'}`); p++; return t; };
    const binl = (next, ops) => () => { let a = next(); while (peek()?.t === 'op' && ops.includes(peek().v)) { const o = eat().v, l = a, r = next(); a = o === '+' ? e => l(e) + r(e) : o === '-' ? e => l(e) - r(e) : o === '*' ? e => l(e) * r(e) : e => l(e) / r(e); } return a; };
    const atom = () => {
      const t = eat();
      if (t.t === 'n') return () => t.v;
      if (t.t === 'op' && t.v === '(') { const a = add(); eat(')'); return a; }
      if (t.t === 'id') {
        if (t.v.startsWith('_') || ['constructor', 'prototype'].includes(t.v)) throw new Error(`expr: the name "${t.v}" is not allowed`);
        if (peek()?.v === '(') {
          if (!Object.hasOwn(FN, t.v)) throw new Error(`expr: no function "${t.v}"`);
          eat('('); const args = [add()]; while (peek()?.v === ',') { eat(','); args.push(add()); } eat(')');
          const f = FN[t.v]; return e => f(...args.map(a => a(e)));
        }
        if (Object.hasOwn(K, t.v)) return () => K[t.v];
        return e => { if (!Object.hasOwn(e, t.v)) throw new Error(`expr: no value "${t.v}"`); return +e[t.v]; };
      }
      throw new Error(`expr: "${src}" has an unexpected "${t.v}"`);
    };
    const pow = () => { const a = atom(); if (peek()?.v === '^') { eat('^'); const b = unary(); return e => a(e) ** b(e); } return a; };
    const unary = () => { if (peek()?.v === '-') { eat('-'); const a = unary(); return e => -a(e); } if (peek()?.v === '+') { eat('+'); return unary(); } return pow(); };
    const mul = binl(unary, ['*', '/']), add = binl(mul, ['+', '-']);
    const f = add();
    if (p < ts.length) throw new Error(`expr: "${src}" has extra text at "${ts[p].v}"`);
    return f;
  };
  const cache = {};
  Rupaka.expr = parse;
  Rupaka.fn('expr', (d, st) => {
    const f = cache[d.expr] ||= parse(d.expr);
    if (!d.over) return f(st);
    const [name, [lo, hi, n = 101]] = Object.entries(d.over)[0];
    return Array.from({length: n}, (_, i) => { const x = lo + (hi - lo) * i / (n - 1); return {x, y: f({...st, [name]: x})}; });
  });
})();
