import json, sys, base64
from xml.sax.saxutils import escape as E
from reportlab import rl_config; rl_config.useA85 = 0
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle as PS
from reportlab.lib.colors import HexColor as H
W, HT, M = 960, 540, 54
INK, BG, DK, ACC, MU, LN, WH, BL = H('#1d2330'), H('#f6f5f1'), H('#16213a'), H('#d9682b'), H('#5d6675'), H('#e1ded6'), H('#ffffff'), H('#23407a')
THEMES = {'market': ('#16213a', '#d9682b', '#f6f5f1', '#fbe3d4', '#a8441a'), 'competition': ('#10302a', '#1f7a55', '#f1f5f2', '#d6efe2', '#17603f'), 'internship': ('#26173a', '#6a3fa0', '#f5f3f8', '#e8dcf6', '#55308a'), 'news': ('#0b2a33', '#14879b', '#f1f6f7', '#d3edf1', '#0e6575')}
TAGC = {'hi': ('#fbe3d4', '#a8441a'), 'new': ('#d9f0e3', '#1d6b43'), '': ('#e6ecf7', '#23407a')}
def st(sz, c=INK, f='Helvetica', ld=1.3): return PS('x', fontName=f, fontSize=sz, leading=sz*ld, textColor=c)
def lk(u, t=None):
    t = t or u.split('//')[-1].split('/')[0].replace('www.', '')
    return '<a href="%s" color="#23407a">%s</a>' % (E(u, {'"': '&quot;'}), E(t))
def para(c, txt, s, x, ytop, w):
    p = Paragraph(txt, s); _, h = p.wrap(w, 9999); p.drawOn(c, x, ytop - h); return h
def tag(c, x, y, t, kind=''):
    bg, fg = TAGC.get(kind, TAGC['']); w = c.stringWidth(t, 'Helvetica-Bold', 9) + 12
    c.setFillColor(H(bg)); c.roundRect(x, y - 3, w, 15, 7.5, 0, 1); c.setFillColor(H(fg)); c.setFont('Helvetica-Bold', 9); c.drawString(x + 6, y + 1, t); return w
def frame(c, d, s, n):
    c.setFillColor(BG); c.rect(0, 0, W, HT, 0, 1); c.setFillColor(ACC); c.rect(0, HT - 8, W, 8, 0, 1)
    c.setFillColor(ACC); c.setFont('Helvetica-Bold', 10); c.drawString(M, HT - 50, s.get('kicker', '').upper())
    h = para(c, E(s.get('title', '')), st(28, f='Helvetica-Bold', ld=1.1), M, HT - 58, W - 2*M - 120)
    if s.get('tag'): tag(c, W - M - c.stringWidth(s['tag'], 'Helvetica-Bold', 9) - 12, HT - 75, s['tag'], s.get('tagkind', 'hi'))
    c.setFillColor(H('#8a92a0')); c.setFont('Helvetica', 9); c.drawString(M, 22, '%s · %s' % (d['title'], d['period'])); c.drawRightString(W - M, 22, str(n))
    return HT - 70 - h
def card_parts(cd, k):
    out = []
    if cd.get('tag'): out.append('<font name="Helvetica-Bold" size="%.1f" color="%s">%s</font>' % (8*k, TAGC.get(cd.get('tagkind', ''), TAGC[''])[1], E(cd['tag'].upper())))
    out.append(('h', '<b>%s</b>' % E(cd.get('h', ''))))
    for key in ('p', 'm'):
        if cd.get(key): out.append((key, E(cd[key])))
    if cd.get('link'): out.append(('l', lk(cd['link'])))
    return out
def cards(c, s, top):
    if not s.get('cards'): return
    cs = s['cards']; per = len(cs) if len(cs) <= 3 else 2 if len(cs) == 4 else 3
    rows = [cs[i:i+per] for i in range(0, len(cs), per)]; gap = 14; avail = top - 48 - gap*(len(rows)-1)
    cw = (W - 2*M - gap*(per-1)) / per; rh = avail / len(rows)
    for k in [1.6, 1.45, 1.3, 1.18, 1.08, 1, .92, .85, .78, .72, .66]:
        sty = {'h': st(14*k, f='Helvetica-Bold', ld=1.2), 'p': st(11.5*k), 'm': st(11.5*k, MU), 'l': st(10*k)}
        def ht(cd):
            t = 0
            for it in card_parts(cd, k):
                s2 = st(8*k) if isinstance(it, str) else sty[it[0]]; tx = it if isinstance(it, str) else it[1]
                t += Paragraph(tx, s2).wrap(cw - 28, 9999)[1] + 5
            return t + 24
        if all(ht(cd) <= rh for cd in cs): break
    rh = min(rh, max(ht(cd) for cd in cs) + 10); y = top
    for r in rows:
        for i, cd in enumerate(r):
            x = M + i*(cw + gap); c.setFillColor(WH); c.setStrokeColor(LN); c.roundRect(x, y - rh, cw, rh, 9, 1, 1)
            yy = y - 14
            for it in card_parts(cd, k):
                s2 = st(8*k, ld=1.2) if isinstance(it, str) else sty[it[0]]; tx = it if isinstance(it, str) else it[1]
                yy -= para(c, tx, s2, x + 14, yy, cw - 28) + 5
        y -= rh + gap
