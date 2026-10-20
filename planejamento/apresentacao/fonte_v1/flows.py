from lib import *

W = 1664


def flow_map():
    b = ''
    b += f'<rect x="0" y="0" width="{W}" height="72" rx="14" fill="{DARK}"/>'
    b += f'<text x="28" y="45" font-size="30" fill="{GOLD}" font-weight="700" class="os">NÚCLEO</text>'
    b += f'<text x="190" y="44" font-size="21" fill="#D8CFC4" class="dm">Usuários e perfis, parâmetros da loja, cadastros (itens, ficha técnica, pessoas), auditoria. Alimenta todos os módulos.</text>'
    M = {
        'fech': (60, 120, RED, '8 Fechamento de Caixa', 'contagem cega e diferenças'),
        'vend': (470, 120, RED, '6 Vendas', 'balcão e Anota Aí'),
        'prod': (880, 120, RED, '7 Produção', 'tablets por função'),
        'estq': (1290, 120, RED, '3 Estoques e Compras', 'saldo, compra e validade'),
        'cont': (265, 330, SLATE, '4 Contas e Fluxo de Caixa', 'pagar, receber, 30 dias'),
        'imob': (1290, 330, SLATE, '2 Imobilizado', 'bens e manutenção'),
        'rh': (60, 540, SLATE, '1 RH', 'pessoas, escala e ponto'),
        'cust': (700, 540, GREEN, '5 Custos', 'CMV, margem e preço'),
    }
    for k, (x, y, c, t, s) in M.items():
        b += title_box(x, y, 300, 96, t, s, c, fs=24, fs2=18)
    b += f'<rect x="60" y="750" width="1544" height="96" rx="16" fill="{GREEN}"/>'
    b += text_block(832, 785, '9 BI', 26, '#fff', 700, 600, family='os')
    b += text_block(832, 822, 'Painel diário, DRE por competência, lucratividade e alertas. Lê de todos os módulos e não escreve em nenhum.', 19, '#fff', 500, 1400)
    a = ''
    a += arrow(770, 168, 880, 168, INK, label='pedido', lx=825, ly=146, fs=17)
    a += arrow(470, 168, 360, 168, INK, label='esperado', lx=415, ly=146, fs=17)
    a += arrow(1180, 168, 1290, 168, INK, label='consumo', lx=1235, ly=146, fs=17)
    a += arrow(560, 216, 480, 330, INK, label='recebíveis', lx=568, ly=268, fs=17)
    a += arrow(270, 216, 340, 330, INK, label='realizado', lx=262, ly=268, fs=17)
    a += arrow(1440, 216, 1440, 330, INK, label='bem', lx=1440, ly=273, fs=17)
    a += arrow(1340, 216, 565, 360, INK, label='títulos a pagar', lx=960, ly=285, fs=17)
    a += arrow(1400, 216, 1000, 565, INK, label='custo médio', lx=1262, ly=292, fs=17)
    a += arrow(1290, 400, 1000, 590, INK, label='depreciação', lx=1215, ly=452, fs=17)
    a += arrow(1290, 385, 565, 405, INK, dash='9 7', label='parcelas e manutenção', lx=1040, ly=392, fs=17, lw=260)
    a += arrow(200, 540, 340, 426, INK, label='folha gerencial', lx=240, ly=488, fs=17)
    a += arrow(360, 588, 700, 588, INK, label='custo de pessoal', lx=530, ly=566, fs=17)
    a += arrow(500, 426, 780, 540, INK, label='despesas e taxas', lx=590, ly=458, fs=17)
    a += arrow(800, 540, 640, 216, RED, dash='9 7', label='sugestão de preço', lx=735, ly=384, fs=17, lcolor=RED)
    a += arrow(210, 636, 210, 750, GREY)
    a += arrow(850, 636, 850, 750, GREY)
    # legend
    lg = ''
    for i, (c, t) in enumerate([(RED, 'Operacionais'), (SLATE, 'Administrativos'), (GREEN, 'Analíticos')]):
        lg += f'<rect x="{1100 + i * 190}" y="868" width="22" height="22" rx="5" fill="{c}"/><text x="{1130 + i * 190}" y="886" font-size="19" fill="{GREY}" class="dm">{t}</text>'
    lg += f'<text x="60" y="886" font-size="19" fill="{GREY}" class="dm">Linha tracejada: ligação secundária.</text>'
    return svg(W, 910, b + a + lg)


def lane(i, name, top=None, h=124, gap=4, fill=None):
    y = i * (h + gap)
    f = fill or (TAN if i % 2 == 0 else '#FFFFFF')
    s = f'<rect x="0" y="{y}" width="{W}" height="{h}" rx="10" fill="{f}" stroke="{LINE}" stroke-width="1.5"/>'
    s += f'<rect x="0" y="{y}" width="190" height="{h}" rx="10" fill="{DARK}"/>'
    s += text_block(95, y + h / 2, name, 20, '#fff', 700, 170)
    return s


