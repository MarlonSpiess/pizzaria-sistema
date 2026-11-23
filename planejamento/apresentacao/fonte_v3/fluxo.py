"""Fluxogramas em grade: nós posicionados por coluna e linha, setas cortadas na borda de cada nó."""
from lib import *

ESTILO = {  # fundo, borda, texto, tracejado
    'ini': (DARK, DARK, '#FAF6EF', None),
    'passo': ('#FFFFFF', RED, INK, None),
    'dec': (GOLD, DARK, DARK, None),
    'fim': (GREEN, GREEN, '#FFFFFF', None),
    'pend': (CREAM, SLATE, SLATE, '10 7'),
    'obra': ('#FFF4E0', GOLD, INK, '10 7'),
    'alerta': ('#FBE9E3', RED, RED, None),
}


class Fluxo:
    def __init__(self, cols, rows, w=1664, h=760, bw=230, bh=92, mx=None, my=None):
        self.W, self.H, self.bw, self.bh = w, h, bw, bh
        self.cols, self.rows = cols, rows
        self.mx = mx if mx is not None else bw / 2 + 10
        self.my = my if my is not None else bh / 2 + 10
        self.nos, self.arestas, self.extra = {}, [], ''

    def pos(self, c, r):
        cw = (self.W - 2 * self.mx) / max(1, self.cols - 1)
        rh = (self.H - 2 * self.my) / max(1, self.rows - 1)
        return self.mx + c * cw, self.my + r * rh

    def no(self, id_, c, r, texto, tipo='passo', w=None, h=None, fs=20):
        x, y = self.pos(c, r)
        self.nos[id_] = (x, y, w or self.bw, h or self.bh, texto, tipo, fs)

    def seta(self, a, b, rotulo=None, tracejado=False, cor=INK, via=None, lx=None, ly=None):
        self.arestas.append((a, b, rotulo, tracejado, cor, via, lx, ly))

    def _borda(self, n, tx, ty):
        x, y, w, h, _, tipo, _ = n
        dx, dy = tx - x, ty - y
        if dx == 0 and dy == 0:
            return x, y
        if tipo == 'dec':
            k = 1 / (abs(dx) / (w / 2) + abs(dy) / (h / 2))
        else:
            k = min((w / 2 + 4) / abs(dx) if dx else 1e9, (h / 2 + 4) / abs(dy) if dy else 1e9)
        return x + dx * k, y + dy * k

    def svg(self):
        corpo = ''
        for a, b, rot, tr, cor, via, lx, ly in self.arestas:
            na, nb = self.nos[a], self.nos[b]
            pts = via or []
            p1 = pts[0] if pts else (nb[0], nb[1])
            p2 = pts[-1] if pts else (na[0], na[1])
            x1, y1 = self._borda(na, *p1)
            x2, y2 = self._borda(nb, *p2)
            mx_, my_ = ((x1 + x2) / 2, (y1 + y2) / 2) if not pts else pts[len(pts) // 2]
            corpo += arrow(x1, y1, x2, y2, cor, dash='9 7' if tr else None, mid=pts or None, label=rot,
                           lx=lx if lx is not None else mx_, ly=ly if ly is not None else my_, fs=17, lw=260)
        for id_, (x, y, w, h, t, tipo, fs) in self.nos.items():
            fundo, borda, cor, dash = ESTILO[tipo]
            if tipo == 'dec':
                corpo += diamond(x, y, w, h, t, fill=fundo, stroke=borda, color=cor, fs=fs)
            else:
                corpo += box(x - w / 2, y - h / 2, w, h, t, fill=fundo, stroke=borda, color=cor, fs=fs,
                             weight=700 if tipo in ('ini', 'fim') else 500, dash=dash)
        return svg(self.W, self.H, corpo + self.extra)


def legenda():
    itens = [('passo', 'Etapa'), ('dec', 'Decisão'), ('fim', 'Fim'), ('pend', 'Pendente da API')]
    s = '<div style="display:flex;gap:30px;font-size:22px;color:#5E534A;margin-top:10px">'
    for tipo, nome in itens:
        fundo, borda, _, dash = ESTILO[tipo]
        estilo = 'dashed' if dash else 'solid'
        forma = 'transform:rotate(45deg);width:20px;height:20px' if tipo == 'dec' else 'width:34px;height:22px;border-radius:5px'
        s += f'<span style="display:flex;align-items:center;gap:10px"><span style="display:inline-block;{forma};background:{fundo};border:2px {estilo} {borda}"></span>{nome}</span>'
    return s + '</div>'
