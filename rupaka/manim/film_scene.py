"The film scene: it draws a rupaka film plan. It reads only data from the plan file, and it uses no LaTeX."
import json, os, textwrap
from manimlib import *

P = json.load(open(os.environ['RUPAKA_PLAN']))
C, FONT = P['colors'], P.get('font') or ''
W, H = 12.6, 4.9          # the figure area, in frame units
TOP, LOW = 3.05, -3.15    # the y of the heading and of the subtitle

def txt(s, size=28, color=None, wrap=None, weight=NORMAL, font=None):
    s = str(s)
    if wrap: s = '\n'.join(textwrap.wrap(s, wrap)) or ' '
    return Text(s or ' ', font=font or FONT, font_size=size, color=color or C['fg'], weight=weight)

def fit(m, w, h):
    if m.get_width() > w: m.set_width(w)
    if m.get_height() > h: m.set_height(h)
    return m

def num(v, d=2):
    v = round(v, d)
    return str(int(v)) if v == int(v) else f'{v:.{d}f}'.rstrip('0')

def box(m, color=None, buff=.18, fill=None):
    r = RoundedRectangle(width=m.get_width() + 2 * buff, height=m.get_height() + 2 * buff, corner_radius=.12)
    r.set_stroke(color or C['line'], 2).set_fill(fill or C['bg'], 1 if fill else 0).move_to(m)
    return VGroup(r, m)

def labeled(g, label):
    return VGroup(txt(label, 22, C['mute']), g).arrange(DOWN, buff=.2) if label else g

# --- one builder for each figure kind
def axis(f):
    xs, ys = f['x'], f['y']
    ax = Axes(x_range=(xs[0], xs[1], f.get('xstep') or 1), y_range=(ys[0], ys[1], f.get('ystep') or 1), width=8.5, height=4.2,
              axis_config=dict(stroke_color=C['line'], stroke_width=2, include_tip=False))
    g = VGroup(ax)
    for x in range(int(xs[0]), int(xs[1]) + 1, int(f.get('xstep') or 1) or 1):
        if x: g.add(txt(x, 16, C['mute']).next_to(ax.c2p(x, 0), DOWN, buff=.12))
    for y in range(int(ys[0]), int(ys[1]) + 1, int(f.get('ystep') or 1) or 1):
        if y: g.add(txt(y, 16, C['mute']).next_to(ax.c2p(0, y), LEFT, buff=.12))
    g.add(txt(f.get('xlabel', ''), 22, C['mute']).next_to(ax.c2p(xs[1], 0), RIGHT, buff=.15))
    g.add(txt(f.get('ylabel', ''), 22, C['mute']).next_to(ax.c2p(0, ys[1]), UP, buff=.12))
    for p in f['plots']:
        segs, cur = [], []
        for x, y in p['pts']:
            if ys[0] <= y <= ys[1]: cur.append(ax.c2p(x, y))
            elif cur: segs.append(cur); cur = []
        segs += [cur] if cur else []
        for s in segs:
            if len(s) > 1: g.add(VMobject().set_points_smoothly(s).set_stroke(C['acc'], 5))
    for p in f['points']:
        d = Dot(ax.c2p(p['x'], p['y']), radius=.11, fill_color=C['warm'])
        g.add(d, txt(f"{p['label']} ({num(p['x'])}, {num(p['y'])})" if p['label'] else '', 20, C['warm']).next_to(d, DR, buff=.1))
    return labeled(g, f.get('label', ''))