def flow_order():
    names = ['Canal e atendimento', 'Sistema', 'Massa (tablet)', 'Pizzaiolo (tablet)', 'Forno e acabamento (tablet)', 'Balcão e entrega', 'Caixa']
    LH = 124
    ST = LH + 4
    b = ''.join(lane(i, n) for i, n in enumerate(names))
    cx = [200, 450, 700, 950, 1200, 1450]
    BW, BH = 205, 100

    def by(l):
        return l * ST + (LH - BH) // 2

    def bx(col, lanei, text, color=RED, fill='#FFFFFF'):
        return box(cx[col], by(lanei), BW, BH, text, fill=fill, stroke=color, fs=17)

    def mid(col):
        return cx[col] + BW / 2

    def cy(l):
        return by(l) + BH / 2
    b += bx(0, 0, 'Cliente pede: balcão ou Anota Aí')
    b += bx(1, 0, 'Atendente registra itens, adicionais e pagamento')
    b += diamond(mid(2), cy(0), 180, 104, 'Urgente?')
    b += text_block(mid(2) + 175, cy(0), 'sim: topo da fila', 17, RED, 700, 160)
    b += bx(2, 1, 'Gera lista de pizzas e necessidade de massa')
    b += bx(2, 2, 'Fase 1: bater, bolear e crescer; lança o total')
    b += bx(3, 2, 'Fase 2: abre massas e massas com borda')
    b += bx(3, 3, 'Monta a próxima pizza; sem insumo, retrocede com motivo')
    b += bx(4, 3, 'Marca produzida')
    b += bx(4, 4, 'Forno esteira: 2 min, 4 a 6 pizzas por vez')
    b += bx(5, 4, 'Acaba, empacota e etiqueta; marca pizza acabada')
    b += bx(5, 5, 'Marca o pedido acabado, à mão')
    b += bx(4, 5, 'Retirada ou despacho; balcão marca entregue')
    b += bx(3, 6, 'Fechamento do dia: contagem cega e acerto do entregador', SLATE)
    a = ''
    a += arrow(cx[0] + BW, cy(0), cx[1], cy(0))
    a += arrow(cx[1] + BW, cy(0), mid(2) - 90, cy(0))
    a += arrow(mid(2), cy(0) + 52, mid(2), by(1))
    a += arrow(mid(2), by(1) + BH, mid(2), by(2))
    a += arrow(cx[2] + BW, cy(2), cx[3], cy(2))
    a += arrow(mid(3), by(2) + BH, mid(3), by(3))
    a += arrow(cx[3] + BW, cy(3), cx[4], cy(3))
    a += arrow(mid(4), by(3) + BH, mid(4), by(4))
    a += arrow(cx[4] + BW, cy(4), cx[5], cy(4))
    a += arrow(mid(5), by(4) + BH, mid(5), by(5))
    a += arrow(cx[5], cy(5), cx[4] + BW, cy(5))
    a += arrow(mid(4), by(5) + BH, cx[3] + BW, cy(6), SLATE)
    return svg(W, 7 * ST - 4, b + a)


def group(x, y, w, h, title, color):
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="{TAN}" stroke="{color}" stroke-width="3"/>'
    s += text_block(x + w / 2, y + 36, title, 27, color, 700, w - 20, family='os')
    return s


def flow_stock():
    b = ''
    stages = [
        ('Compra', RED, ['Pedido por fornecedor, aprovado acima do valor definido', 'Recebimento conferido e nota digitada']),
        ('Estoque', RED, ['Saldo por local: freezer, câmara e estoque seco', 'Inventário: críticos todo dia, completo todo mês']),
        ('Venda e produção', RED, ['Baixa pela ficha técnica a cada venda', 'Perdas com motivo e consumo interno']),
        ('Custos', GREEN, ['Custo médio móvel, com os últimos 3 preços visíveis', 'CMV teórico contra real, por mês']),
        ('Resultado', GREEN, ['Margem por produto, sabor e canal; preço sugerido', 'DRE por competência e alertas']),
    ]
    xs = [20, 350, 680, 1010, 1340]
    for (t, c, items), x in zip(stages, xs):
        b += group(x, 20, 304, 430, t, c)
        b += box(x + 22, 90, 260, 150, items[0], fill='#fff', stroke=c, fs=20)
        b += box(x + 22, 270, 260, 150, items[1], fill='#fff', stroke=c, fs=20)
    a = ''
    for i in range(4):
        a += arrow(xs[i] + 304, 235, xs[i + 1], 235, INK)
    a += arrow(172, 450, 172, 520, SLATE, label='gera título', lx=240, ly=486, fs=17)
    b += box(20, 520, 300, 120, 'Título a pagar com prazo e forma do fornecedor', fill='#fff', stroke=SLATE, fs=20)
    b += box(370, 520, 300, 120, 'Pagamento com a forma registrada na baixa', fill='#fff', stroke=SLATE, fs=20)
    b += box(720, 520, 300, 120, 'Fluxo de caixa: 30 dias, com 7 em destaque', fill='#fff', stroke=SLATE, fs=20)
    a += arrow(320, 580, 370, 580, INK)
    a += arrow(670, 580, 720, 580, INK)
    b += f'<rect x="1070" y="520" width="574" height="120" rx="14" fill="{TAN}"/>'
    b += text_block(1357, 580, 'Despesas recorrentes, taxas de cartão e de canal e a depreciação dos bens vêm de Contas e Imobilizado e alimentam Custos.', 20, INK, 500, 520)
    return svg(W, 680, b + a)