def bullets(c, s, top):
    for k in [1.5, 1.35, 1.2, 1.08, 1, .92, .85, .78, .7, .64]:
        sty = st(15*k, ld=1.35); tot = sum(Paragraph(E(b), sty).wrap(W - 2*M - 18, 9999)[1] + 8*k for b in s['bullets'])
        if tot <= top - 48: break
    y = top - 6
    for b in s['bullets']:
        c.setFillColor(ACC); c.circle(M + 4, y - 15*k*.62, 3, 0, 1); y -= para(c, E(b), sty, M + 18, y, W - 2*M - 18) + 8*k
def table(c, s, top):
    tw = W - 2*M; wr = s.get('widths') or [1]*len(s['cols']); cw = [tw*w/sum(wr) for w in wr]
    for k in [1.5, 1.35, 1.2, 1.08, 1, .92, .85, .78, .72, .66, .6]:
        hs, bs = st(9*k, MU, 'Helvetica-Bold'), st(11*k, ld=1.25)
        cell = lambda v, sty: Paragraph(lk(v) if isinstance(v, str) and v.startswith('http') else E(str(v)), sty)
        data = [[cell(v.upper(), hs) for v in s['cols']]] + [[cell(v, bs) for v in r] for r in s['rows']]
        t = Table(data, colWidths=cw); t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), H('#ecebe5')), ('BACKGROUND', (0, 1), (-1, -1), WH), ('LINEBELOW', (0, 0), (-1, -1), .5, H('#ecebe5')), ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('TOPPADDING', (0, 0), (-1, -1), 6*k), ('BOTTOMPADDING', (0, 0), (-1, -1), 6*k), ('LEFTPADDING', (0, 0), (-1, -1), 9), ('RIGHTPADDING', (0, 0), (-1, -1), 9)]))
        _, h = t.wrap(tw, 9999)
        if h <= top - 48: break
    t.drawOn(c, M, top - 6 - h)
def sources(c, s, top):
    items = s['links']; half = (len(items) + 1) // 2; k = 1.3 if len(items) <= 14 else 1 if len(items) <= 24 else .8
    for col, part in enumerate([items[:half], items[half:]]):
        y = top - 6
        for it in part: y -= para(c, lk(it['u'], it.get('t')), st(10*k), M + col*(W/2 - M + 10), y, W/2 - M - 20) + 4*k
def cover(c, d):
    c.setFillColor(DK); c.rect(0, 0, W, HT, 0, 1); c.setFillColor(ACC); c.rect(M, 330, 40, 4, 0, 1)
    c.setFillColor(H(TAGC['hi'][0])); c.setFont('Helvetica-Bold', 11); c.drawString(M, 350, d['title'].upper())
    c.setFillColor(H('#eef1f6')); c.setFont('Helvetica-Bold', 54); c.drawString(M, 270, d['period'])
    y = 240 - para(c, E(d.get('subtitle', '')), st(15, H('#a9b3c6')), M, 240, W - 2*M) - 22
    para(c, E(d.get('topline', '')), st(17, H('#eef1f6'), ld=1.4), M, y, W - 2*M - 120)
def statement(c, d, s, n):
    c.setFillColor(ACC); c.rect(0, 0, W, HT, 0, 1); c.setFillColor(WH); c.setFont('Helvetica-Bold', 10); c.drawString(M, HT - 50, s.get('kicker', '').upper())
    para(c, E(s['text']), st(30, WH, 'Helvetica-Bold', 1.2), M, HT - 90, W - 2*M - 80)
    c.setFont('Helvetica', 9); c.drawRightString(W - M, 22, str(n))
raw = open(sys.argv[1], encoding='utf-8').read()
for a, b in [('→', '->'), ('←', '<-'), ('≈', '~'), ('≥', '>='), ('≤', '<='), ('−', '-'), ('✓', 'Yes'), ('×', 'x')]: raw = raw.replace(a, b)
d = json.loads(raw); th = THEMES.get(d.get('theme'), THEMES['market']); DK, ACC, BG = H(th[0]), H(th[1]), H(th[2]); TAGC['hi'] = (th[3], th[4])
c = Canvas(sys.argv[2], pagesize=(W, HT)); c.setTitle('%s — %s' % (d['title'], d['period']))
cover(c, d); c.showPage()
for n, s in enumerate(d['slides'], 2):
    if s['type'] == 'statement': statement(c, d, s, n)
    else: {'cards': cards, 'bullets': bullets, 'table': table, 'sources': sources}[s['type']](c, s, frame(c, d, s, n))
    c.showPage()
c.save(); open(sys.argv[2] + '.b64', 'w').write(base64.b64encode(open(sys.argv[2], 'rb').read()).decode())
print('pages', len(d['slides']) + 1)