def bars(f):
    items, d = f['items'], f.get('digits', 2)
    top = f.get('max') or max([abs(v) for _, v, _ in items] + [1e-9])
    rows = VGroup()
    for lab, v, parts in items:
        w = max(.02, 6.5 * abs(v) / top)
        segs = VGroup(*[Rectangle(width=max(.01, w * p / v) if v else .01, height=.42) for p in parts]) if parts and v else VGroup(Rectangle(width=w, height=.42))
        for i, s in enumerate(segs): s.set_stroke(width=0).set_fill([C['acc'], C['warm'], C['ok']][i % 3], 1)
        segs.arrange(RIGHT, buff=0)
        r = VGroup(txt(lab, 24).set_width(1.4, stretch=False) if len(lab) > 9 else txt(lab, 24), segs, txt(num(v, d), 22, C['mute'])).arrange(RIGHT, buff=.25)
        r[1].align_to(r[0], LEFT).shift(RIGHT * 1.6); r[2].next_to(r[1], RIGHT, buff=.2)
        rows.add(r)
    rows.arrange(DOWN, buff=.22, aligned_edge=LEFT)
    if f.get('parts'):
        key = VGroup(*[VGroup(Square(.22).set_fill([C['acc'], C['warm'], C['ok']][i % 3], 1).set_stroke(width=0), txt(t, 18, C['mute'])).arrange(RIGHT, buff=.1)
                       for i, t in enumerate(f['parts'])]).arrange(RIGHT, buff=.4)
        rows = VGroup(rows, key).arrange(DOWN, buff=.3, aligned_edge=LEFT)
    return labeled(rows, f.get('label', ''))

def grid(f):
    cells = VGroup()
    for r in f['rows']:
        cells.add(VGroup(*[box(txt(num(v), 26), buff=.25) for v in r]).arrange(RIGHT, buff=.12))
    cells.arrange(DOWN, buff=.12)
    if f.get('cols') and len(f['rows']) == 1:
        cells = VGroup(VGroup(*[txt(c, 20, C['mute']).next_to(cell, UP, buff=.1) for c, cell in zip(f['cols'], cells[0])]), cells)
    return labeled(cells, f.get('label', ''))

def pixels(f):
    rows = f['rows']; flat = [v for r in rows for v in r] or [0]
    lo, hi = f.get('lo', min(flat)), f.get('hi', max(flat))
    n = max(len(rows), max(len(r) for r in rows) if rows else 1); s = 4. / n
    g = VGroup()
    for i, r in enumerate(rows):
        for j, v in enumerate(r):
            t = 0 if hi == lo else min(1, max(0, (v - lo) / (hi - lo)))
            g.add(Square(s).set_stroke(width=0).set_fill(interpolate_color(C['bg'], C['fg'], t), 1).move_to([j * s, -i * s, 0]))
    return labeled(VGroup(Square(n * s).set_stroke(C['line'], 2).move_to(g), g), f.get('label', ''))