def flow_cash():
    b = ''
    bx = lambda x, y, w, h, t, c=RED: box(x, y, w, h, t, fill='#fff', stroke=c, fs=20)
    b += bx(20, 60, 230, 130, 'Abertura: fundo de troco padrão; fica registrado quem abriu')
    b += bx(280, 60, 230, 130, 'Durante o dia: vendas por forma de pagamento e sangrias com motivo')
    b += bx(540, 60, 230, 130, 'Fim do turno: acerto do entregador, por pedido', SLATE)
    b += bx(800, 60, 230, 130, 'Contagem cega: o operador conta sem ver o esperado')
    b += diamond(1230, 125, 250, 160, 'Dentro da tolerância?')
    b += bx(1400, 60, 244, 130, 'Justificativa obrigatória; gerente aprova a diferença')
    b += bx(1100, 380, 260, 130, 'Relatório do dia, em tela e impressão')
    b += bx(740, 380, 260, 130, 'Contas e Fluxo de Caixa recebem o realizado; BI recebe as quebras', SLATE)
    b += f'<rect x="20" y="380" width="620" height="130" rx="14" fill="{TAN}"/>'
    b += text_block(330, 445, 'Uma gaveta e um caixa por dia. Abre gerente ou atendente. Sangria acima do valor definido exige o gerente. A tolerância de diferença fica nos parâmetros.', 20, INK, 500, 570)
    a = ''
    a += arrow(250, 125, 280, 125)
    a += arrow(510, 125, 540, 125)
    a += arrow(770, 125, 800, 125)
    a += arrow(1030, 125, 1105, 125)
    a += arrow(1355, 125, 1400, 125, RED, label='não', lx=1378, ly=100, fs=17)
    a += arrow(1230, 205, 1230, 380, INK, label='sim', lx=1252, ly=290, fs=17)
    a += arrow(1522, 190, 1360, 445, RED, mid=[(1522, 445)])
    a += arrow(1100, 445, 1000, 445)
    return svg(W, 540, b + a)


def flow_maint():
    b = ''
    bx = lambda x, y, w, h, t, c=SLATE: box(x, y, w, h, t, fill='#fff', stroke=c, fs=20)
    b += bx(20, 40, 420, 140, 'Preventiva: plano por bem, começando por forno, câmara e freezer, com alerta antes do vencimento')
    b += bx(20, 270, 420, 140, 'Preditiva: leitura digitada na inspeção (horas de uso, temperatura) sai do normal')
    b += bx(20, 500, 420, 140, 'Corretiva: quebra registrada, com a hora da parada e da volta')
    b += bx(620, 270, 320, 140, 'Ordem de serviço: bem, tipo, responsável, peças, horas e custo; administrador aprova acima do valor definido')
    b += bx(1040, 270, 230, 140, 'Execução por funcionário ou terceiro, e fechamento da ordem')
    b += bx(1380, 40, 264, 120, 'Estoque: baixa das peças; estoque mínimo só das peças críticas', RED)
    b += bx(1380, 270, 264, 140, 'Custos: custo da manutenção por bem, fixo ou variável', GREEN)
    b += bx(1380, 500, 264, 120, 'Contas a Pagar: pagamento ao terceiro', SLATE)
    b += bx(620, 540, 320, 100, 'Parada de bem crítico avisa a produção e registra o tempo parado', RED)
    a = ''
    a += arrow(440, 110, 620, 320, INK)
    a += arrow(440, 340, 620, 340, INK)
    a += arrow(440, 570, 620, 380, INK)
    a += arrow(440, 600, 620, 590, RED, dash='9 7')
    a += arrow(940, 340, 1040, 340, INK)
    a += arrow(1270, 320, 1380, 110, INK)
    a += arrow(1270, 340, 1380, 340, INK)
    a += arrow(1270, 360, 1380, 560, INK)
    return svg(W, 680, b + a)


ALL = [
    ('Mapa do sistema', 'Nove módulos ligados pelo mesmo registro', flow_map),
    ('Jornada do pedido', 'Da chamada do cliente ao fechamento do dia', flow_order),
    ('Do insumo ao resultado', 'Compra, estoque, custo e margem', flow_stock),
    ('O dinheiro do dia', 'Fechamento de caixa sem surpresa', flow_cash),
    ('Manutenção dos equipamentos', 'Preventiva, preditiva e corretiva', flow_maint),
]