def wheel(f):
    items, R = f['items'], 2.2
    n, many = len(items) or 1, len(items) > 12
    def at(deg, r): a = np.radians(90 - deg); return np.array([r * np.cos(a), r * np.sin(a), 0])
    hot = f.get('pick') if f.get('angle') is None else int(f['angle'] % 360 // (360 / n))
    g = VGroup()
    if hot is not None:
        g.add(AnnularSector(inner_radius=R * .62, outer_radius=R, angle=-TAU / n, start_angle=PI / 2 - TAU * hot / n).set_fill(C['acc'], .35).set_stroke(width=0))
    g.add(Circle(radius=R).set_stroke(C['line'], 3), Circle(radius=R * .62).set_stroke(C['line'], 2))
    for i, it in enumerate(items):
        g.add(Line(at(360 * i / n, R * .62), at(360 * i / n, R)).set_stroke(C['line'], 2))
        if not many or i == hot: g.add(txt(it, 20 if not many else 16, C['fg'] if i == hot else C['mute']).move_to(at(360 * (i + .5) / n, R * .81)))
        for m in range(1, f.get('marks') or 0):
            g.add(Line(at(360 * (i + m / f['marks']) / n, R * .9), at(360 * (i + m / f['marks']) / n, R)).set_stroke(C['acc'], 2))
    if f.get('outer'):
        k = len(f['outer']); g.add(Circle(radius=R * 1.24).set_stroke(C['line'], 2))
        for i, it in enumerate(f['outer']):
            g.add(Line(at(360 * i / k, R), at(360 * i / k, R * 1.24)).set_stroke(C['line'], 2))
            g.add(txt(it, 15, C['mute']).move_to(at(360 * (i + .5) / k, R * 1.12)))
    if f.get('angle') is not None:
        g.add(Line(ORIGIN, at(f['angle'], R * .95)).set_stroke(C['warm'], 5), Dot(at(f['angle'], R * .95), radius=.09, fill_color=C['warm']),
              txt(f"{num(f['angle'], 1)}°", 26, C['warm']).move_to(DOWN * .45), txt(items[hot], 20, C['fg']).move_to(DOWN * .85))
    elif hot is not None: g.add(txt(items[hot], 40, C['warm'], weight=BOLD))
    return labeled(g, f.get('label', ''))

def ranks(f):
    g = VGroup(*[VGroup(txt(i + 1, 22, C['mute']), txt(x, 28)).arrange(RIGHT, buff=.3) for i, x in enumerate(f['items'])]).arrange(DOWN, buff=.2, aligned_edge=LEFT)
    return labeled(box(g, buff=.3), f.get('label', ''))

def pair(f):
    cells = VGroup(*[box(txt(c, 30), C['acc'], .22) for c in f['cells']]).arrange(RIGHT, buff=.15)
    out = box(txt(f['to'], 30, C['warm']), C['warm'], .22)
    g = VGroup(cells, Arrow(LEFT, RIGHT, stroke_color=C['mute']).set_width(1.1), out).arrange(RIGHT, buff=.3)
    if f.get('heads'):
        hs = f['heads']
        g = VGroup(VGroup(txt(hs[0], 20, C['mute']).next_to(cells, UP, buff=.15), txt(hs[-1], 20, C['mute']).next_to(out, UP, buff=.15)), g)
    return g

def flow(f):
    nodes = [box(txt(t, 26), C['acc'], .25) for t in f['nodes']]
    g = VGroup(*nodes)
    if f.get('layout') == 'cycle':
        n = len(nodes)
        for i, m in enumerate(nodes): m.move_to(1.7 * np.array([np.sin(TAU * i / n), np.cos(TAU * i / n), 0]))
    else: g.arrange(RIGHT, buff=1.1)
    at = dict(zip(f['ids'], nodes))
    arrows = VGroup(*[Arrow(at[a].get_center(), at[b].get_center(), buff=.75, stroke_color=C['mute'], stroke_width=4)
                      for a, b in f['edges'] if a in at and b in at])
    return VGroup(g, arrows)

def text(f):
    t = txt(f['text'], 34 if f.get('big') else 26, C['fg'], wrap=46)
    return labeled(box(t, buff=.3), f.get('label', '')) if f.get('big') else t

def knob(f):
    lo, hi, v = f['lo'], f['hi'], f['value']
    line = Line(LEFT * 2, RIGHT * 2).set_stroke(C['line'], 6)
    t = 0 if hi == lo else min(1, max(0, (v - lo) / (hi - lo)))
    dot = Dot(line.point_from_proportion(t), radius=.14, fill_color=C['acc'])
    return VGroup(txt(f"{f['label']} = {f['text']}", 24), VGroup(line, dot)).arrange(DOWN, buff=.2)

def chip(f): return box(txt(f"{f['label']}: {f['text']}", 24), C['line'], .2)

def row(f): return VGroup(*map(build, f['items'])).arrange(RIGHT, buff=.8, aligned_edge=UP)
def stack(f): return VGroup(*map(build, f['items'])).arrange(DOWN, buff=.4)

KINDS = dict(axis=axis, bars=bars, grid=grid, pixels=pixels, ranks=ranks, pair=pair, flow=flow, text=text, knob=knob, chip=chip, wheel=wheel, row=row, stack=stack)
def build(f): return KINDS[f['k']](f)

def frame(fs, h=H, w=W, y=0):
    "One figure list as one group, in the figure area."
    if not fs: return VGroup()
    g = VGroup(*map(build, fs)).arrange(DOWN, buff=.45)
    return fit(g, w, h).move_to(UP * y)

class Film(Scene):
    def head(self, s):
        return fit(txt(s, 34, C['fg'], wrap=60, weight=BOLD), 12.8, 1.2).move_to(UP * TOP)

    def sub(self, s):
        return fit(txt(s, 22, C['mute'], wrap=96), 12.8, .9).move_to(UP * LOW)

    def swap(self, old, new, t=.8):
        "Replace `old` with `new`: a morph when both are there, else a fade."
        if len(old) and len(new): self.play(FadeTransform(old, new), run_time=t)
        else:
            if len(old): self.play(FadeOut(old), run_time=t / 2)
            if len(new): self.play(FadeIn(new, shift=RIGHT * .3), run_time=t / 2)
        return new

    def opts(self, os_, pick=None):
        def tick(o): return pick is not None and o.strip().lower() == str(pick).strip().lower()
        rows = [VGroup(txt(i + 1, 24, C['acc'], weight=BOLD), txt(o, 24, C['ok'] if tick(o) else C['fg'])).arrange(RIGHT, buff=.3)
                for i, o in enumerate(os_)]
        g = VGroup(*rows).arrange(DOWN, buff=.25, aligned_edge=LEFT)
        for r, o in zip(rows, os_):
            if tick(o): g.add(SurroundingRectangle(r, buff=.12, color=C['ok'], stroke_width=3))
        return box(g, C['line'], .35)

    def countdown(self, n):
        ring = Circle(radius=.42).set_stroke(C['warm'], 6)
        g = VGroup(ring, txt('Pause and predict', 20, C['warm'])).arrange(DOWN, buff=.15).to_corner(DR, buff=.6).shift(UP * .7)
        self.play(FadeIn(g), run_time=.3)
        for i in range(n, 0, -1):
            d = txt(i, 30, C['warm']).move_to(ring)
            self.add(d); self.play(Uncreate(ring.copy(), lag_ratio=0), run_time=1); self.remove(d)
        self.play(FadeOut(g), run_time=.3)
        return n + .6

    def construct(self):
        fig, hd, sb, op = VGroup(), VGroup(), VGroup(), VGroup()
        for b in P['beats']:
            used, k = 0., b['kind']
            nh, ns = self.head(b['head']), self.sub(b['say'])
            anims = []
            if b['head'] != getattr(self, '_h', None):
                anims += [FadeOut(hd), Write(nh, run_time=1)] if k == 'title' else [FadeOut(hd), FadeIn(nh)]
                hd = nh; self._h = b['head']
            anims += [FadeOut(sb), FadeIn(ns)]; sb = ns
            self.play(*anims, run_time=1); used += 1
            side = k in ('ask', 'reveal') and b.get('opts')
            if k == 'move':
                frames = [frame(fs, w=W * .62 if len(op) else W).shift(LEFT * 2.6 * bool(len(op))) for fs in b['frames']]
                fig = self.swap(fig, frames[0], .6); used += .6
                hold = fig.copy(); self.remove(fig); self.add(hold)
                run = max(1.5, b['secs'] - used - .5)
                self.play(UpdateFromAlphaFunc(hold, lambda m, a: m.become(frames[min(len(frames) - 1, int(a * len(frames)))])), run_time=run, rate_func=linear)
                fig = hold; used += run
            else:
                nf = frame(b['frames'][-1], w=W * .62 if side else W).shift(LEFT * 2.6 * bool(side))
                fig = self.swap(fig, nf, 1); used += 1
            if side:
                no = self.opts(b['opts'], b.get('pick')).to_edge(RIGHT, buff=.6)
                if len(op): self.play(FadeTransform(op, no), run_time=.8)
                else: self.play(FadeIn(no, shift=LEFT * .3), run_time=.8)
                op = no; used += .8
            elif len(op) and k != 'move': self.play(FadeOut(op), run_time=.5); op = VGroup(); used += .5
            if k == 'ask': used += self.countdown(3)
            self.wait(max(.2, b['secs'] - used))
        self.play(*map(FadeOut, (fig, hd, sb, op)), run_time=1)
